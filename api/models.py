"""SQLAlchemy models. This is the data contract in CLAUDE.md; change only with team agreement."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base


class Associate(Base):
    __tablename__ = "associates"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, index=True)
    npi: Mapped[Optional[str]]
    role: Mapped[str]
    department: Mapped[str] = mapped_column(String, index=True)
    facility: Mapped[str] = mapped_column(String, index=True)
    state: Mapped[str]  # two-letter work state: IN or MI
    manager_email: Mapped[str] = mapped_column(String, index=True)

    credentials: Mapped[list[Credential]] = relationship(back_populates="associate", cascade="all, delete-orphan")


class CredentialType(Base):
    __tablename__ = "credential_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    issuing_source: Mapped[str]
    verify_method: Mapped[str]  # api | file | mock | manual
    renewal_months: Mapped[Optional[int]]  # None = does not expire (NPI, exclusion check)


class RoleRequirement(Base):
    __tablename__ = "role_requirements"

    role: Mapped[str] = mapped_column(primary_key=True)
    credential_type_id: Mapped[int] = mapped_column(ForeignKey("credential_types.id"), primary_key=True)


class Credential(Base):
    __tablename__ = "credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    associate_id: Mapped[int] = mapped_column(ForeignKey("associates.id"), index=True)
    credential_type_id: Mapped[int] = mapped_column(ForeignKey("credential_types.id"))
    number: Mapped[Optional[str]]
    issued_date: Mapped[Optional[date]]
    expires_date: Mapped[Optional[date]] = mapped_column(index=True)
    # Derived (see status.py); stored so list endpoints can filter and sort in SQL.
    status: Mapped[str] = mapped_column(String, index=True, default="valid")

    associate: Mapped[Associate] = relationship(back_populates="credentials")
    credential_type: Mapped[CredentialType] = relationship()
    verifications: Mapped[list[Verification]] = relationship(
        back_populates="credential", cascade="all, delete-orphan", order_by="Verification.checked_at"
    )
    alerts: Mapped[list[Alert]] = relationship(cascade="all, delete-orphan")


class Verification(Base):
    __tablename__ = "verifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    credential_id: Mapped[int] = mapped_column(ForeignKey("credentials.id"), index=True)
    checked_at: Mapped[datetime]
    source: Mapped[str]
    result: Mapped[str]  # verified | not_found | excluded | mismatch | error
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    evidence_path: Mapped[Optional[str]]

    credential: Mapped[Credential] = relationship(back_populates="verifications")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    credential_id: Mapped[int] = mapped_column(ForeignKey("credentials.id"), index=True)
    threshold: Mapped[str]  # 90 | 60 | 30 | expired | excluded
    sent_to: Mapped[str]
    sent_at: Mapped[datetime]
    channel: Mapped[str]
