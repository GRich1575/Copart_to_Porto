import json
from datetime import datetime, timedelta, timezone

import pytest

from vehicle_intelligence.core.config import MonitoringSettings, Settings
from vehicle_intelligence.core.database import create_schema, make_engine, make_session_factory
from vehicle_intelligence.models import CollectorRun
from vehicle_intelligence.monitoring import Level, evaluate, tracked_run, worst
from vehicle_intelligence.monitoring.__main__ import main as monitoring_main

NOW = datetime(2026, 11, 21, 12, 0, tzinfo=timezone.utc)
JOB = "auction_collector"


def _settings(jobs=(JOB,)):
    return Settings(
        monitoring=MonitoringSettings(max_job_age_hours=26, max_failure_rate=0.5, failure_window=10),
        expected_jobs=list(jobs),
    )


@pytest.fixture
def sf(tmp_path):
    eng = make_engine(f"sqlite:///{(tmp_path / 'mon.db').as_posix()}")
    create_schema(eng)
    factory = make_session_factory(eng)
    yield factory
    eng.dispose()


def _add_runs(sf, statuses_and_ages_hours, job=JOB):
    """statuses_and_ages_hours: list of (status, hours_before_NOW), newest first."""
    with sf() as s:
        for status, hours in statuses_and_ages_hours:
            started = NOW - timedelta(hours=hours)
            s.add(CollectorRun(job=job, status=status, started_at=started,
                               finished_at=started, rows=1 if status == "success" else 0))
        s.commit()


def _checks(findings):
    return {(f.check, f.level) for f in findings}


def test_healthy_job_is_ok(sf):
    _add_runs(sf, [("success", 2), ("success", 26), ("failed", 30)])
    findings = evaluate(sf, _settings(), now=NOW)
    assert worst(findings) == Level.OK
    assert ("job_ok", Level.OK) in _checks(findings)


def test_job_never_ran_is_critical(sf):
    findings = evaluate(sf, _settings(), now=NOW)
    assert ("job_never_ran", Level.CRITICAL) in _checks(findings)
    assert worst(findings) == Level.CRITICAL


def test_stale_success_is_critical(sf):
    _add_runs(sf, [("success", 30)])
    findings = evaluate(sf, _settings(), now=NOW)
    assert ("job_stale", Level.CRITICAL) in _checks(findings)


def test_high_failure_rate_is_warning(sf):
    _add_runs(sf, [("failed", 1), ("failed", 2), ("failed", 3), ("success", 4), ("failed", 5), ("success", 6)])
    findings = evaluate(sf, _settings(), now=NOW)
    assert ("job_failure_rate", Level.WARNING) in _checks(findings)
    assert worst(findings) == Level.WARNING


def test_run_stuck_in_running_is_warning(sf):
    _add_runs(sf, [("running", 40), ("success", 1)])
    findings = evaluate(sf, _settings(), now=NOW)
    assert ("job_stuck", Level.WARNING) in _checks(findings)


def test_unreachable_database_is_critical_not_exception(tmp_path):
    bad = make_session_factory(make_engine(f"sqlite:///{(tmp_path / 'no' / 'such' / 'dir.db').as_posix()}"))
    findings = evaluate(bad, _settings(), now=NOW)
    assert findings and findings[0].check == "database" and findings[0].level == Level.CRITICAL


def test_tracked_run_records_success(sf):
    with tracked_run(sf, JOB) as run:
        run.rows = 7
    with sf() as s:
        row = s.query(CollectorRun).one()
        assert (row.job, row.status, row.rows, row.error) == (JOB, "success", 7, None)
        assert row.finished_at is not None


def test_tracked_run_records_failure_and_reraises(sf):
    with pytest.raises(RuntimeError, match="boom"):
        with tracked_run(sf, JOB):
            raise RuntimeError("boom")
    with sf() as s:
        row = s.query(CollectorRun).one()
        assert row.status == "failed"
        assert "RuntimeError: boom" in row.error


def test_cli_exit_code_follows_worst_level(tmp_path, sf):
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "settings.yaml").write_text(
        "log_dir: " + json.dumps((tmp_path / "logs").as_posix()) + "\n"
        "monitoring:\n  max_job_age_hours: 26\n  max_failure_rate: 0.5\n  failure_window: 10\n"
        "expected_jobs: [" + JOB + "]\n",
        encoding="utf-8",
    )
    from vehicle_intelligence.core.config import DEFAULT_CONFIG_DIR

    for name in ("countries.yaml", "platforms.yaml", "vehicle_watchlist.yaml"):
        (cfg_dir / name).write_text((DEFAULT_CONFIG_DIR / name).read_text(encoding="utf-8"), encoding="utf-8")

    db_url = f"sqlite:///{(tmp_path / 'cli.db').as_posix()}"
    create_schema(make_engine(db_url))
    # no runs yet -> job_never_ran -> CRITICAL (2)
    assert monitoring_main(["check", "--config-dir", str(cfg_dir), "--url", db_url]) == 2

    with tracked_run(make_session_factory(make_engine(db_url)), JOB) as run:
        run.rows = 1
    assert monitoring_main(["check", "--config-dir", str(cfg_dir), "--url", db_url]) == 0
