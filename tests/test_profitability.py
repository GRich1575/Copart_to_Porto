from decimal import Decimal

from vehicle_intelligence.core.config import Economics
from vehicle_intelligence.services.import_cost import cost_line
from vehicle_intelligence.services.profitability import Verdict, decide

D = Decimal
PRICES = [D("10000"), D("12000"), D("11000")]  # median 11000 -> target 9900 at 10% discount


def _econ(**over) -> Economics:
    base = dict(container_shipping=D("350"), documents_fee=D("100"), min_edge=D("1500"))
    base.update(over)
    return Economics(**base)


def test_needs_data_when_too_few_comparables():
    d = decide(D("5000"), PRICES[:2], _econ())
    assert d.verdict == Verdict.NEEDS_DATA and d.max_bid is None


def test_reference_and_resale_target():
    d = decide(D("7000"), PRICES, _econ())
    assert d.reference_price == D("11000")
    assert d.resale_target == D("9900.00")


def test_buy_below_max_bid_and_profit_meets_min_edge():
    # max bid = 9900 - 1500 - 450 = 7950
    d = decide(D("7900"), PRICES, _econ())
    assert d.max_bid == D("7950.00")
    assert d.verdict == Verdict.BUY
    assert d.expected_profit == D("1550.00") and d.expected_profit >= D("1500")


def test_pass_above_max_bid_with_reason():
    d = decide(D("8000"), PRICES, _econ())
    assert d.verdict == Verdict.PASS
    assert any("above max bid" in r for r in d.reasons)


def test_max_bid_gives_exactly_min_edge_profit():
    econ = _econ(auction_fee_percent=D("0.07"), auction_fee_fixed=D("25"), transport_to_port=D("180"),
                 customs_duty_percent=D("0.04"))
    d = decide(D("1"), PRICES, econ)
    line = cost_line(econ)
    profit_at_max = d.resale_target - line.at(d.max_bid)
    assert profit_at_max >= econ.min_edge
    assert profit_at_max - econ.min_edge < D("1")  # rounding down to cents only


def test_repair_reduces_max_bid():
    no_repair = decide(D("1"), PRICES, _econ()).max_bid
    with_repair = decide(D("1"), PRICES, _econ(), repair=D("500")).max_bid
    assert with_repair == no_repair - D("500.00")


def test_pass_when_fixed_costs_exceed_margin():
    d = decide(D("100"), PRICES, _econ(transport_to_port=D("9000")))
    assert d.verdict == Verdict.PASS and d.max_bid == D("0.00")
    assert "no bid gives the minimal edge" in d.reasons[0]


def test_non_positive_bid_is_pass():
    d = decide(D("0"), PRICES, _econ())
    assert d.verdict == Verdict.PASS and "bid must be positive" in d.reasons
