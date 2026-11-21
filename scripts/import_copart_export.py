"""Import a Copart search-results CSV saved by the owner.

Usage:
  python scripts/import_copart_export.py --file data/raw/copart/<export>.csv [--vehicle-type motorcycle]
                                         [--url sqlite:///data/local.db]
Without --url the database from settings / DATABASE_URL is used.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from vehicle_intelligence.collectors.auctions.copart_search_export import discard_excluded, import_search_export
from vehicle_intelligence.core.config import load_config
from vehicle_intelligence.core.database import create_schema, make_engine, make_session_factory
from vehicle_intelligence.core.logging import setup_logging


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--vehicle-type", default=None, help="vehicle type of the search, e.g. motorcycle")
    parser.add_argument("--url", help="SQLAlchemy URL override")
    parser.add_argument("--discard-excluded", action="store_true",
                        help="also delete stored lots with no title or odometer above the watchlist cap")
    args = parser.parse_args(argv)

    cfg = load_config()
    setup_logging(cfg.settings.log_level, Path(cfg.settings.log_dir))
    engine = make_engine(args.url or cfg.settings.database_url)
    create_schema(engine)
    try:
        accepted, rejected = import_search_export(args.file, make_session_factory(engine), args.vehicle_type)
        print(f"accepted: {accepted}  rejected: {len(rejected)}")
        for line, msg in rejected:
            print(f"  line {line}: {msg}")
    except ValueError as exc:  # no valid rows: recorded as failed run; purge still applies
        print(f"import: {exc}")
    if args.discard_excluded:
        cap = max(v.mileage_cap_miles for v in cfg.watchlist if v.active)
        print(f"discarded stored lots: {discard_excluded(make_session_factory(engine), mileage_cap=cap)} (cap {cap} mi)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
