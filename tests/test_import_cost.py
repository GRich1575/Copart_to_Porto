from decimal import Decimal

import pytest

from vehicle_intelligence.core.config import DEFAULT_CONFIG_DIR, Economics, load_config
from vehicle_intelligence.services.import_cost import cost_line, landed_cost


def _econ(**over) -> Economics:
    base = dict(container_shipping=Decimal("350"), documents_fee=Decimal("100"))
    base.update(over)
    return Economics(**base)


def test_repo_economics_match_business_model_numbers():
    econ = load_config(DEFAULT_CONFIG_DIR, env={}).economics
    assert econ.container_shipping == Decimal("350")  # Business_Model.txt: container ~ $350
    assert econ.documents_fee == Decimal("100")        # Business_Model.txt: documents ~ $100
    assert econ.resale_discount == Decimal("0.10")     # resale at least 10% below local price
    assert econ.min_edge == Decimal("1500")            # lower bound of 1500-2000


def test_fixed_costs_only_no_fees():
    econ = _econ()
    b = landed_cost(Decimal("5000"), econ)
    assert b.total == Decimal("5000") + Decimal("350") + Decimal("100")
    assert b.items["auction_fee"] == 0 and b.items["customs_duty"] == 0


def test_percent_auction_fee_and_customs_duty_on_bid_plus_container():
    econ = _econ(auction_fee_percent=Decimal("0.10"), customs_duty_percent=Decimal("0.05"))
    b = landed_cost(Decimal("1000"), econ)
    assert b.items["auction_fee"] == Decimal("100.00")
    assert b.items["customs_duty"] == Decimal("67.50")  # 5% of (1000 + 350)
    assert b.total == Decimal("1000") + Decimal("100") + Decimal("350") + Decimal("100") + Decimal("67.50")


def test_repair_included_in_total():
    b = landed_cost(Decimal("1000"), _econ(), repair=Decimal("250"))
    assert b.items["repair"] == Decimal("250")
    assert b.total == Decimal("1000") + Decimal("350") + Decimal("100") + Decimal("250")


@pytest.mark.parametrize("bid", ["0", "1", "1234.56", "9999.99"])
def test_linear_line_equals_itemised_breakdown(bid):
    econ = _econ(auction_fee_percent=Decimal("0.07"), auction_fee_fixed=Decimal("25"),
                 transport_to_port=Decimal("180"), port_load=Decimal("40"), port_unload=Decimal("35"),
                 last_mile=Decimal("90"), registration_fee=Decimal("60"), customs_duty_percent=Decimal("0.04"))
    repair = Decimal("300")
    b = Decimal(bid)
    assert cost_line(econ, repair).at(b) == landed_cost(b, econ, repair).total
