from datetime import datetime
from decimal import Decimal

import pytest

from vehicle_intelligence.collectors.auctions.copart_import import import_file, parse_csv
from vehicle_intelligence.core.database import create_schema, make_engine, make_session_factory
from vehicle_intelligence.models import AuctionLot, CollectorRun

HEADER = "lot_id,make,model,status,vin,year,mileage_miles,auction_date,current_bid,final_price,source_url\n"


@pytest.fixture
def sf(tmp_path):
    eng = make_engine(f"sqlite:///{(tmp_path / 'auc.db').as_posix()}")
    create_schema(eng)
    yield make_session_factory(eng)
    eng.dispose()


def _csv(tmp_path, body, name="export.csv"):
    p = tmp_path / name
    p.write_text(HEADER + body, encoding="utf-8")
    return p


def test_parse_valid_rows_and_blank_cells_become_none(tmp_path):
    p = _csv(tmp_path, "1001,Honda,Gold Wing,listed,,2019,12000,2026-12-01T15:00:00+00:00,5000.50,,https://x\n")
    rows, errors = parse_csv(p)
    assert errors == []
    r = rows[0]
    assert r.vin is None and r.final_price is None
    assert r.current_bid == Decimal("5000.50") and r.mileage_miles == 12000
    assert r.auction_date == datetime.fromisoformat("2026-12-01T15:00:00+00:00")


def test_bad_rows_reported_with_line_numbers_not_fatal(tmp_path):
    body = (
        "1001,Honda,Gold Wing,listed,,2019,12000,,,,\n"
        "1002,Honda,Gold Wing,bogus,,2019,12000,,,,\n"   # bad status
        "1003,Honda,Gold Wing,sold,,2019,-5,,,,\n"       # negative mileage
    )
    rows, errors = parse_csv(_csv(tmp_path, body))
    assert [r.lot_id for r in rows] == ["1001"]
    assert [line for line, _ in errors] == [3, 4]


def test_missing_required_column_rejected(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("lot_id,make,status\n1,Honda,listed\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing required column"):
        parse_csv(p)


def test_import_upserts_and_is_idempotent(tmp_path, sf):
    p = _csv(tmp_path, "1001,Honda,Gold Wing,listed,,2019,12000,,4000,,\n")
    res = import_file(p, sf)
    assert res.accepted == 1
    # same file again: no duplicates
    import_file(p, sf)
    # lot sold later: status and final price updated in place
    p2 = _csv(tmp_path, "1001,Honda,Gold Wing,sold,,2019,12000,,4000,9100,\n", name="export2.csv")
    import_file(p2, sf)
    with sf() as s:
        lots = s.query(AuctionLot).all()
        assert len(lots) == 1
        assert lots[0].status == "sold" and float(lots[0].final_price) == 9100.0
        assert lots[0].platform_id == "copart_us" and lots[0].country == "US" and lots[0].currency == "USD"
        assert s.query(CollectorRun).filter_by(job="copart_import", status="success").count() == 3


def test_all_rows_invalid_fails_run_and_raises(tmp_path, sf):
    p = _csv(tmp_path, "1001,Honda,Gold Wing,bogus,,,,,,,\n")
    with pytest.raises(ValueError, match="no valid rows"):
        import_file(p, sf)
    with sf() as s:
        run = s.query(CollectorRun).one()
        assert run.status == "failed"


def test_partial_file_imports_valid_and_reports_rejected(tmp_path, sf):
    p = _csv(tmp_path, "1001,Honda,Gold Wing,listed,,,,,,,\n1002,Honda,Gold Wing,bogus,,,,,,,\n")
    res = import_file(p, sf)
    assert res.accepted == 1 and [line for line, _ in res.rejected] == [3]
