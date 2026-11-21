"""Flag a reviewed lot as eligible for restoration and queue the proxy notification.

The eligibility decision is the owner's manual review. This service only enforces guard rails:
- the lot must be stored (so the title, VIN and cap rules from the import already applied);
- the stored lot must still match an active watchlist entry (type, brand, model, year, mileage cap);
- each lot is queued at most once.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from vehicle_intelligence.core.config import VehicleSpec
from vehicle_intelligence.models import AuctionLot, ProxyNotification
from vehicle_intelligence.models.base import utcnow
from vehicle_intelligence.monitoring.ledger import as_aware
from vehicle_intelligence.services.title import title_exclusion
from vehicle_intelligence.services.vehicle_matching import VehicleFacts, match_watchlist


class NotificationError(ValueError):
    pass


def _facts(lot: AuctionLot) -> VehicleFacts:
    return VehicleFacts(
        vehicle_type=lot.vehicle_type,
        make=lot.make,
        model=lot.model,
        year=lot.year,
        mileage_miles=lot.mileage_miles,
    )


def flag_lot(session: Session, lot_id: str, watchlist: list[VehicleSpec], platform_id: str = "copart_us",
             now: datetime | None = None) -> ProxyNotification:
    lot = session.scalar(select(AuctionLot).where(AuctionLot.platform_id == platform_id,
                                                  AuctionLot.lot_id == lot_id))
    if lot is None:
        raise NotificationError(f"lot {lot_id} is not stored")
    if not (lot.title_type or "").strip():
        raise NotificationError(f"lot {lot_id} has no title: excluded (owner rule)")
    reason = title_exclusion(lot.title_type)
    if reason:
        raise NotificationError(f"lot {lot_id}: {reason}")
    if not match_watchlist(_facts(lot), watchlist):
        raise NotificationError(f"lot {lot_id} does not match an active watchlist entry")
    existing = session.scalar(select(ProxyNotification).where(ProxyNotification.auction_lot_id == lot.id))
    if existing is not None:
        raise NotificationError(f"lot {lot_id} is already queued")
    note = ProxyNotification(
        auction_lot_id=lot.id,
        lot_id=lot.lot_id,
        lot_url=lot.source_url,
        auction_date=lot.auction_date,
        flagged_at=now or utcnow(),
    )
    session.add(note)
    session.commit()
    return note


def pending(session: Session) -> list[tuple[ProxyNotification, datetime | None]]:
    """Unsent notifications in dispatch order, with the lot's current auction date.

    Priority: lots with an auction date first (earliest date first), then the waiting list
    (no date yet, in flag order). Dates are read from the lot at query time, so a waiting lot
    moves up as soon as a later import gives it a date.
    """
    rows = session.execute(
        select(ProxyNotification, AuctionLot.auction_date)
        .join(AuctionLot, AuctionLot.id == ProxyNotification.auction_lot_id)
        .where(ProxyNotification.sent_at.is_(None))
    ).all()
    return sorted(
        ((note, as_aware(date)) for note, date in rows),
        key=lambda r: (r[1] is None, r[1] or datetime.max.replace(tzinfo=timezone.utc), r[0].flagged_at, r[0].id),
    )


def is_waiting(date: datetime | None) -> bool:
    return date is None


def mark_sent(session: Session, ids: list[int], now: datetime | None = None) -> int:
    notes = list(session.scalars(select(ProxyNotification).where(ProxyNotification.id.in_(ids))))
    for n in notes:
        n.sent_at = now or utcnow()
    session.commit()
    return len(notes)
