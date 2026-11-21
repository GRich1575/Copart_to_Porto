from datetime import datetime, timezone
from decimal import Decimal

import pytest

from vehicle_intelligence.collectors.auctions.copart_search_export import (
    JOB,
    import_search_export,
    parse_search_export,
)
from vehicle_intelligence.core.database import create_schema, make_engine, make_session_factory
from vehicle_intelligence.models import AuctionLot, CollectorRun

HEADER = ("Lot URL,Lot #,Est. Retail value,Sale date,Year,Make,Model,Engine type,Cylinders,VIN,"
          "Title code,Odometer,Odometer description,Damage description,Current bid,My bid,Item number,"
          "Sale name,Auto grade,Sale light,Announcements\n")
URL = "https://www.copart.com/lot/{}"


def _row(lot, odo="12,088 A", sale="11/25/2026 06:00 pm GMT", bid="1,800 USD", title="", year="2019", vin="VINX"):
    # Values containing commas are quoted, as in the real Copart export.
    return (f"{URL.format(lot)},{lot},0,{sale},{year},HONDA,GL1800,6,6,{vin},{title},\"{odo}\",ACTUAL,"
            f"FRONT END,\"{bid}\",0 USD,1,SALE,0.0,N/A,\n")


@pytest.fixture
def export(tmp_path):
    def make(*rows, name="search.csv", header=HEADER):
        p = tmp_path / name
        p.write_text(header + "".join(rows), encoding="utf-8-sig")
        return p
    return make


@pytest.fixture
def sf(tmp_path):
    eng = make_engine(f"sqlite:///{(tmp_path / 'exp.db').as_posix()}")
    create_schema(eng)
    yield make_session_factory(eng)
    eng.dispose()


def test_column_conversions(export):
    rows, errors = parse_search_export(export(_row("111", odo="12,088 A", bid="1,800 USD",
                                                   sale="11/25/2026 06:00 pm GMT", title="SALVAGE VEHICLE TITLE"),
                                              _row("222", odo="2,872", sale="Future", bid="0 USD", title="")),
                                          vehicle_type="motorcycle")
    assert errors == []
    a, b = rows
    assert a.lot_id == "111" and a.make == "HONDA" and a.model == "GL1800" and a.year == 2019
    assert a.mileage_miles == 12088 and b.mileage_miles == 2872       # " A" stripped, commas removed
    assert a.current_bid == Decimal("1800") and b.current_bid == Decimal("0")
    assert a.auction_date == datetime(2026, 11, 25, 18, 0, tzinfo=timezone.utc)  # pm -> 18:00 UTC
    assert b.auction_date is None                                     # "Future"
    assert a.title_type == "SALVAGE VEHICLE TITLE" and b.title_type is None
    assert a.status == "listed" and a.vehicle_type == "motorcycle"
    assert a.source_url == URL.format("111")


def test_bad_rows_rejected_with_line_numbers(export):
    rows, errors = parse_search_export(export(_row("111"), _row(""), _row("333", odo="abc")))
    assert [r.lot_id for r in rows] == ["111"]
    assert [line for line, _ in errors] == [3, 4]


def test_non_export_file_rejected(tmp_path):
    p = tmp_path / "other.csv"
    p.write_text("lot_id,make\n1,Honda\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not a Copart search export"):
        parse_search_export(p)


def test_import_upserts_and_records_run(export, sf):
    p = export(_row("111"), _row("222", sale="Future", bid="525 USD"))
    accepted, errors = import_search_export(p, sf, vehicle_type="motorcycle")
    assert accepted == 2 and errors == []
    accepted, _ = import_search_export(p, sf, vehicle_type="motorcycle")  # rerun: no duplicates
    with sf() as s:
        assert s.query(AuctionLot).count() == 2
        lot = s.query(AuctionLot).filter_by(lot_id="222").one()
        assert float(lot.current_bid) == 525.0 and lot.platform_id == "copart_us"
        run = s.query(CollectorRun).filter_by(job=JOB).order_by(CollectorRun.id.desc()).first()
        assert run.status == "success" and run.rows == 2
