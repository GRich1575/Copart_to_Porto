"""Proxy-dealer notification queue. Minimal by design: lot number, auction date, lot link only."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from vehicle_intelligence.models.base import Base, utcnow


class ProxyNotification(Base):
    __tablename__ = "proxy_notification"

    id: Mapped[int] = mapped_column(primary_key=True)
    auction_lot_id: Mapped[int] = mapped_column(ForeignKey("auction_lot.id"), unique=True)
    lot_id: Mapped[str] = mapped_column(String(64))
    lot_url: Mapped[str | None] = mapped_column(String(500))
    auction_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    flagged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
