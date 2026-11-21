"""Create the database schema. Usage: python scripts/init_db.py [--url URL]"""

from __future__ import annotations

import argparse
import sys

from vehicle_intelligence.core.config import load_config
from vehicle_intelligence.core.database import create_schema, make_engine


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", help="SQLAlchemy URL (default: settings / DATABASE_URL)")
    args = parser.parse_args(argv)
    url = args.url or load_config().settings.database_url
    tables = create_schema(make_engine(url))
    print(f"schema ready: {', '.join(tables)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
