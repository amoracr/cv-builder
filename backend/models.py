from datetime import datetime
from enum import StrEnum
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import event
from sqlmodel import Column, Field, Relationship, SQLModel, Text

COSTA_RICA_TZ = ZoneInfo("America/Costa_Rica")


class JobStatus(StrEnum):
    DISCOVERED = "discovered"
    DISCARDED = "discarded"
    MANUAL_REVIEW = "manual_review"
    TO_APPLY = "to_apply"
    APPLIED = "applied"
    WAITING = "waiting"
    INTERVIEWING = "interviewing"
    GHOSTED = "ghosted"
    OFFERED = "offered"


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
    summary_of_changes: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=lambda: datetime.now(COSTA_RICA_TZ))

    job_offer: Optional["JobOffer"] = Relationship(back_populates="tailored_cv")


class JobOffer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    url: str = Field(index=True, unique=True)
    description: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Estados y clasificación
    status: JobStatus = Field(default=JobStatus.DISCOVERED)
    sector: str = Field(default="private")  # "private" o "public"
    role: Optional[str] = Field(default="General", index=True)

    # Resultados del análisis rápido de IA (métricas globales)
    match_percentage: Optional[int] = Field(default=None)
    ai_reasoning: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Claves foráneas
    company_id: Optional[int] = Field(default=None, foreign_key="company.id")
    source_id: Optional[int] = Field(default=None, foreign_key="jobsource.id")

    # Auditoría
    created_at: datetime = Field(default_factory=lambda: datetime.now(COSTA_RICA_TZ))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(COSTA_RICA_TZ))

    # Relaciones ORM
    company: Optional[Company] = Relationship(back_populates="jobs")
    source: Optional[JobSource] = Relationship(back_populates="jobs")
    tailored_cv: Optional[TailoredCV] = Relationship(
        back_populates="job_offer", sa_relationship_kwargs={"uselist": False}
    )


# Evento de SQLAlchemy para actualizar el campo updated_at automáticamente antes de cada actualización
@event.listens_for(JobOffer, "before_update")
def receive_before_update(mapper, connection, target):
    target.updated_at = datetime.now(COSTA_RICA_TZ)


# Esquema para recibir los datos por API
class JobOfferCreate(SQLModel):
    title: str
    url: str
    description: Optional[str] = None
    sector: Optional[str] = "private"  # NUEVO: por defecto privada
    company_name: Optional[str] = "Manual"
    source_name: Optional[str] = "Direct Message"
