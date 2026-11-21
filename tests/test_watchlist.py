from vehicle_intelligence.core.config import VehicleSpec
from vehicle_intelligence.services.vehicle_matching import VehicleFacts, match_vehicle, match_watchlist

SPEC = VehicleSpec(
    id="gw", vehicle_type="motorcycle", brand="Honda", model="Gold Wing",
    variants=["GL1800", "F6B"], min_year=2018, max_mileage_miles=50000,
)


def _facts(**over):
    data = dict(vehicle_type="motorcycle", make="HONDA", model="GOLD WING", year=2019,
                mileage_miles=12000, description="")
    data.update(over)
    return VehicleFacts(**data)


def test_matches_within_all_limits_case_insensitive():
    r = match_vehicle(_facts(), SPEC)
    assert r.matched and r.reasons == ()


def test_matches_by_variant_in_description():
    r = match_vehicle(_facts(model="GL1800", description=""), SPEC)
    assert r.matched
    r2 = match_vehicle(_facts(model="Honda", description="Gold Wing F6B tour"), SPEC)
    assert r2.matched


def test_year_boundary_inclusive_and_below_rejected():
    assert match_vehicle(_facts(year=2018), SPEC).matched
    r = match_vehicle(_facts(year=2017), SPEC)
    assert not r.matched and "year 2017 < 2018" in r.reasons


def test_mileage_boundary_inclusive_and_above_rejected():
    assert match_vehicle(_facts(mileage_miles=50000), SPEC).matched
    r = match_vehicle(_facts(mileage_miles=50001), SPEC)
    assert not r.matched and "mileage 50001 > 50000" in r.reasons


def test_unknown_year_or_mileage_never_matches():
    r = match_vehicle(_facts(year=None, mileage_miles=None), SPEC)
    assert not r.matched
    assert "year unknown" in r.reasons and "mileage unknown" in r.reasons


def test_wrong_brand_type_or_model_rejected():
    assert "brand differs" in match_vehicle(_facts(make="Yamaha"), SPEC).reasons
    assert "vehicle type differs" in match_vehicle(_facts(vehicle_type="car"), SPEC).reasons
    r = match_vehicle(_facts(model="Africa Twin", description=""), SPEC)
    assert not r.matched and "model/variant not found in lot" in r.reasons


def test_watchlist_skips_inactive_entries():
    inactive = SPEC.model_copy(update={"id": "old", "active": False})
    results = match_watchlist(_facts(), [inactive, SPEC])
    assert [r.spec_id for r in results] == ["gw"]
