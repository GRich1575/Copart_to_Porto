import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from vehicle_intelligence.core.config import DEFAULT_CONFIG_DIR, load_config

REPO_CONFIG = DEFAULT_CONFIG_DIR


@pytest.fixture
def cfg_dir(tmp_path: Path) -> Path:
    d = tmp_path / "config"
    shutil.copytree(REPO_CONFIG, d)
    return d


def test_repo_config_loads():
    cfg = load_config(REPO_CONFIG, env={})
    assert cfg.watchlist[0].brand == "Honda"
    assert cfg.watchlist[0].max_mileage_miles == 50000
    assert cfg.watchlist[0].min_year == 2018
    assert cfg.platforms[0].enabled is False
    assert cfg.settings.monitoring.max_job_age_hours > 0


def test_env_overrides_database_url_and_log_level(cfg_dir):
    cfg = load_config(cfg_dir, env={"DATABASE_URL": "postgresql+psycopg://u@h/db", "LOG_LEVEL": "debug"})
    assert cfg.settings.database_url == "postgresql+psycopg://u@h/db"
    assert cfg.settings.log_level == "DEBUG"


def test_missing_file_raises(cfg_dir):
    (cfg_dir / "countries.yaml").unlink()
    with pytest.raises(FileNotFoundError):
        load_config(cfg_dir, env={})


def test_watchlist_rejects_bad_mileage(cfg_dir):
    (cfg_dir / "vehicle_watchlist.yaml").write_text(
        "vehicles:\n  - id: x\n    vehicle_type: motorcycle\n    brand: Honda\n    model: GW\n"
        "    min_year: 2018\n    max_mileage_miles: 0\n",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError):
        load_config(cfg_dir, env={})


def test_watchlist_rejects_duplicate_ids(cfg_dir):
    entry = "  - id: same\n    vehicle_type: car\n    brand: A\n    model: B\n    min_year: 2000\n    max_mileage_miles: 1\n"
    (cfg_dir / "vehicle_watchlist.yaml").write_text("vehicles:\n" + entry + entry, encoding="utf-8")
    with pytest.raises(ValidationError, match="duplicate watchlist ids"):
        load_config(cfg_dir, env={})


def test_platform_with_unknown_country_rejected(cfg_dir):
    (cfg_dir / "platforms.yaml").write_text(
        "platforms:\n  - id: p\n    name: P\n    country: DE\n    kind: auction\n", encoding="utf-8"
    )
    with pytest.raises(ValidationError, match="unknown countries"):
        load_config(cfg_dir, env={})
