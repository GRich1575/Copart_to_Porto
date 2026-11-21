"""Match an auction lot or listing against the watchlist (Business_Model.txt item 0).

A lot matches a watchlist vehicle when: vehicle type and brand are equal, the model or one of the
variants appears in the lot text, year >= min_year and mileage <= mileage_cap_miles
(max_mileage_miles + mileage_tolerance_miles, hard cap; owner rule: 50 000 + up to 10 000 = 60 000).
Missing year or mileage never matches (reason is reported instead).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from vehicle_intelligence.core.config import VehicleSpec


@dataclass(frozen=True)
class VehicleFacts:
    vehicle_type: str | None
    make: str
    model: str
    year: int | None
    mileage_miles: int | None
    description: str = ""  # free text from the lot (e.g. "GOLD WING GL1800 F6B")


@dataclass(frozen=True)
class MatchResult:
    spec_id: str
    matched: bool
    reasons: tuple[str, ...] = field(default_factory=tuple)


def _norm(text: str | None) -> str:
    return " ".join((text or "").lower().split())


def match_vehicle(facts: VehicleFacts, spec: VehicleSpec) -> MatchResult:
    reasons: list[str] = []
    if facts.vehicle_type is None or _norm(facts.vehicle_type) != _norm(spec.vehicle_type):
        reasons.append("vehicle type differs")
    if _norm(facts.make) != _norm(spec.brand):
        reasons.append("brand differs")

    haystack = _norm(f"{facts.model} {facts.description}")
    names = [spec.model, *spec.variants]
    if not any(_norm(n) and _norm(n) in haystack for n in names):
        reasons.append("model/variant not found in lot")

    if facts.year is None:
        reasons.append("year unknown")
    elif facts.year < spec.min_year:
        reasons.append(f"year {facts.year} < {spec.min_year}")

    if facts.mileage_miles is None:
        reasons.append("mileage unknown")
    elif facts.mileage_miles > spec.mileage_cap_miles:
        reasons.append(f"mileage {facts.mileage_miles} > {spec.mileage_cap_miles}")

    return MatchResult(spec_id=spec.id, matched=not reasons, reasons=tuple(reasons))


def match_watchlist(facts: VehicleFacts, watchlist: list[VehicleSpec]) -> list[MatchResult]:
    """Results for all active watchlist entries that match the facts."""
    return [r for spec in watchlist if spec.active for r in [match_vehicle(facts, spec)] if r.matched]
