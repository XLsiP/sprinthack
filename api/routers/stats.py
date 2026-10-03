from datetime import date
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


def _next_months(start: date, count: int) -> list[str]:
    months = []
    year, month = start.year, start.month
    for _ in range(count):
        months.append("%04d-%02d" % (year, month))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return months


@router.get("/stats", response_model=StatsOut)
def stats(
    manager: Optional[str] = None,
    department: Optional[str] = None,
    facility: Optional[str] = None,
    db: Session = Depends(get_db),
) -> StatsOut:
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
    months = dict.fromkeys(_next_months(today, 12), 0)
    for (expires,) in db.execute(scoped(select(Credential.expires_date)).where(Credential.expires_date >= today)):
        key = expires.strftime("%Y-%m")
        if key in months:
            months[key] += 1

    return StatsOut(
        associates=db.scalar(filter_associates(select(func.count(Associate.id)), manager, department, facility)) or 0,
        credentials=sum(by_status.values()),
        unverified=db.scalar(scoped(select(func.count(Credential.id))).where(~Credential.verifications.any())) or 0,
        by_status=by_status,
        by_facility=[
            FacilityStats(facility=f, total=sum(c.values()), by_status=c) for f, c in sorted(facilities.items())
        ],
        timeline=[TimelinePoint(month=m, count=n) for m, n in months.items()],
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
