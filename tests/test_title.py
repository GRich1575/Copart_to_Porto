from datetime import datetime, timezone

import pytest

from vehicle_intelligence.collectors.auctions.copart_search_export import discard_excluded, parse_search_export
from vehicle_intelligence.core.config import VehicleSpec
from vehicle_intelligence.core.database import create_schema, make_engine, make_session_factory
from vehicle_intelligence.models import AuctionLot
from vehicle_intelligence.services import notification as svc
from vehicle_intelligence.services.title import title_exclusion

HEADER = ("Lot URL,Lot #,Est. Retail value,Sale date,Year,Make,Model,Engine type,Cylinders,VIN,"
          "Title code,Odometer,Odometer description,Damage description,Current bid,My bid,Item number,"
          "Sale name,Auto grade,Sale light,Announcements\n")
WATCH = [VehicleSpec(id="gw", vehicle_type="motorcycle", brand="Honda", model="Gold Wing",
                     variants=["GL1800"], min_year=2018, max_mileage_miles=50000,
                     mileage_tolerance_miles=10000, active=True)]


def _row(lot, title):
    return (f'https://www.copart.com/lot/{lot},{lot},0,11/25/2026 06:00 pm GMT,2021,HONDA,GL1800,6,6,'
            f'aa9aa9999aa******,{title},"12,000 A",ACTUAL,FRONT END,"1,800 USD",0 USD,1,SALE,0.0,N/A,\n')


@pytest.mark.parametrize("title", ["SALVAGE VEHICLE TITLE", "CERT OF TITLE-SALVAGE", "Non-Repairable Certificate",
                                   "JUNK", "Certificate of Destruction"])
def test_excluded_titles(title):
    assert title_exclusion(title) is not None


@pytest.mark.parametrize("title", ["CERT OF TITLE", "CERT OF TITLE-REBUILT", None, ""])
def test_allowed_titles(title):
    assert title_exclusion(title) is None


def test_importer_rejects_salvage_title(tmp_path):
    p = tmp_path / "e.csv"
    p.write_text(HEADER + _row("111", "CERT OF TITLE") + _row("222", "SALVAGE VEHICLE TITLE"), encoding="utf-8-sig")
    rows, errors = parse_search_export(p)
    assert [r.lot_id for r in rows] == ["111"]
    assert errors == [(3, "salvage title: excluded (owner rule)")]


@pytest.fixture
def sf(tmp_path):
    eng = make_engine(f"sqlite:///{(tmp_path / 't.db').as_posix()}")
    create_schema(eng)
    yield make_session_factory(eng)
    eng.dispose()


def _store(sf, lot_id, title):
    with sf() as s:
        s.add(AuctionLot(platform_id="copart_us", lot_id=lot_id, country="US", make="HONDA", model="GL1800",
                         year=2021, mileage_miles=12000, title_type=title, vehicle_type="motorcycle",
                         status="listed", currency="USD", vin="aa9aa9999aa******",
                         auction_date=datetime(2026, 11, 25, 18, tzinfo=timezone.utc),
                         source_url=f"https://www.copart.com/lot/{lot_id}"))
        s.commit()


def test_purge_removes_stored_salvage_lots(sf):
    _store(sf, "111", "CERT OF TITLE")
    _store(sf, "222", "CERT OF TITLE-SALVAGE")
    assert discard_excluded(sf, mileage_cap=60000) == 1
    with sf() as s:
        assert [l.lot_id for l in s.query(AuctionLot).all()] == ["111"]


def test_flag_refuses_salvage_lot(sf):
    _store(sf, "222", "SALVAGE VEHICLE TITLE")
    with sf() as s, pytest.raises(svc.NotificationError, match="salvage title"):
        svc.flag_lot(s, "222", WATCH)
