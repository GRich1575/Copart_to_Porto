"""Landed cost of one vehicle: purchase -> repair -> registration (Business_Model.txt items 3, 5, 6).

Cost is linear in the bid b:  total(b) = slope * b + intercept, with
    slope     = 1 + auction_fee_percent + customs_duty_percent
    intercept = auction_fee_fixed + transport_to_port + port_load + container_shipping + port_unload
                + documents_fee + last_mile + registration_fee + repair
                + customs_duty_percent * container_shipping
Customs duty is assumed on (bid + container shipping). Rates are assumptions until verified in S3.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from vehicle_intelligence.core.config import Economics

ZERO = Decimal("0")


@dataclass(frozen=True)
class CostBreakdown:
    items: dict[str, Decimal]

    @property
    def total(self) -> Decimal:
        return sum(self.items.values(), ZERO)


@dataclass(frozen=True)
class CostLine:
    slope: Decimal
    intercept: Decimal

    def at(self, bid: Decimal) -> Decimal:
        return self.slope * bid + self.intercept


def cost_line(econ: Economics, repair: Decimal = ZERO) -> CostLine:
    duty = econ.customs_duty_percent
    slope = Decimal("1") + econ.auction_fee_percent + duty
    intercept = (
        econ.auction_fee_fixed + econ.transport_to_port + econ.port_load + econ.container_shipping
        + econ.port_unload + econ.documents_fee + econ.last_mile + econ.registration_fee
        + repair + duty * econ.container_shipping
    )
    return CostLine(slope=slope, intercept=intercept)


def landed_cost(bid: Decimal, econ: Economics, repair: Decimal = ZERO) -> CostBreakdown:
    """Itemised landed cost for a purchase at `bid`. Sums to cost_line(...).at(bid)."""
    duty_base = bid + econ.container_shipping
    items = {
        "purchase": bid,
        "auction_fee": bid * econ.auction_fee_percent + econ.auction_fee_fixed,
        "transport_to_port": econ.transport_to_port,
        "port_load": econ.port_load,
        "container_shipping": econ.container_shipping,
        "port_unload": econ.port_unload,
        "documents": econ.documents_fee,
        "customs_duty": duty_base * econ.customs_duty_percent,
        "registration": econ.registration_fee,
        "last_mile": econ.last_mile,
        "repair": repair,
    }
    return CostBreakdown(items=items)
