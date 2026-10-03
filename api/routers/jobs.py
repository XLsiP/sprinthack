from fastapi import APIRouter, HTTPException

import scheduler
from schemas import DailyJobStatusOut, DailyRunOut

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/daily", response_model=DailyJobStatusOut)
def daily_job_status() -> DailyJobStatusOut:
    """Whether the daily job is scheduled, when it runs next, and what the last run did."""
    return scheduler.status()


@router.post("/daily/run", response_model=DailyRunOut)
def run_daily_job() -> DailyRunOut:
    """Run the daily re-verification and alert sweep now (the admin button for the demo)."""
    try:
        return scheduler.run_daily_job("manual")
    except scheduler.AlreadyRunning:
        raise HTTPException(409, "The daily job is already running")
