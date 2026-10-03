from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db import get_db
from models import Associate, Credential
from routers.deps import filter_associates
from schemas import FacilityStats, FiltersOut, StatsOut, TimelinePoint
from status import SEVERITY

router = APIRouter(tags=["stats"])


TIMELINE_DAYS = 90
TIMELINE_WEEKS = 13  # 13 weeks = days 0 through 90


@router.get("/stats", response_model=StatsOut)
def stats(
    manager: Optional[str] = None,
    department: Optional[str] = None,
    facility: Optional[str] = None,
    db: Session = Depends(get_db),
) -> StatsOut:
    """Counts for the dashboard, all scoped by the optional manager / department / facility filters.

    `timeline` is credentials expiring in the next 90 days, in 13 weekly buckets starting today.
    """
    def scoped(query):
        return filter_associates(query.join(Associate, Credential.associate_id == Associate.id), manager, department, facility)

    by_status = dict.fromkeys(SEVERITY, 0)
    facilities: dict[str, dict[str, int]] = {}
    rows = db.execute(
        scoped(select(Associate.facility, Credential.status, func.count())).group_by(Associate.facility, Credential.status)
    )
    for fac, status, count in rows:
        by_status[status] += count
        facilities.setdefault(fac, dict.fromkeys(SEVERITY, 0))[status] = count

    today = date.today()
    weeks = [0] * TIMELINE_WEEKS
    upcoming = scoped(select(Credential.expires_date, func.count())).where(
        Credential.expires_date.between(today, today + timedelta(days=TIMELINE_DAYS))
    )
    for expires, count in db.execute(upcoming.group_by(Credential.expires_date)):
        weeks[(expires - today).days // 7] += count

    return StatsOut(
        associates=db.scalar(filter_associates(select(func.count(Associate.id)), manager, department, facility)) or 0,
        credentials=sum(by_status.values()),
        unverified=db.scalar(scoped(select(func.count(Credential.id))).where(~Credential.verifications.any())) or 0,
        by_status=by_status,
        by_facility=[
            FacilityStats(facility=f, total=sum(c.values()), by_status=c) for f, c in sorted(facilities.items())
        ],
        timeline=[
            TimelinePoint(start=today + timedelta(days=7 * i), end=today + timedelta(days=7 * i + 6), count=n)
            for i, n in enumerate(weeks)
        ],
    )


@router.get("/filters", response_model=FiltersOut)
def filters(db: Session = Depends(get_db)) -> FiltersOut:
    """Distinct values for the dashboard filter dropdowns."""
    def distinct(column) -> list[str]:
        return list(db.scalars(select(column).distinct().order_by(column)))

    return FiltersOut(
        facilities=distinct(Associate.facility),
        departments=distinct(Associate.department),
        managers=distinct(Associate.manager_email),
    )
