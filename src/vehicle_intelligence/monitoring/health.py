"""Health evaluation of collectors and the database. Pure rules over the run ledger; no LLM."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import IntEnum

from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

from vehicle_intelligence.core.config import Settings
from vehicle_intelligence.models import CollectorRun
from vehicle_intelligence.models.base import utcnow
from vehicle_intelligence.monitoring.ledger import as_aware, recent_runs


class Level(IntEnum):
    OK = 0
    WARNING = 1
    CRITICAL = 2


@dataclass(frozen=True)
class Finding:
    level: Level
    check: str  # database | job_stale | job_never_ran | job_failure_rate | job_stuck | job_ok
    job: str | None
    message: str


def evaluate(session_factory: sessionmaker[Session], settings: Settings, now: datetime | None = None) -> list[Finding]:
    """Return one or more findings. Never raises: an unreachable database is a CRITICAL finding."""
    now = now or utcnow()
    try:
        with session_factory() as s:
            s.execute(text("SELECT 1"))
            findings = [Finding(Level.OK, "database", None, "database reachable")]
            for job in settings.expected_jobs:
                findings.extend(_evaluate_job(s, job, settings, now))
            return findings
    except Exception as exc:  # noqa: BLE001 - monitoring must report, not crash
        return [Finding(Level.CRITICAL, "database", None, f"database check failed: {type(exc).__name__}: {exc}")]


def _evaluate_job(s: Session, job: str, settings: Settings, now: datetime) -> list[Finding]:
    m = settings.monitoring
    max_age = timedelta(hours=m.max_job_age_hours)
    runs = recent_runs(s, job, m.failure_window)
    if not runs:
        return [Finding(Level.CRITICAL, "job_never_ran", job, "no runs recorded")]

    out: list[Finding] = []
    successes = [r for r in runs if r.status == "success"]
    last_success = as_aware(successes[0].started_at) if successes else None
    if last_success is None:
        out.append(Finding(Level.CRITICAL, "job_stale", job, "no successful run in the monitoring window"))
    elif now - last_success > max_age:
        out.append(Finding(Level.CRITICAL, "job_stale", job,
                           f"last success {last_success.isoformat(timespec='minutes')} is older than {m.max_job_age_hours} h"))

    failed = sum(r.status == "failed" for r in runs)
    rate = failed / len(runs)
    if rate > m.max_failure_rate:
        out.append(Finding(Level.WARNING, "job_failure_rate", job,
                           f"{failed}/{len(runs)} recent runs failed (limit {m.max_failure_rate:.0%})"))

    stuck = [r for r in runs if r.status == "running" and now - as_aware(r.started_at) > max_age]
    if stuck:
        out.append(Finding(Level.WARNING, "job_stuck", job, f"{len(stuck)} run(s) still 'running' past {m.max_job_age_hours} h"))

    if not out:
        out.append(Finding(Level.OK, "job_ok", job, "on schedule, failure rate within limit"))
    return out


def worst(findings: list[Finding]) -> Level:
    return max((f.level for f in findings), default=Level.OK)
