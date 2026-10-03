"""Shared query helpers for the routers."""
from typing import Optional

from sqlalchemy import Select, case
from sqlalchemy.orm import selectinload

from models import Associate, Credential
from status import SEVERITY

CREDENTIAL_LOAD = (
    selectinload(Credential.associate),
    selectinload(Credential.credential_type),
    selectinload(Credential.verifications),
)
URGENCY = case({s: i for i, s in enumerate(SEVERITY)}, value=Credential.status)


def filter_associates(
    query: Select, manager: Optional[str], department: Optional[str], facility: Optional[str]
) -> Select:
    if manager:
        query = query.where(Associate.manager_email == manager)
    if department:
        query = query.where(Associate.department == department)
    if facility:
        query = query.where(Associate.facility == facility)
    return query
