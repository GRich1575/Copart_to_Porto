"""Proxy-dealer notifications for lots the owner reviewed as eligible.

Usage:
  python scripts/proxy_notifications.py flag LOT_ID [--url URL]   # queue one reviewed lot
  python scripts/proxy_notifications.py pending [--url URL]       # unsent: dated lots first, then WAITING (no date)
  python scripts/proxy_notifications.py sent ID [ID ...] [--url URL]  # mark as sent after you notify the dealer
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from vehicle_intelligence.core.config import load_config
from vehicle_intelligence.core.database import create_schema, make_engine, make_session_factory
from vehicle_intelligence.services import notification as svc


def _fmt_date(dt) -> str:
    return dt.strftime("%Y-%m-%d %H:%M UTC") if dt else "date not set"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", help="SQLAlchemy URL override")
    sub = parser.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("flag")
    f.add_argument("lot_id")
    sub.add_parser("pending")
    s = sub.add_parser("sent")
    s.add_argument("ids", type=int, nargs="+")
    args = parser.parse_args(argv)

    cfg = load_config()
    engine = make_engine(args.url or cfg.settings.database_url)
    create_schema(engine)
    sf = make_session_factory(engine)

    with sf() as s_:
        if args.cmd == "flag":
            try:
                note = svc.flag_lot(s_, args.lot_id, cfg.watchlist)
            except svc.NotificationError as exc:
                print(f"refused: {exc}")
                return 1
            print(f"queued #{note.id}: lot {note.lot_id}, {_fmt_date(note.auction_date)}, {note.lot_url}")
        elif args.cmd == "pending":
            rows = svc.pending(s_)
            if not rows:
                print("no pending notifications")
            for n, date in rows:
                tag = "WAITING" if svc.is_waiting(date) else "PRIORITY"
                print(f"#{n.id}\t{tag}\tlot {n.lot_id}\t{_fmt_date(date)}\t{n.lot_url}")
        elif args.cmd == "sent":
            print(f"marked sent: {svc.mark_sent(s_, args.ids)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
