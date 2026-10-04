"""Pydantic response models. Keep web/lib/api.ts in sync with this file."""
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

import status as status_rules
from models import Associate, Credential
from roster import LOOKUP_URLS

CredentialStatus = Literal[
    "valid", "unverified", "expiring_90", "expiring_60", "expiring_30", "expired", "verification_failed", "excluded"
]
VerificationResultName = Literal["verified", "not_found", "excluded", "mismatch", "error"]
AlertThreshold = Literal["90", "60", "30", "expired", "excluded"]


class HealthOut(BaseModel):
    status: Literal["ok"]


class AccessOut(BaseModel):
    required: bool
    granted: bool


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
    manager_email: str
    department: str
    facility: str
    credential_type: str
    issuing_source: str
    verify_method: str
    lookup_url: Optional[str]  # where a person checks a hand-verified credential
    number: Optional[str]
    issued_date: Optional[date]
    expires_date: Optional[date]
    status: CredentialStatus
    days_left: Optional[int]
    last_verification: Optional[VerificationOut]  # None = not yet verified
    email_contacted: bool
    email_contact_count: int
    last_email_contact_at: Optional[datetime]
    last_email_contact_channel: Optional[Literal["email", "outbox"]]

    @classmethod
    def from_model(cls, c: Credential) -> "CredentialOut":
        return cls(
            id=c.id,
            associate_id=c.associate_id,
            associate_name=c.associate.name,
            manager_email=c.associate.manager_email,
            department=c.associate.department,
            facility=c.associate.facility,
            credential_type=c.credential_type.name,
            issuing_source=c.credential_type.issuing_source,
            verify_method=c.credential_type.verify_method,
            lookup_url=(
                LOOKUP_URLS.get(c.credential_type.issuing_source)
                if c.credential_type.verify_method in ("manual", "api") else None
            ),
            number=c.number,
            issued_date=c.issued_date,
            expires_date=c.expires_date,
            status=c.status,
            days_left=status_rules.days_left(c.expires_date),
            last_verification=VerificationOut.model_validate(c.verifications[-1]) if c.verifications else None,
            email_contacted=bool(c.email_contacts),
            email_contact_count=len(c.email_contacts),
            last_email_contact_at=c.email_contacts[-1].sent_at if c.email_contacts else None,
            last_email_contact_channel=c.email_contacts[-1].channel if c.email_contacts else None,
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


# Keys the app writes into a verification's details; a source label must not replace them.
RESERVED_DETAIL_KEYS = {
    "entered_by_hand", "number", "expires_date", "issued_date", "note", "reason", "credentials_held",
    "source_status", "mock", "seeded", "outcome_source", "needs_review", "candidates",
}


class ManualVerificationIn(BaseModel):
    """What a person saw when they looked a credential up at its source."""
    result: Literal["verified", "not_found"]
    number: Optional[str] = Field(None, max_length=64)
    expires_date: Optional[date] = None
    issued_date: Optional[date] = None
    note: Optional[str] = Field(None, max_length=500)
    credentials_held: Optional[str] = Field(None, max_length=300)  # as the source writes them, e.g. R.T.(R)(CT)(ARRT)
    source_status: Optional[str] = Field(None, max_length=120)  # e.g. Active
    # Anything else the source page shows, by its label there (e.g. "CE Biennium"). Kept with the verification.
    source_details: dict[str, str] = Field(default_factory=dict, max_length=12)

    @field_validator("source_details")
    @classmethod
    def _labels_are_free(cls, value: dict[str, str]) -> dict[str, str]:
        cleaned = {}
        for label, text in value.items():
            label, text = label.strip(), text.strip()
            key = label.lower().replace(" ", "_")
            if not label or len(label) > 60 or len(text) > 500:
                raise ValueError("each label is 1 to 60 characters and each value at most 500")
            if key in RESERVED_DETAIL_KEYS or key.endswith("path"):
                raise ValueError("'%s' is recorded by the app itself and cannot be set here" % label)
            if text:
                cleaned[label] = text
        return cleaned


class VerifyAllOut(BaseModel):
    checked: int
    by_result: dict[str, int]
    skipped_manual: int = 0  # credentials that are verified by hand and so were left alone


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    credential_id: int
    threshold: AlertThreshold
    sent_to: str
    sent_at: datetime
    channel: str


class AlertRunResult(BaseModel):
    sent: int
    by_threshold: dict[AlertThreshold, int]
    by_channel: dict[str, int]  # alert rows emailed vs left in the outbox


class CredentialEmailContactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    credential_id: int
    kind: Literal["initial", "follow_up"]
    sent_to: str
    sent_at: datetime
    channel: Literal["email", "outbox"]


class DailyRunOut(BaseModel):
    trigger: Literal["scheduled", "manual"]
    started_at: datetime
    finished_at: datetime
    checked: int
    by_result: dict[str, int]
    alerts: Optional[AlertRunResult]  # None when the sweep was skipped
    alerts_skipped: Optional[str]  # why the sweep was skipped, if it was


class DailyJobStatusOut(BaseModel):
    enabled: bool  # False when the schedule is turned off; the manual run still works
    next_run_at: Optional[datetime]
    running: bool
    last_run: Optional[DailyRunOut]  # since the API last started


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
    demo_manager: Optional[str]  # the manager with the largest team; the Manager view shows this team
    demo_team: Optional[str]  # that team's department and facility, for display
