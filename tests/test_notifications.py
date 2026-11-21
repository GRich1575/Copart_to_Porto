from datetime import datetime, timezone

import pytest

from vehicle_intelligence.core.config import VehicleSpec
from vehicle_intelligence.core.database import create_schema, make_engine, make_session_factory
from vehicle_intelligence.models import AuctionLot, ProxyNotification
from vehicle_intelligence.services import notification as svc

WATCH = [VehicleSpec(id="gw", vehicle_type="motorcycle", brand="Honda", model="Gold Wing",
                     variants=["GL1800"], min_year=2018, max_mileage_miles=50000,
                     mileage_tolerance_miles=10000, active=True)]
AUCTION = datetime(2026, 11, 25, 18, 0, tzinfo=timezone.utc)


def _lot(**over):
    data = dict(platform_id="copart_us", lot_id="65038036", country="US", vehicle_type="motorcycle",
                make="HONDA", model="GL1800", year=2023, mileage_miles=14132, title_type="CERT OF TITLE",
                status="listed", currency="USD", auction_date=AUCTION,
                source_url="https://www.copart.com/lot/65038036")
    data.update(over)
    return AuctionLot(**data)


@pytest.fixture
def sf(tmp_path):
    eng = make_engine(f"sqlite:///{(tmp_path / 'n.db').as_posix()}")
    create_schema(eng)
    yield make_session_factory(eng)
    eng.dispose()


def _store(sf, **over):
    with sf() as s:
        s.add(_lot(**over))
        s.commit()


def test_flag_queues_minimal_fields(sf):
    _store(sf)
    with sf() as s:
        note = svc.flag_lot(s, "65038036", WATCH)
        assert note.lot_id == "65038036"
        assert note.auction_date.replace(tzinfo=timezone.utc) == AUCTION
        assert note.lot_url == "https://www.copart.com/lot/65038036"
        assert note.sent_at is None


def test_refuses_unknown_lot(sf):
    with sf() as s, pytest.raises(svc.NotificationError, match="not stored"):
        svc.flag_lot(s, "999", WATCH)


def test_refuses_lot_without_title(sf):
    _store(sf, lot_id="111", title_type=None)
    with sf() as s, pytest.raises(svc.NotificationError, match="no title"):
        svc.flag_lot(s, "111", WATCH)


def test_refuses_lot_outside_watchlist(sf):
    _store(sf, lot_id="222", mileage_miles=70879)  # over the 60 000 cap
    with sf() as s, pytest.raises(svc.NotificationError, match="does not match"):
        svc.flag_lot(s, "222", WATCH)


def test_each_lot_queued_once(sf):
    _store(sf)
    with sf() as s:
        svc.flag_lot(s, "65038036", WATCH)
    with sf() as s, pytest.raises(svc.NotificationError, match="already queued"):
        svc.flag_lot(s, "65038036", WATCH)


def test_pending_and_mark_sent(sf):
    _store(sf)
    _store(sf, lot_id="333", auction_date=None)
    with sf() as s:
        a = svc.flag_lot(s, "65038036", WATCH)
        b = svc.flag_lot(s, "333", WATCH)
        ids = [a.id, b.id]
    with sf() as s:
        assert [n.lot_id for n, _ in svc.pending(s)] == ["65038036", "333"]
        assert svc.mark_sent(s, [ids[0]]) == 1
    with sf() as s:
        assert [n.lot_id for n, _ in svc.pending(s)] == ["333"]
        assert s.query(ProxyNotification).filter(ProxyNotification.sent_at.is_not(None)).count() == 1


def _set_date(sf, lot_id, when):
    with sf() as s:
        lot = s.query(AuctionLot).filter_by(lot_id=lot_id).one()
        lot.auction_date = when
        s.commit()


def test_waiting_list_goes_below_dated_lots(sf):
    _store(sf, lot_id="W1", auction_date=None)   # flagged first, but undated
    _store(sf, lot_id="D2", auction_date=datetime(2026, 12, 9, 18, 0, tzinfo=timezone.utc))
    _store(sf, lot_id="D1", auction_date=datetime(2026, 11, 25, 18, 0, tzinfo=timezone.utc))
    _store(sf, lot_id="W2", auction_date=None)
    with sf() as s:
        for lot in ["W1", "D2", "D1", "W2"]:
            svc.flag_lot(s, lot, WATCH)
    with sf() as s:
        order = [(n.lot_id, svc.is_waiting(d)) for n, d in svc.pending(s)]
    # dated lots first by earliest date, then waiting list in flag order
    assert order == [("D1", False), ("D2", False), ("W1", True), ("W2", True)]


def test_waiting_lot_moves_up_when_date_appears(sf):
    _store(sf, lot_id="W1", auction_date=None)
    _store(sf, lot_id="D1", auction_date=datetime(2026, 11, 25, 18, 0, tzinfo=timezone.utc))
    with sf() as s:
        svc.flag_lot(s, "W1", WATCH)
        svc.flag_lot(s, "D1", WATCH)
    _set_date(sf, "W1", datetime(2026, 11, 20, 18, 0, tzinfo=timezone.utc))  # later import adds a date
    with sf() as s:
        assert [n.lot_id for n, _ in svc.pending(s)] == ["W1", "D1"]  # earlier date now first


def test_undated_lot_can_still_be_flagged(sf):
    _store(sf, lot_id="W9", auction_date=None)
    with sf() as s:
        note = svc.flag_lot(s, "W9", WATCH)
        assert note.lot_id == "W9"
