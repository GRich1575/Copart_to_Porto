"""Fees and import rules by country (Business_Model.txt items 3 and 4). Every row carries its source."""

from __future__ import annotations

from datetime import date

from sqlalchemy import JSON, Boolean, Date, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from vehicle_intelligence.models.base import Base


class FeeRule(Base):
    __tablename__ = "fee_rule"

    id: Mapped[int] = mapped_column(primary_key=True)
    country: Mapped[str] = mapped_column(String(2))
    category: Mapped[str] = mapped_column(String(32))  # customs | processing | registration | port | other
    name: Mapped[str] = mapped_column(String(200))
    amount: Mapped[float | None] = mapped_column(Numeric(12, 2))
    percent: Mapped[float | None] = mapped_column(Numeric(6, 3))
    currency: Mapped[str | None] = mapped_column(String(3))
    applies_to: Mapped[dict] = mapped_column(JSON, default=dict)  # vehicle_type, engine_cc range, ...
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    source: Mapped[str] = mapped_column(String(500))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)


class ImportRule(Base):
    __tablename__ = "import_rule"

    id: Mapped[int] = mapped_column(primary_key=True)
    origin_country: Mapped[str] = mapped_column(String(2))
    destination_country: Mapped[str] = mapped_column(String(2))
    topic: Mapped[str] = mapped_column(String(32))  # import | repair | register | resell
    allowed: Mapped[bool] = mapped_column(Boolean)
    conditions: Mapped[str | None] = mapped_column(String(1000))
    title_restrictions: Mapped[str | None] = mapped_column(String(500))
    source: Mapped[str] = mapped_column(String(500))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
