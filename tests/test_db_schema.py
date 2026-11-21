import os
from datetime import datetime, timezone

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from vehicle_intelligence.core.database import create_schema, make_engine, make_session_factory
from vehicle_intelligence.models import AuctionLot, Base, FeeRule

EXPECTED_TABLES = {
    "auction_lot",
    "local_listing",
    "fee_rule",
    "import_rule",
    "shipment_quote",
    "repair_estimate",
    "collector_run",
}


def _lot(**over):
    data = dict(
        platform_id="copart_us", lot_id="1", country="US", make="Honda", model="Gold Wing",
        year=2019, mileage_miles=12000, status="sold", currency="USD",
        auction_date=datetime(2026, 11, 1, tzinfo=timezone.utc), final_price=9000.0,
    )
    data.update(over)
    return AuctionLot(**data)


@pytest.fixture
def engine(tmp_path):
    eng = make_engine(f"sqlite:///{(tmp_path / 'schema.db').as_posix()}")
    create_schema(eng)
    yield eng
    eng.dispose()


def test_all_tables_created(engine):
    assert set(inspect(engine).get_table_names()) >= EXPECTED_TABLES


def test_create_schema_is_idempotent(engine):
    first = create_schema(engine)
    second = create_schema(engine)
    assert first == second


def test_auction_lot_unique_per_platform(engine):
    Session = make_session_factory(engine)
    with Session() as s:
        s.add(_lot())
        s.commit()
    with Session() as s:
        s.add(_lot())
        with pytest.raises(IntegrityError):
            s.commit()
    with Session() as s:
        s.add(_lot(platform_id="other_platform"))  # same lot id on another platform is allowed
        s.commit()


def test_fee_rule_json_roundtrip(engine):
    Session = make_session_factory(engine)
    with Session() as s:
        s.add(FeeRule(country="DE", category="customs", name="duty", percent=10.0,
                      applies_to={"vehicle_type": "motorcycle", "engine_cc_min": 800},
                      source="test", verified=False))
        s.commit()
    with Session() as s:
        rule = s.scalar(select(FeeRule).where(FeeRule.country == "DE"))
        assert rule.applies_to == {"vehicle_type": "motorcycle", "engine_cc_min": 800}
        assert rule.verified is False


def test_metadata_has_naming_convention():
    assert Base.metadata.naming_convention["pk"] == "pk_%(table_name)s"


@pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL not set")
def test_postgres_schema_roundtrip():
    eng = make_engine(os.environ["TEST_DATABASE_URL"])
    try:
        create_schema(eng)
        assert set(inspect(eng).get_table_names()) >= EXPECTED_TABLES
    finally:
        Base.metadata.drop_all(eng)
        eng.dispose()
