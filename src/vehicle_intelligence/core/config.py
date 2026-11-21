"""Load and validate configuration from config/*.yaml and environment variables."""

from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path
from typing import Literal, Mapping

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

PACKAGE_ROOT = Path(__file__).resolve().parents[3]  # repo root (src/vehicle_intelligence/core/config.py)
DEFAULT_CONFIG_DIR = PACKAGE_ROOT / "config"
DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres@localhost:5432/vehicle_intel"


class MonitoringSettings(BaseModel):
    max_job_age_hours: float = Field(gt=0)
    max_failure_rate: float = Field(gt=0, le=1)
    failure_window: int = Field(ge=1)


class Settings(BaseModel):
    database_url: str = DEFAULT_DATABASE_URL
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_dir: str = "data/logs"
    monitoring: MonitoringSettings
    expected_jobs: list[str] = Field(default_factory=list)


class VehicleSpec(BaseModel):
    id: str = Field(min_length=1)
    vehicle_type: Literal["motorcycle", "car", "truck", "other"]
    brand: str = Field(min_length=1)
    model: str = Field(min_length=1)
    variants: list[str] = Field(default_factory=list)
    min_year: int = Field(ge=1900, le=2100)
    max_mileage_miles: int = Field(gt=0)
    # Extra miles admitted above max_mileage_miles. Owner rule: hard cap = max + tolerance (60 000 for GL1800).
    mileage_tolerance_miles: int = Field(default=0, ge=0, le=10000)
    active: bool = True

    @property
    def mileage_cap_miles(self) -> int:
        return self.max_mileage_miles + self.mileage_tolerance_miles


class Watchlist(BaseModel):
    vehicles: list[VehicleSpec]

    @model_validator(mode="after")
    def _unique_ids(self) -> "Watchlist":
        ids = [v.id for v in self.vehicles]
        dups = {i for i in ids if ids.count(i) > 1}
        if dups:
            raise ValueError(f"duplicate watchlist ids: {sorted(dups)}")
        return self


class Country(BaseModel):
    code: str = Field(pattern=r"^[A-Z]{2}$")
    name: str
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    role: Literal["origin", "destination"]


class Countries(BaseModel):
    countries: list[Country]


class Platform(BaseModel):
    id: str = Field(min_length=1)
    name: str
    country: str
    kind: Literal["auction", "local_listing", "historical"]
    enabled: bool = False


class Platforms(BaseModel):
    platforms: list[Platform]

    @model_validator(mode="after")
    def _unique_ids(self) -> "Platforms":
        ids = [p.id for p in self.platforms]
        dups = {i for i in ids if ids.count(i) > 1}
        if dups:
            raise ValueError(f"duplicate platform ids: {sorted(dups)}")
        return self


class Economics(BaseModel):
    """Money inputs for import economics (config/economics.yaml). All amounts are in `currency`."""

    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    resale_discount: Decimal = Field(default=Decimal("0.10"), ge=0, lt=1)
    min_edge: Decimal = Field(default=Decimal("1500"), ge=0)
    min_comparables: int = Field(default=3, ge=1)
    auction_fee_percent: Decimal = Field(default=Decimal("0"), ge=0, lt=1)
    auction_fee_fixed: Decimal = Field(default=Decimal("0"), ge=0)
    transport_to_port: Decimal = Field(default=Decimal("0"), ge=0)
    port_load: Decimal = Field(default=Decimal("0"), ge=0)
    container_shipping: Decimal = Field(default=Decimal("0"), ge=0)
    port_unload: Decimal = Field(default=Decimal("0"), ge=0)
    documents_fee: Decimal = Field(default=Decimal("0"), ge=0)
    last_mile: Decimal = Field(default=Decimal("0"), ge=0)
    customs_duty_percent: Decimal = Field(default=Decimal("0"), ge=0, lt=1)
    registration_fee: Decimal = Field(default=Decimal("0"), ge=0)


class AppConfig(BaseModel):
    settings: Settings
    countries: list[Country]
    platforms: list[Platform]
    watchlist: list[VehicleSpec]
    economics: Economics

    @field_validator("platforms")
    @classmethod
    def _platform_countries_known(cls, platforms: list[Platform], info) -> list[Platform]:
        codes = {c.code for c in info.data.get("countries", [])}
        unknown = {p.country for p in platforms if p.country not in codes}
        if unknown:
            raise ValueError(f"platforms reference unknown countries: {sorted(unknown)}")
        return platforms


def _read_yaml(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"config file missing: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path.name}: top level must be a mapping")
    return data


def load_config(config_dir: Path = DEFAULT_CONFIG_DIR, env: Mapping[str, str] | None = None) -> AppConfig:
    env = os.environ if env is None else env
    raw_settings = _read_yaml(config_dir / "settings.yaml")
    if env.get("DATABASE_URL"):
        raw_settings["database_url"] = env["DATABASE_URL"]
    if env.get("LOG_LEVEL"):
        raw_settings["log_level"] = env["LOG_LEVEL"].upper()
    settings = Settings.model_validate(raw_settings)
    countries = Countries.model_validate(_read_yaml(config_dir / "countries.yaml")).countries
    platforms = Platforms.model_validate(_read_yaml(config_dir / "platforms.yaml")).platforms
    watchlist = Watchlist.model_validate(_read_yaml(config_dir / "vehicle_watchlist.yaml")).vehicles
    economics = Economics.model_validate(_read_yaml(config_dir / "economics.yaml"))
    return AppConfig(
        settings=settings, countries=countries, platforms=platforms, watchlist=watchlist, economics=economics
    )
