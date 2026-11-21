"""Auction lots (Business_Model.txt items 1 and 7): current and finished auctions."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from vehicle_intelligence.models.base import Base, utcnow


class AuctionLot(Base):
    __tablename__ = "auction_lot"
    __table_args__ = (UniqueConstraint("platform_id", "lot_id", name="platform_lot"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    platform_id: Mapped[str] = mapped_column(String(64))
    lot_id: Mapped[str] = mapped_column(String(64))
    country: Mapped[str] = mapped_column(String(2))
    vin: Mapped[str | None] = mapped_column(String(32))
    vehicle_type: Mapped[str | None] = mapped_column(String(32))
    make: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(64))
    year: Mapped[int | None] = mapped_column(Integer)
    mileage_miles: Mapped[int | None] = mapped_column(Integer)
    damage_type: Mapped[str | None] = mapped_column(String(64))
    title_type: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16))  # listed | sold | unsold | historical
    auction_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_bid: Mapped[float | None] = mapped_column(Numeric(12, 2))
    final_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3))
    source_url: Mapped[str | None] = mapped_column(String(500))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
