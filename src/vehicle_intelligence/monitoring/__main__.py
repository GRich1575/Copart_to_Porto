"""CLI: python -m vehicle_intelligence.monitoring check [--config-dir DIR] [--url URL]

Exit codes (for Windows Task Scheduler / cron): 0 = OK, 1 = WARNING, 2 = CRITICAL.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from vehicle_intelligence.core.config import DEFAULT_CONFIG_DIR, load_config
from vehicle_intelligence.core.database import make_engine, make_session_factory
from vehicle_intelligence.core.logging import get_logger, setup_logging
from vehicle_intelligence.monitoring.health import Level, evaluate, worst

log = get_logger("health")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vehicle_intelligence.monitoring")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="evaluate collector health and print findings")
    check.add_argument("--config-dir", type=Path, default=DEFAULT_CONFIG_DIR)
    check.add_argument("--url", help="database URL override")
    args = parser.parse_args(argv)

    cfg = load_config(args.config_dir)
    setup_logging(cfg.settings.log_level, Path(cfg.settings.log_dir))
    url = args.url or cfg.settings.database_url
    findings = evaluate(make_session_factory(make_engine(url)), cfg.settings)

    for f in findings:
        log.log(
            40 if f.level == Level.CRITICAL else 30 if f.level == Level.WARNING else 20,
            f.message,
            extra={"extra_fields": {"check": f.check, "job": f.job, "level": f.level.name}},
        )
    result = worst(findings)
    print(f"monitoring status: {result.name}")
    return int(result)


if __name__ == "__main__":
    sys.exit(main())
