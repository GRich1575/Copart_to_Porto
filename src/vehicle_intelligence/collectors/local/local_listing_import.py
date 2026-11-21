"""Import local used-vehicle listings from an owner-exported CSV (Business_Model.txt item 2).

Columns (header required; empty cell = unknown):
  source, external_id, make, model                        (required)
  price, currency                                         (required; currency must be EUR for Portugal)
  year, mileage_km, source_url                            (optional)
source must be a platform with kind local_listing in config/platforms.yaml.
Rows are upserted by (source, external_id); observed_at is refreshed on every import.
"""

from __future__ import annotations

import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from vehicle_intelligence.models import LocalListing
from vehicle_intelligence.models.base import utcnow
from vehicle_intelligence.monitoring import tracked_run

JOB = "local_listing_import"
COUNTRY = "PT"
REQUIRED = ("source", "external_id", "make", "model", "price", "currency")


class ListingRow(BaseModel):
    source: str = Field(min_length=1)
    external_id: str = Field(min_length=1)
    make: str = Field(min_length=1)
    model: str = Field(min_length=1)
    price: Decimal = Field(gt=0)
    currency: Literal["EUR"]
    year: int | None = Field(default=None, ge=1900, le=2100)
    mileage_km: int | None = Field(default=None, ge=0)
    source_url: str | None = None

    @field_validator("*", mode="before")
    @classmethod
    def _blank_to_none(cls, v):
        if isinstance(v, str):
            v = v.strip()
            return v or None
        return v


def _parse_price(v: str | None):
    """Accept '9500', '9500.50', '9.500,50' (PT) and '9,500.50' (EN). The last separator is the decimal mark."""
    s = (v or "").replace(" ", "").replace(" ", "")
    last_dot, last_comma = s.rfind("."), s.rfind(",")
    if last_dot != -1 and last_comma != -1:
        dec = "," if last_comma > last_dot else "."
        s = s.replace("." if dec == "," else ",", "").replace(dec, ".")
    elif last_comma != -1:
        s = s.replace(",", ".")
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return v


def parse_csv(path: Path, known_sources: set[str]) -> tuple[list[ListingRow], list[tuple[int, str]]]:
    rows: list[ListingRow] = []
    errors: list[tuple[int, str]] = []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path.name}: missing required column(s): {', '.join(missing)}")
        for line_no, raw in enumerate(reader, start=2):
            data = dict(raw)
            data["price"] = _parse_price(raw.get("price"))
            if data.get("source") not in known_sources:
                errors.append((line_no, f"unknown or non-local source: {data.get('source')!r}"))
                continue
            try:
                rows.append(ListingRow.model_validate(data))
            except ValidationError as exc:
                errors.append((line_no, "; ".join(e["msg"] for e in exc.errors())))
    return rows, errors


def upsert_listings(session: Session, rows: list[ListingRow], now: datetime) -> int:
    for r in rows:
        item = session.scalar(select(LocalListing).where(
            LocalListing.platform_id == r.source, LocalListing.external_id == r.external_id))
        if item is None:
            item = LocalListing(platform_id=r.source, external_id=r.external_id, country=COUNTRY,
                                currency=r.currency, price=r.price, make=r.make, model=r.model)
            session.add(item)
        item.make = r.make
        item.model = r.model
        item.year = r.year
        item.mileage_km = r.mileage_km
        item.price = r.price
        item.currency = r.currency
        item.source_url = r.source_url
        item.observed_at = now
    session.commit()
    return len(rows)


def import_listings(path: Path, session_factory: sessionmaker[Session],
                    known_sources: set[str]) -> tuple[int, list[tuple[int, str]]]:
    """Upsert the file's valid rows. Raises if no row is valid (run recorded as failed)."""
    with tracked_run(session_factory, JOB) as run:
        rows, errors = parse_csv(path, known_sources)
        if not rows:
            raise ValueError(f"{path.name}: no valid rows ({len(errors)} rejected)")
        with session_factory() as s:
            accepted = upsert_listings(s, rows, utcnow())
        run.rows = accepted
    return accepted, errors
