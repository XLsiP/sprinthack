from fastapi import APIRouter, Request

import access
from schemas import AccessOut, HealthOut

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    """Liveness check. Does not touch the database."""
    return HealthOut(status="ok")


@router.get("/access", response_model=AccessOut)
def access_status(request: Request) -> AccessOut:
    """Whether an access password is required, and whether this request supplied the right one."""
    return AccessOut(required=bool(access.password()), granted=access.granted(request))
