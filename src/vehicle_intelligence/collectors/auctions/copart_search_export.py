"""Adapter for the CSV the owner saves from a Copart search-results page (Download results).

Source columns used: Lot #, Make, Model, Year, VIN, Odometer, Damage description, Title code,
Current bid, Sale date, Lot URL. Other columns are ignored.

Conventions (verified on the 2026-11-21 export, see docs/sources/copart.md):
- Odometer "12,088 A": number with an optional trailing " A" (actual reading). Units: miles.
- Current bid "1,800 USD": amount in USD.
- Sale date "11/25/2026 06:00 pm GMT" (UTC); "Future" or blank = no date yet.
- Every exported lot is a live listing: status = listed.
"""

from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy.orm import Session, sessionmaker

from vehicle_intelligence.collectors.auctions.copart_import import PLATFORM_ID, LotRow, upsert_lots
from vehicle_intelligence.models import AuctionLot
from vehicle_intelligence.services.vin import vin_status
from vehicle_intelligence.models.base import utcnow
from vehicle_intelligence.monitoring import tracked_run

JOB = "copart_search_import"
REQUIRED = ("Lot #", "Make", "Model", "Year", "VIN", "Odometer", "Current bid", "Sale date", "Lot URL")
_NUM = re.compile(r"[^\d.]")
_ACTUAL_SUFFIX = re.compile(r"\s+A$")
_SALE_FORMAT = "%m/%d/%Y %I:%M %p GMT"


def _blank(v: str | None) -> str | None:
    v = (v or "").strip()
    return v or None


def _odometer(v: str) -> int | None:
    v = _ACTUAL_SUFFIX.sub("", (v or "").strip())
    return int(v.replace(",", "")) if v else None


def _money(v: str) -> Decimal | None:
    digits = _NUM.sub("", (v or "").replace(",", ""))
    if not digits:
        return None
    try:
        return Decimal(digits)
    except InvalidOperation:
        return None


def _sale_date(v: str) -> datetime | None:
    v = (v or "").strip()
    if not v or v.lower() == "future":
        return None
    return datetime.strptime(v, _SALE_FORMAT).replace(tzinfo=timezone.utc)


def parse_search_export(path: Path, vehicle_type: str | None = None) -> tuple[list[LotRow], list[tuple[int, str]]]:
    rows: list[LotRow] = []
    errors: list[tuple[int, str]] = []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path.name}: not a Copart search export; missing: {', '.join(missing)}")
        for line_no, raw in enumerate(reader, start=2):
            if not _blank(raw.get("Title code")):
                errors.append((line_no, "no title: excluded (owner rule)"))
                continue
            if vin_status(raw.get("VIN")) == "invalid":
                errors.append((line_no, "invalid VIN: excluded (owner rule)"))
                continue
            try:
                rows.append(LotRow(
                    lot_id=raw["Lot #"].strip(),
                    make=raw["Make"].strip(),
                    model=raw["Model"].strip(),
                    status="listed",
                    vehicle_type=vehicle_type,
                    year=int(raw["Year"]) if (raw["Year"] or "").strip() else None,
                    vin=_blank(raw["VIN"]),
                    mileage_miles=_odometer(raw["Odometer"]),
                    damage_type=_blank(raw.get("Damage description")),
                    title_type=_blank(raw.get("Title code")),
                    auction_date=_sale_date(raw["Sale date"]),
                    current_bid=_money(raw["Current bid"]),
                    source_url=_blank(raw["Lot URL"]),
                ))
            except (ValidationError, ValueError) as exc:
                errors.append((line_no, str(exc).splitlines()[0]))
    return rows, errors


def discard_excluded(session_factory: sessionmaker[Session], mileage_cap: int | None = None) -> int:
    """Delete stored Copart lots that fail the owner rules: no title, invalid VIN, or odometer above mileage_cap.

    Lots are discarded from the database, not just hidden. Re-import restores them only if they still
    have a title and mileage within the cap.
    """
    from sqlalchemy import delete, or_, select

    conds = [AuctionLot.title_type.is_(None), AuctionLot.title_type == ""]
    if mileage_cap is not None:
        conds.append(AuctionLot.mileage_miles > mileage_cap)
    with session_factory() as s:
        result = s.execute(delete(AuctionLot).where(
            AuctionLot.platform_id == PLATFORM_ID, or_(*conds)))
        bad_vin_ids = [lot.id for lot in s.scalars(
            select(AuctionLot).where(AuctionLot.platform_id == PLATFORM_ID, AuctionLot.vin.is_not(None)))
            if vin_status(lot.vin) == "invalid"]
        if bad_vin_ids:
            s.execute(delete(AuctionLot).where(AuctionLot.id.in_(bad_vin_ids)))
        s.commit()
    return (result.rowcount or 0) + len(bad_vin_ids)


def import_search_export(path: Path, session_factory: sessionmaker[Session],
                         vehicle_type: str | None = None) -> tuple[int, list[tuple[int, str]]]:
    """Upsert the export's lots. Raises if no row is valid (run recorded as failed)."""
    with tracked_run(session_factory, JOB) as run:
        rows, errors = parse_search_export(path, vehicle_type)
        if not rows:
            raise ValueError(f"{path.name}: no valid rows ({len(errors)} rejected)")
        with session_factory() as s:
            accepted = upsert_lots(s, rows, utcnow())
        run.rows = accepted
    return accepted, errors
