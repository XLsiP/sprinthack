"""The daily job: re-verify every credential, then run the alert sweep.

Runs once a day on a background APScheduler thread, and on demand through `POST /api/jobs/daily/run`.

Environment:
  SCHEDULER_ENABLED   "0" turns the schedule off (the manual endpoint still works). Default on.
  DAILY_JOB_HOUR      Hour of day to run, 0-23. Default 6.
  DAILY_JOB_MINUTE    Minute of the hour. Default 0.
  SCHEDULER_TIMEZONE  IANA time zone for the above. Default America/Indiana/Indianapolis.
  HR_EMAIL            HR recipient for alerts. Without it the alert sweep is skipped.
"""
import logging
import os
import threading
from collections import Counter
from datetime import datetime, timezone
from typing import Literal, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

import alerts
import verify
from db import SessionLocal
from models import Credential
from routers.deps import CREDENTIAL_LOAD
from schemas import AlertRunResult, DailyJobStatusOut, DailyRunOut

log = logging.getLogger(__name__)

JOB_ID = "daily"
DEFAULT_TIMEZONE = "America/Indiana/Indianapolis"

_lock = threading.Lock()  # one run at a time, whether scheduled or manual
_scheduler: Optional[BackgroundScheduler] = None
_last_run: Optional[DailyRunOut] = None  # kept in memory only; resets on restart


class AlreadyRunning(RuntimeError):
    pass


def run_daily_job(trigger: Literal["scheduled", "manual"] = "scheduled") -> DailyRunOut:
    """Re-verify every credential (which also refreshes each stored status), then send due alerts."""
    global _last_run
    if not _lock.acquire(blocking=False):
        raise AlreadyRunning("The daily job is already running")
    try:
        started_at = datetime.now(timezone.utc)
        results: Counter[str] = Counter()
        alert_result: Optional[AlertRunResult] = None
        alerts_skipped: Optional[str] = None
        with SessionLocal() as db:
            for credential in db.scalars(select(Credential).options(*CREDENTIAL_LOAD)):
                results[verify.run(db, credential, delay=False).result] += 1
            db.commit()

            hr_email = os.environ.get("HR_EMAIL", "").strip()
            if hr_email:
                alert_result = AlertRunResult(**alerts.run_alerts(db, hr_email))
                db.commit()
            else:
                alerts_skipped = "HR_EMAIL is not configured"
        _last_run = DailyRunOut(
            trigger=trigger,
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
            checked=sum(results.values()),
            by_result=dict(results),
            alerts=alert_result,
            alerts_skipped=alerts_skipped,
        )
        return _last_run
    finally:
        _lock.release()


def _scheduled_run() -> None:
    try:
        result = run_daily_job("scheduled")
        log.info("Daily job checked %d credentials", result.checked)
    except AlreadyRunning:
        log.warning("Daily job skipped: a run is already in progress")
    except Exception:
        log.exception("Daily job failed")


def start() -> None:
    """Start the background scheduler with the one daily job. Does nothing if disabled or already started."""
    global _scheduler
    if _scheduler is not None or os.environ.get("SCHEDULER_ENABLED", "1").strip().lower() in ("0", "false", "no"):
        return
    tz = os.environ.get("SCHEDULER_TIMEZONE", DEFAULT_TIMEZONE)
    trigger = CronTrigger(
        hour=int(os.environ.get("DAILY_JOB_HOUR", "6")), minute=int(os.environ.get("DAILY_JOB_MINUTE", "0")), timezone=tz
    )
    _scheduler = BackgroundScheduler(timezone=tz)
    _scheduler.add_job(_scheduled_run, trigger, id=JOB_ID, max_instances=1, coalesce=True)
    _scheduler.start()


def shutdown() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def status() -> DailyJobStatusOut:
    job = _scheduler.get_job(JOB_ID) if _scheduler is not None else None
    return DailyJobStatusOut(
        enabled=job is not None,
        next_run_at=job.next_run_time if job is not None else None,
        running=_lock.locked(),
        last_run=_last_run,
    )
