from fastapi import APIRouter

from schemas import HealthOut

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    """Liveness check. Does not touch the database."""
    return HealthOut(status="ok")
