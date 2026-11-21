"""Local used-vehicle listings (Business_Model.txt item 2): actual local selling prices."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from vehicle_intelligence.models.base import Base, utcnow


class LocalListing(Base):
    __tablename__ = "local_listing"
    __table_args__ = (Index("ix_local_listing_make_model_year", "make", "model", "year"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    platform_id: Mapped[str] = mapped_column(String(64))
    external_id: Mapped[str] = mapped_column(String(64))
    country: Mapped[str] = mapped_column(String(2))
    make: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(64))
    year: Mapped[int | None] = mapped_column(Integer)
    mileage_km: Mapped[int | None] = mapped_column(Integer)
    price: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3))
    source_url: Mapped[str | None] = mapped_column(String(500))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
