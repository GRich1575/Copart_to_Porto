from decimal import Decimal

import pytest

from vehicle_intelligence.collectors.local.local_listing_import import import_listings, parse_csv
from vehicle_intelligence.core.config import VehicleSpec, load_config
from vehicle_intelligence.core.database import create_schema, make_engine, make_session_factory
from vehicle_intelligence.models import CollectorRun, LocalListing
from vehicle_intelligence.services.comparables import comparable_prices

HEADER = "source,external_id,make,model,year,mileage_km,price,currency,source_url\n"
SOURCES = {"standvirtual_pt", "olx_pt"}
SPEC = VehicleSpec(id="gw", vehicle_type="motorcycle", brand="Honda", model="Gold Wing",
                   variants=["GL1800"], min_year=2018, max_mileage_miles=50000,
                   mileage_tolerance_miles=10000, active=True)


@pytest.fixture
def sf(tmp_path):
    eng = make_engine(f"sqlite:///{(tmp_path / 'l.db').as_posix()}")
    create_schema(eng)
    yield make_session_factory(eng)
    eng.dispose()


def _csv(tmp_path, *lines, name="l.csv"):
    p = tmp_path / name
    p.write_text(HEADER + "".join(l + "\n" for l in lines), encoding="utf-8-sig")
    return p


def test_repo_config_has_portugal_and_local_platforms():
    cfg = load_config(env={})
    assert any(c.code == "PT" and c.currency == "EUR" for c in cfg.countries)
    kinds = {p.id: p.kind for p in cfg.platforms}
    assert kinds["standvirtual_pt"] == "local_listing" and kinds["olx_pt"] == "local_listing"
    assert all(not p.enabled for p in cfg.platforms if p.kind == "local_listing")


def test_valid_rows_parsed_and_unknown_source_rejected(tmp_path):
    p = _csv(tmp_path,
             "standvirtual_pt,1,Honda,GL1800,2019,45000,9500,EUR,https://x/1",
             "copart_us,2,Honda,GL1800,2019,45000,9500,EUR,https://x/2",   # not a local source
             "olx_pt,3,Honda,GL1800,2019,45000,9500,USD,https://x/3")      # wrong currency
    rows, errors = parse_csv(p, SOURCES)
    assert [r.external_id for r in rows] == ["1"]
    assert [line for line, _ in errors] == [3, 4]


def test_price_with_comma_decimal_parsed(tmp_path):
    rows, errors = parse_csv(_csv(tmp_path, "olx_pt,4,Honda,GL1800,2020,30000,\"9.500,50\",EUR,"), SOURCES)
    assert errors == [] and rows[0].price == Decimal("9500.50")


def test_import_upserts_and_records_run(tmp_path, sf):
    p = _csv(tmp_path, "olx_pt,1,Honda,GL1800,2019,45000,9500,EUR,")
    assert import_listings(p, sf, SOURCES)[0] == 1
    import_listings(p, sf, SOURCES)  # rerun: no duplicate
    with sf() as s:
        assert s.query(LocalListing).count() == 1
        assert s.query(CollectorRun).filter_by(job="local_listing_import", status="success").count() == 2


def test_all_rows_invalid_raises(tmp_path, sf):
    with pytest.raises(ValueError, match="no valid rows"):
        import_listings(_csv(tmp_path, "copart_us,1,Honda,GL1800,2019,1,9,EUR,"), sf, SOURCES)


def test_comparables_respect_watchlist_and_km_to_miles_cap(tmp_path, sf):
    p = _csv(tmp_path,
             "olx_pt,1,Honda,GL1800,2019,45000,9500,EUR,",     # in: 27 962 mi
             "olx_pt,2,Honda,GL1800,2019,96000,8000,EUR,",     # in: 59 650 mi (just under 60 000)
             "olx_pt,3,Honda,GL1800,2019,97000,7000,EUR,",     # out: 60 285 mi > 60 000
             "olx_pt,4,Honda,GL1800,2017,20000,6000,EUR,",     # out: year < 2018
             "olx_pt,5,Honda,CBR600,2020,20000,5000,EUR,",     # out: different model
             "olx_pt,6,Honda,GL1800,2020,,4000,EUR,")          # out: mileage unknown
    import_listings(p, sf, SOURCES)
    with sf() as s:
        prices = sorted(comparable_prices(s, SPEC))
    assert prices == [Decimal("8000"), Decimal("9500")]
