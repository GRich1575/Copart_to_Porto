from vehicle_intelligence.services.vin import check_digit, vin_status

VALID_NA = "1HGCM82633A004352"  # standard textbook VIN, check digit 3 at position 9


def test_check_digit_known_vin():
    assert check_digit(VALID_NA) == "3"


def test_valid_north_american_vin_ok():
    assert vin_status(VALID_NA) == "ok"


def test_wrong_check_digit_invalid():
    bad = VALID_NA[:8] + "4" + VALID_NA[9:]
    assert vin_status(bad) == "invalid"


def test_check_digit_x_case():
    # check digit X (remainder 10) must be matched exactly
    base = "1M8GDM9AXKP042788"  # textbook VIN with X at position 9
    assert vin_status(base) == "ok"


def test_wrong_length_or_forbidden_letters_invalid():
    assert vin_status("1HGCM82633A00435") == "invalid"    # 16 chars
    assert vin_status("1HGCM82633I004352") == "invalid"   # I is not allowed


def test_masked_missing_and_non_na_kept():
    assert vin_status("aa9aa9999aa******") == "masked"
    assert vin_status("") == "missing"
    assert vin_status(None) == "missing"
    # WMI starting with 9 (not North America): format only, no check digit
    assert vin_status("9BWZZZ377VT004251") == "ok"


def test_non_na_wrong_check_digit_not_rejected():
    non_na = "9BWZZZ377VT004251"
    assert vin_status(non_na) == "ok"


def test_partially_masked_vin_kept_not_invalid():
    partial = "1HGCM8263*A004352"  # one hidden digit: fails format, but masked => kept
    assert vin_status(partial) == "masked"
    assert vin_status("1HGCM82633A0043*2") == "masked"
