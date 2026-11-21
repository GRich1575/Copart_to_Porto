"""Import Copart lots from a CSV that the owner exports from his own account (see docs/sources/copart.md).

No network access. Input columns (header required; empty cell = unknown):
  lot_id, make, model, status                          (required)
  vin, vehicle_type, year, mileage_miles, damage_type, title_type,
  auction_date (ISO 8601), current_bid, final_price, source_url   (optional)
status: listed | sold | unsold | historical
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from vehicle_intelligence.core.logging import get_logger
from vehicle_intelligence.models import AuctionLot
from vehicle_intelligence.models.base import utcnow
from vehicle_intelligence.monitoring import tracked_run

PLATFORM_ID = "copart_us"
COUNTRY = "US"
CURRENCY = "USD"
JOB = "copart_import"
REQUIRED = ("lot_id", "make", "model", "status")
log = get_logger("collectors.copart")


class LotRow(BaseModel):
    lot_id: str = Field(min_length=1)
    make: str = Field(min_length=1)
    model: str = Field(min_length=1)
    status: Literal["listed", "sold", "unsold", "historical"]
    vin: str | None = None
    vehicle_type: str | None = None
    year: int | None = Field(default=None, ge=1900, le=2100)
    mileage_miles: int | None = Field(default=None, ge=0)
    damage_type: str | None = None
    title_type: str | None = None
    auction_date: datetime | None = None
    current_bid: Decimal | None = Field(default=None, ge=0)
    final_price: Decimal | None = Field(default=None, ge=0)
    source_url: str | None = None

    @field_validator("*", mode="before")
    @classmethod
    def _blank_to_none(cls, v):
        if isinstance(v, str):
            v = v.strip()
            return v or None
        return v


@dataclass
class ImportResult:
    accepted: int = 0
    rejected: list[tuple[int, str]] = field(default_factory=list)  # (csv line, message)


def parse_csv(path: Path) -> tuple[list[LotRow], list[tuple[int, str]]]:
    rows: list[LotRow] = []
    errors: list[tuple[int, str]] = []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path.name}: missing required column(s): {', '.join(missing)}")
        for line_no, raw in enumerate(reader, start=2):  # line 1 is the header
            try:
                rows.append(LotRow.model_validate(raw))
            except ValidationError as exc:
                errors.append((line_no, "; ".join(e["msg"] for e in exc.errors())))
    return rows, errors


def upsert_lots(session: Session, rows: list[LotRow], now: datetime) -> int:
    for r in rows:
        lot = session.scalar(
            select(AuctionLot).where(AuctionLot.platform_id == PLATFORM_ID, AuctionLot.lot_id == r.lot_id)
        )
        if lot is None:
            lot = AuctionLot(platform_id=PLATFORM_ID, lot_id=r.lot_id, country=COUNTRY, currency=CURRENCY,
                             first_seen_at=now)
            session.add(lot)
        lot.vin = r.vin
        lot.vehicle_type = r.vehicle_type
        lot.make = r.make
        lot.model = r.model
        lot.year = r.year
        lot.mileage_miles = r.mileage_miles
        lot.damage_type = r.damage_type
        lot.title_type = r.title_type
        lot.status = r.status
        lot.auction_date = r.auction_date
        lot.current_bid = r.current_bid
        lot.final_price = r.final_price
        lot.source_url = r.source_url
        lot.last_seen_at = now
    session.commit()
    return len(rows)


def import_file(path: Path, session_factory: sessionmaker[Session]) -> ImportResult:
    """Import one export file. Raises if the file has no valid rows at all (run is recorded as failed)."""
    with tracked_run(session_factory, JOB) as run:
        rows, errors = parse_csv(path)
        if not rows:
            raise ValueError(f"{path.name}: no valid rows ({len(errors)} rejected)")
        with session_factory() as s:
            accepted = upsert_lots(s, rows, utcnow())
        run.rows = accepted
    for line_no, msg in errors:
        log.warning("row rejected", extra={"extra_fields": {"file": path.name, "line": line_no, "error": msg}})
    return ImportResult(accepted=accepted, rejected=errors)
