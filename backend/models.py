import enum
from datetime import datetime
from typing import List, Optional
from zoneinfo import ZoneInfo

from pydantic import BaseModel
from sqlalchemy import event
from sqlmodel import Column, Field, Relationship, SQLModel, Text

COSTA_RICA_TZ = ZoneInfo("America/Costa_Rica")


class JobStatus(str, enum.Enum):
    DISCOVERED = "discovered"
    DISCARDED = "discarded"
    MANUAL_REVIEW = "manual_review"
    TO_APPLY = "to_apply"
    APPLIED = "applied"
    WAITING = "waiting"
    INTERVIEWING = "interviewing"
    GHOSTED = "ghosted"
    OFFERED = "offered"
    REJECTED = "rejected"
    HIRED = "hired"


class Company(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    jobs: list["JobOffer"] = Relationship(back_populates="company")


class JobSource(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    jobs: list["JobOffer"] = Relationship(back_populates="source")


class TailoredCV(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job_offer_id: int = Field(foreign_key="joboffer.id", unique=True)
    markdown_content: Optional[str] = Field(default=None, sa_column=Column(Text))
    cover_letter: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=lambda: datetime.now(COSTA_RICA_TZ))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(COSTA_RICA_TZ))

    job_offer: Optional["JobOffer"] = Relationship(back_populates="tailored_cv")


@event.listens_for(TailoredCV, "before_update")
def receive_before_update(mapper, connection, target):
    target.updated_at = datetime.now(COSTA_RICA_TZ)


class JobEmail(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job_offer_id: int = Field(foreign_key="joboffer.id", index=True)

    subject: str
    sender: str
    content: Optional[str] = Field(default=None, sa_column=Column(Text))
    received_at: datetime = Field(default_factory=lambda: datetime.now(COSTA_RICA_TZ))

    job_offer: Optional["JobOffer"] = Relationship(back_populates="emails")


class JobOffer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    url: str = Field(index=True, unique=True)
    description: Optional[str] = Field(default=None, sa_column=Column(Text))

    status: JobStatus = Field(default=JobStatus.DISCOVERED)
    sector: str = Field(default="private")
    role: Optional[str] = Field(default="General", index=True)

    match_percentage: Optional[int] = Field(default=None)
    ai_reasoning: Optional[str] = Field(default=None, sa_column=Column(Text))

    company_id: Optional[int] = Field(default=None, foreign_key="company.id")
    source_id: Optional[int] = Field(default=None, foreign_key="jobsource.id")

    created_at: datetime = Field(default_factory=lambda: datetime.now(COSTA_RICA_TZ))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(COSTA_RICA_TZ))

    company: Optional[Company] = Relationship(back_populates="jobs")
    source: Optional[JobSource] = Relationship(back_populates="jobs")
    tailored_cv: Optional[TailoredCV] = Relationship(
        back_populates="job_offer",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "uselist": False},
    )
    emails: List[JobEmail] = Relationship(
        back_populates="job_offer",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "desc(JobEmail.received_at)",
        },
    )


@event.listens_for(JobOffer, "before_update")
def receive_before_update(mapper, connection, target):
    target.updated_at = datetime.now(COSTA_RICA_TZ)


class JobOfferCreate(SQLModel):
    title: str
    url: str
    description: Optional[str] = None
    sector: Optional[str] = "private"
    company_name: Optional[str] = "Manual"
    source_name: Optional[str] = "Direct Message"


class JobOfferStatusUpdate(BaseModel):
    status: JobStatus


class CompanyPublic(SQLModel):
    id: Optional[int] = None
    name: str


class JobSourcePublic(SQLModel):
    id: Optional[int] = None
    name: str


class JobOfferPublic(SQLModel):
    id: Optional[int] = None
    title: str
    url: str
    status: str
    match_percentage: Optional[int] = None
    ai_reasoning: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    company: Optional[CompanyPublic] = None
    source: Optional[JobSourcePublic] = None


class JobEmailPublic(SQLModel):
    id: Optional[int] = None
    subject: str
    sender: str
    content: Optional[str] = None
    received_at: datetime


class TailoredCVPublic(SQLModel):
    markdown_content: Optional[str] = None
    cover_letter: Optional[str] = None


class JobOfferDetailPublic(JobOfferPublic):
    description: Optional[str] = None
    emails: List[JobEmailPublic] = []
    tailored_cv: Optional[TailoredCVPublic] = None


class EmailRegisterRequest(BaseModel):
    subject: str
    sender: str
    content: str


class TailoredDocumentResponse(BaseModel):
    markdown_content: str
    cover_letter: str


class TailoredCVUpdate(BaseModel):
    markdown_content: Optional[str] = None
    cover_letter: Optional[str] = None
