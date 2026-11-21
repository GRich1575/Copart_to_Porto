"""Shipping quotes (Business_Model.txt item 5, indirect fees)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from vehicle_intelligence.models.base import Base, utcnow


class ShipmentQuote(Base):
    __tablename__ = "shipment_quote"

    id: Mapped[int] = mapped_column(primary_key=True)
    carrier: Mapped[str] = mapped_column(String(120))
    origin_port: Mapped[str] = mapped_column(String(120))
    destination_port: Mapped[str] = mapped_column(String(120))
    container_type: Mapped[str | None] = mapped_column(String(32))
    load_cost: Mapped[float | None] = mapped_column(Numeric(12, 2))
    freight_cost: Mapped[float] = mapped_column(Numeric(12, 2))
    unload_cost: Mapped[float | None] = mapped_column(Numeric(12, 2))
    last_mile_cost: Mapped[float | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3))
    quoted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
