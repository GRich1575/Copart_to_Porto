"""Local comparable prices for a watchlist vehicle (input to the profitability decision).

A listing is a comparable when it matches the watchlist entry (brand, model/variant, year >= min,
mileage <= cap). Listing mileage is in km and is converted to miles before the check.
Prices are EUR. No FX conversion is done here: the economics config is USD, so the caller must
not compare these prices with USD costs until an FX source is added.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from vehicle_intelligence.core.config import VehicleSpec
from vehicle_intelligence.models import LocalListing
from vehicle_intelligence.services.vehicle_matching import VehicleFacts, match_vehicle

KM_TO_MILES = Decimal("0.621371")


def comparable_prices(session: Session, spec: VehicleSpec) -> list[Decimal]:
    rows = session.scalars(select(LocalListing).where(LocalListing.country == "PT")).all()
    prices: list[Decimal] = []
    for r in rows:
        miles = round(r.mileage_km * KM_TO_MILES) if r.mileage_km is not None else None
        facts = VehicleFacts(vehicle_type=spec.vehicle_type, make=r.make, model=r.model,
                             year=r.year, mileage_miles=miles)
        if match_vehicle(facts, spec).matched:
            prices.append(Decimal(r.price))
    return prices
