"""Repair cost estimates (Business_Model.txt item 6)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from vehicle_intelligence.models.base import Base, utcnow


class RepairEstimate(Base):
    __tablename__ = "repair_estimate"

    id: Mapped[int] = mapped_column(primary_key=True)
    auction_lot_id: Mapped[int | None] = mapped_column(ForeignKey("auction_lot.id"))
    damage_type: Mapped[str] = mapped_column(String(64))
    parts_cost: Mapped[float] = mapped_column(Numeric(12, 2))
    labour_hours: Mapped[float] = mapped_column(Numeric(6, 2))
    labour_rate: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3))
    method: Mapped[str] = mapped_column(String(120))
    estimated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    year_hint: Mapped[int | None] = mapped_column(Integer)
