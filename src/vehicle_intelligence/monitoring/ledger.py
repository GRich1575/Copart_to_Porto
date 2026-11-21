"""Run ledger: every collector job writes one collector_run row per execution."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from vehicle_intelligence.core.logging import get_logger
from vehicle_intelligence.models import CollectorRun
from vehicle_intelligence.models.base import utcnow

log = get_logger("ledger")


@dataclass
class RunHandle:
    id: int
    job: str
    rows: int = 0


@contextmanager
def tracked_run(session_factory: sessionmaker[Session], job: str) -> Iterator[RunHandle]:
    """Record a run of `job`. Set handle.rows inside the block. Exceptions are recorded and re-raised."""
    with session_factory() as s:
        run = CollectorRun(job=job, status="running", started_at=utcnow(), rows=0)
        s.add(run)
        s.commit()
        handle = RunHandle(id=run.id, job=job)
    try:
        yield handle
    except Exception as exc:
        _finish(session_factory, handle.id, "failed", handle.rows, f"{type(exc).__name__}: {exc}")
        log.error("job failed", extra={"extra_fields": {"job": job, "error": str(exc)}})
        raise
    else:
        _finish(session_factory, handle.id, "success", handle.rows, None)
        log.info("job finished", extra={"extra_fields": {"job": job, "rows": handle.rows}})


def _finish(session_factory: sessionmaker[Session], run_id: int, status: str, rows: int, error: str | None) -> None:
    with session_factory() as s:
        run: CollectorRun = s.get(CollectorRun, run_id)
        run.status = status
        run.rows = rows
        run.error = error
        run.finished_at = utcnow()
        s.commit()


def recent_runs(session: Session, job: str, limit: int) -> list[CollectorRun]:
    stmt = (
        select(CollectorRun)
        .where(CollectorRun.job == job)
        .order_by(CollectorRun.started_at.desc(), CollectorRun.id.desc())
        .limit(limit)
    )
    return list(session.scalars(stmt))


def as_aware(dt: datetime | None) -> datetime | None:
    """SQLite drops tzinfo; treat stored naive datetimes as UTC."""
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=utcnow().tzinfo)
