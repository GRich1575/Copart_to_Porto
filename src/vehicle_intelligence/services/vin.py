"""VIN status for lot rules (owner rule, 2026-11-21).

- missing : no VIN given                         -> kept (not a damage signal)
- masked  : contains '*' (Copart hides digits)   -> kept (not a damage signal)
- invalid : fully visible but malformed, i.e. not 17 chars, or characters I/O/Q,
            or (VIN starts with 1-5, North America) the check digit at position 9 is wrong
            -> excluded and discarded
- ok      : fully visible and valid
"""

from __future__ import annotations

import re
from typing import Literal

VinStatus = Literal["missing", "masked", "invalid", "ok"]

_FORMAT = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")
_WEIGHTS = (8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2)
_VALUE = {
    **{str(d): d for d in range(10)},
    "A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7, "H": 8,
    "J": 1, "K": 2, "L": 3, "M": 4, "N": 5, "P": 7, "R": 9,
    "S": 2, "T": 3, "U": 4, "V": 5, "W": 6, "X": 7, "Y": 8, "Z": 9,
}


def check_digit(vin: str) -> str:
    total = sum(_VALUE[c] * w for c, w in zip(vin, _WEIGHTS))
    rem = total % 11
    return "X" if rem == 10 else str(rem)


def vin_status(vin: str | None) -> VinStatus:
    v = (vin or "").strip().upper()
    if not v:
        return "missing"
    if "*" in v:
        return "masked"
    if not _FORMAT.match(v):
        return "invalid"
    if v[0] in "12345" and v[8] != check_digit(v):
        return "invalid"
    return "ok"
