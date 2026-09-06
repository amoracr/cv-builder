from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import Company, JobOffer, JobOfferCreate, JobSource

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("/", response_model=List[JobOffer])
def get_jobs(session: Session = Depends(get_session)):
    """Obtiene todas las ofertas de empleo registradas."""
    jobs = session.exec(select(JobOffer)).all()
    return jobs


@router.post("/", response_model=JobOffer)
def create_job(job_in: JobOfferCreate, session: Session = Depends(get_session)):
    """Crea una oferta buscando o creando automáticamente la empresa y la fuente por su nombre."""

    # 1. Gestionar la Empresa (Company)
    company_name = job_in.company_name or "Manual"
    company = session.exec(select(Company).where(Company.name == company_name)).first()
    if not company:
        company = Company(name=company_name)
        session.add(company)
        session.commit()
        session.refresh(company)

    # 2. Gestionar la Fuente (JobSource)
    source_name = job_in.source_name or "Direct Message"
    source = session.exec(
        select(JobSource).where(JobSource.name == source_name)
    ).first()
    if not source:
        source = JobSource(name=source_name)
        session.add(source)
        session.commit()
        session.refresh(source)

    # 3. Crear la Oferta de Empleo usando los IDs obtenidos/creados
    db_job = JobOffer(
        title=job_in.title,
        url=job_in.url,
        description=job_in.description,
        sector=job_in.sector or "private",  # NUEVO
        company_id=company.id,
        source_id=source.id,
    )

    session.add(db_job)
    session.commit()
    session.refresh(db_job)
    return db_job


@router.post("/archive-expired")
def archive_expired_jobs(session: Session = Depends(get_session)):
    """
    Revisa todas las ofertas activas y las archiva si han superado el tiempo límite sin actualizaciones:
    - Sector privado: 30 días desde updated_at
    - Sector público: 360 días desde updated_at
    """
    now = datetime.utcnow()

    # Seleccionamos las ofertas que NO estén ya archivadas
    statement = select(JobOffer).where(JobOffer.status != "archived")
    jobs = session.exec(statement).all()

    archived_count = 0

    for job in jobs:
        # Calculamos los días transcurridos desde la última actualización
        days_inactive = (now - job.updated_at).days

        # Evaluamos según el sector
        if (
            job.sector == "public"
            and days_inactive >= 360
            or job.sector == "private"
            and days_inactive >= 30
        ):
            job.status = "archived"
            job.updated_at = now  # Actualizamos el timestamp
            session.add(job)
            archived_count += 1

    if archived_count > 0:
        session.commit()

    return {
        "message": "Rutina completada con éxito.",
        "jobs_archived": archived_count,
        "checked_at": now.isoformat(),
    }
