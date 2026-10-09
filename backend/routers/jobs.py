from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import List
from zoneinfo import ZoneInfo

from database import get_session
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from models import (
    Company,
    EmailRegisterRequest,
    JobEmail,
    JobOffer,
    JobOfferCreate,
    JobOfferDetailPublic,
    JobOfferPublic,
    JobSource,
)
from scrapers.get_on_board import GetOnBoardScraper
from scrapers.jobicy import JobicyScraper
from scrapers.remote_ok import RemoteOKScraper
from scrapers.remotive import RemotiveScraper
from scrapers.wwr import WWRScraper
from services.job_processor import analyze_discovered_jobs
from sqlmodel import Session, func, select

router = APIRouter(prefix="/jobs", tags=["Jobs"])

COSTA_RICA_TZ = ZoneInfo("America/Costa_Rica")


@router.head("/", status_code=200)
def count_jobs_head(response: Response, session: Session = Depends(get_session)):
    """
    Método HEAD para el recurso /jobs/.
    Retorna la cantidad total de ofertas de empleo en la cabecera 'X-Total-Count'
    sin transferir el cuerpo de la respuesta.
    """
    total_jobs = session.exec(select(func.count()).select_from(JobOffer)).one()
    response.headers["X-Total-Count"] = str(total_jobs)
    return


@router.get("/", response_model=List[JobOfferPublic])
def get_jobs(session: Session = Depends(get_session)):
    statement = select(JobOffer).order_by(JobOffer.updated_at.desc())
    jobs = session.exec(statement).all()
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
        sector=job_in.sector or "private",
        company_id=company.id,
        source_id=source.id,
    )

    session.add(db_job)
    session.commit()
    session.refresh(db_job)
    return db_job


@router.get("/{job_id}", response_model=JobOfferDetailPublic)
def get_job_detail(job_id: int, session: Session = Depends(get_session)):
    job = session.get(JobOffer, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Oferta de empleo no encontrada")
    return job


@router.post("/{job_id}/register-email")
def register_job_email(
    job_id: int, payload: EmailRegisterRequest, session: Session = Depends(get_session)
):
    job = session.get(JobOffer, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Oferta no encontrada")

    # 1. Guardar el correo en la tabla relacional JobEmail
    new_email = JobEmail(
        job_offer_id=job.id,
        subject=payload.subject,
        sender=payload.sender,
        content=payload.content,
        received_at=datetime.now(COSTA_RICA_TZ),
    )
    session.add(new_email)

    # 2. Actualizar el estado de la oferta con el parámetro recibido del frontend
    job.status = payload.status
    job.updated_at = datetime.now(COSTA_RICA_TZ)

    session.add(job)
    session.commit()
    session.refresh(job)

    return {
        "message": "Correo registrado y estado actualizado exitosamente",
        "job_id": job.id,
        "new_status": job.status,
    }


@router.post("/archive-expired")
def archive_expired_jobs(session: Session = Depends(get_session)):
    """
    Revisa todas las ofertas activas y las archiva si han superado el tiempo límite sin actualizaciones:
    - Sector privado: 30 días desde updated_at
    - Sector público: 360 días desde updated_at
    """
    now = datetime.now(COSTA_RICA_TZ)

    statement = select(JobOffer).where(JobOffer.status != "archived")
    jobs = session.exec(statement).all()

    archived_count = 0

    for job in jobs:
        days_inactive = (now - job.updated_at).days

        if (
            job.sector == "public"
            and days_inactive >= 360
            or job.sector == "private"
            and days_inactive >= 30
        ):
            job.status = "archived"
            job.updated_at = now
            session.add(job)
            archived_count += 1

    if archived_count > 0:
        session.commit()

    return {
        "message": "Rutina completada con éxito.",
        "jobs_archived": archived_count,
        "checked_at": now.isoformat(),
    }


def run_single_scraper(scraper_cls, name: str):
    """Ejecuta un scraper individual de forma aislada"""
    print(f"🎯 [Orquestador API] Iniciando proceso de {name}...")
    try:
        # Instanciamos el scraper sin pasarle la sesión (como está diseñado originalmente)
        scraper = scraper_cls()
        scraper.run()
        print(f"✨ [Orquestador API] Proceso de {name} finalizado con éxito.")
    except Exception as e:
        print(f"❌ [Orquestador API] Error crítico en {name}: {e}")


def run_scrapers_background():
    """Ejecuta cada scraper de forma concurrente pero totalmente aislada"""
    # Pasamos las clases, no instancias compartidas
    scrapers_to_run = [
        (WWRScraper, "We Work Remotely"),
        (RemoteOKScraper, "Remote OK"),
        (RemotiveScraper, "Remotive"),
        (JobicyScraper, "Jobicy"),
        (GetOnBoardScraper, "Get On Board"),
    ]

    with ThreadPoolExecutor(max_workers=len(scrapers_to_run)) as executor:
        for scraper_cls, name in scrapers_to_run:
            executor.submit(run_single_scraper, scraper_cls, name)


@router.post("/scrap-offers", status_code=202)
def trigger_scrapers(background_tasks: BackgroundTasks):
    """
    Endpoint para disparar la ingesta de todos los scrapers en paralelo en segundo plano.
    """
    background_tasks.add_task(run_scrapers_background)

    return {
        "message": "La sincronización con los portales de empleo ha sido iniciada en segundo plano en paralelo.",
        "status": "processing",
    }


@router.post("/analyze-offers")
def trigger_processing_queue(session: Session = Depends(get_session)):
    """Ejecuta el procesamiento por lotes de todas las ofertas 'Discovered' respetando el PAUSE_BETWEEN_REQUEST."""
    result = analyze_discovered_jobs(session)
    return result
