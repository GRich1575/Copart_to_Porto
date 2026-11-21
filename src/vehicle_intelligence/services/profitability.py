"""Buy decision per vehicle (Business_Model.txt questions 2, 4, 5).

Rules:
- Reference price = median of local comparable listings (needs >= min_comparables, else NEEDS_DATA).
- Target resale price = reference * (1 - resale_discount).
- Expected profit at bid b = target resale - landed_cost(b).
- Max bid = largest b with expected profit >= min_edge (solved from the linear cost line, rounded down to cents).
- BUY when 0 < bid <= max bid; otherwise PASS, with the reason.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal
from enum import Enum

from vehicle_intelligence.core.config import Economics
from vehicle_intelligence.services.import_cost import ZERO, CostLine, cost_line

CENT = Decimal("0.01")


class Verdict(str, Enum):
    BUY = "BUY"
    PASS = "PASS"
    NEEDS_DATA = "NEEDS_DATA"


@dataclass(frozen=True)
class Decision:
    verdict: Verdict
    bid: Decimal
    reference_price: Decimal | None
    resale_target: Decimal | None
    landed_cost: Decimal | None
    expected_profit: Decimal | None
    max_bid: Decimal | None
    reasons: tuple[str, ...]


def decide(bid: Decimal, local_prices: list[Decimal], econ: Economics, repair: Decimal = ZERO) -> Decision:
    prices = [p for p in local_prices if p is not None and p > 0]
    if len(prices) < econ.min_comparables:
        return Decision(Verdict.NEEDS_DATA, bid, None, None, None, None, None,
                        (f"{len(prices)} comparable listing(s); need {econ.min_comparables}",))

    reference = Decimal(str(statistics.median(prices)))
    resale_target = reference * (Decimal("1") - econ.resale_discount)
    line = cost_line(econ, repair)
    landed = line.at(bid)
    profit = resale_target - landed
    max_bid = _max_bid(resale_target, line, econ.min_edge)

    reasons: list[str] = []
    if max_bid <= 0:
        reasons.append("no bid gives the minimal edge: fixed costs exceed margin")
        verdict = Verdict.PASS
    elif bid <= 0:
        reasons.append("bid must be positive")
        verdict = Verdict.PASS
    elif bid <= max_bid:
        verdict = Verdict.BUY
    else:
        reasons.append(f"bid {bid} above max bid {max_bid}")
        verdict = Verdict.PASS

    return Decision(
        verdict=verdict,
        bid=bid,
        reference_price=reference,
        resale_target=resale_target.quantize(CENT, rounding=ROUND_DOWN),
        landed_cost=landed.quantize(CENT, rounding=ROUND_DOWN),
        expected_profit=profit.quantize(CENT, rounding=ROUND_DOWN),
        max_bid=max_bid,
        reasons=tuple(reasons),
    )


def _max_bid(resale_target: Decimal, line: CostLine, min_edge: Decimal) -> Decimal:
    raw = (resale_target - min_edge - line.intercept) / line.slope
    return max(raw, ZERO).quantize(CENT, rounding=ROUND_DOWN)
