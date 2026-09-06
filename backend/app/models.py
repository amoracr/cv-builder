from datetime import datetime
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class Company(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    jobs: list["JobOffer"] = Relationship(back_populates="company")


class JobSource(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    jobs: list["JobOffer"] = Relationship(back_populates="source")


class JobOffer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    url: str
    description: Optional[str] = None
    status: str = Field(
        default="Discovered"
    )  # Discovered, Applied, Interviewing, Archived, etc.

    # NUEVO CAMPO: "private" o "public"
    sector: str = Field(default="private")

    match_score: Optional[float] = Field(default=None)
    company_id: Optional[int] = Field(default=None, foreign_key="company.id")
    source_id: Optional[int] = Field(default=None, foreign_key="jobsource.id")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    company: Optional[Company] = Relationship(back_populates="jobs")
    source: Optional[JobSource] = Relationship(back_populates="jobs")


# Esquema para recibir los datos por API
class JobOfferCreate(SQLModel):
    title: str
    url: str
    description: Optional[str] = None
    sector: Optional[str] = "private"  # NUEVO: por defecto privada
    company_name: Optional[str] = "Manual"
    source_name: Optional[str] = "Direct Message"
