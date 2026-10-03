"""Pydantic response models. Keep web/lib/api.ts in sync with this file."""
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict

import status as status_rules
from models import Associate, Credential

CredentialStatus = Literal[
    "valid", "expiring_90", "expiring_60", "expiring_30", "expired", "verification_failed", "excluded"
]
VerificationResultName = Literal["verified", "not_found", "excluded", "mismatch", "error"]


class HealthOut(BaseModel):
    status: Literal["ok"]


class VerificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    credential_id: int
    checked_at: datetime
    source: str
    result: VerificationResultName
    details: dict
    evidence_path: Optional[str]


class CredentialOut(BaseModel):
    id: int
    associate_id: int
    associate_name: str
    department: str
    facility: str
    credential_type: str
    issuing_source: str
    verify_method: str
    number: Optional[str]
    issued_date: Optional[date]
    expires_date: Optional[date]
    status: CredentialStatus
    days_left: Optional[int]
    last_verification: Optional[VerificationOut]  # None = not yet verified

    @classmethod
    def from_model(cls, c: Credential) -> "CredentialOut":
        return cls(
            id=c.id,
            associate_id=c.associate_id,
            associate_name=c.associate.name,
            department=c.associate.department,
            facility=c.associate.facility,
            credential_type=c.credential_type.name,
            issuing_source=c.credential_type.issuing_source,
            verify_method=c.credential_type.verify_method,
            number=c.number,
            issued_date=c.issued_date,
            expires_date=c.expires_date,
            status=c.status,
            days_left=status_rules.days_left(c.expires_date),
            last_verification=VerificationOut.model_validate(c.verifications[-1]) if c.verifications else None,
        )


class AssociateOut(BaseModel):
    id: int
    name: str
    npi: Optional[str]
    role: str
    department: str
    facility: str
    state: str
    manager_email: str
    worst_status: Optional[CredentialStatus]
    credential_count: int

    @classmethod
    def fields_from(cls, a: Associate) -> dict:
        return dict(
            id=a.id, name=a.name, npi=a.npi, role=a.role, department=a.department, facility=a.facility,
            state=a.state, manager_email=a.manager_email,
            worst_status=status_rules.worst([c.status for c in a.credentials]),
            credential_count=len(a.credentials),
        )

    @classmethod
    def from_model(cls, a: Associate) -> "AssociateOut":
        return cls(**cls.fields_from(a))


class AssociateDetail(AssociateOut):
    credentials: list[CredentialOut]

    @classmethod
    def from_model(cls, a: Associate) -> "AssociateDetail":
        ordered = sorted(a.credentials, key=lambda c: status_rules.SEVERITY.index(c.status))
        return cls(**cls.fields_from(a), credentials=[CredentialOut.from_model(c) for c in ordered])


class VerifyAllOut(BaseModel):
    checked: int
    by_result: dict[str, int]


class FacilityStats(BaseModel):
    facility: str
    total: int
    by_status: dict[str, int]


class TimelinePoint(BaseModel):
    start: date  # first and last day of the week, both inclusive
    end: date
    count: int


class StatsOut(BaseModel):
    associates: int
    credentials: int
    unverified: int
    by_status: dict[str, int]
    by_facility: list[FacilityStats]
    timeline: list[TimelinePoint]  # credentials expiring in the next 90 days, by week


class FiltersOut(BaseModel):
    facilities: list[str]
    departments: list[str]
    managers: list[str]
