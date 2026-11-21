"""Import owner-exported Portugal listings. Usage:
  python scripts/import_local_listings.py --file data/raw/local/<export>.csv [--url URL]
Known sources come from config/platforms.yaml (kind: local_listing).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from vehicle_intelligence.collectors.local.local_listing_import import import_listings
from vehicle_intelligence.core.config import load_config
from vehicle_intelligence.core.database import create_schema, make_engine, make_session_factory
from vehicle_intelligence.core.logging import setup_logging


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--url", help="SQLAlchemy URL override")
    args = parser.parse_args(argv)

    cfg = load_config()
    setup_logging(cfg.settings.log_level, Path(cfg.settings.log_dir))
    engine = make_engine(args.url or cfg.settings.database_url)
    create_schema(engine)
    known = {p.id for p in cfg.platforms if p.kind == "local_listing"}
    try:
        accepted, rejected = import_listings(args.file, make_session_factory(engine), known)
    except ValueError as exc:
        print(f"import: {exc}")
        return 1
    print(f"accepted: {accepted}  rejected: {len(rejected)}")
    for line, msg in rejected:
        print(f"  line {line}: {msg}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
