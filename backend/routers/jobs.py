from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import List

from database import get_session
from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response
from models import Company, JobOffer, JobOfferCreate, JobSource
from scrapers.get_on_board import GetOnBoardScraper
from scrapers.jobicy import JobicyScraper
from scrapers.remote_ok import RemoteOKScraper
from scrapers.remotive import RemotiveScraper
from scrapers.wwr import WWRScraper
from services.job_processor import process_discovered_jobs
from sqlmodel import Session, func, select

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.head("/jobs/", status_code=200)
def count_jobs_head(response: Response, session: Session = Depends(get_session)):
    """
    Método HEAD para el recurso /jobs/.
    Retorna la cantidad total de ofertas de empleo en la cabecera 'X-Total-Count'
    sin transferir el cuerpo de la respuesta.
    """
    total_jobs = session.exec(select(func.count()).select_from(JobOffer)).one()
    response.headers["X-Total-Count"] = str(total_jobs)
    return


@router.get("/jobs/")
def List_jobs(
    role: str | None = Query(
        default=None, description="Ej: wordpress developer, php developer"
    ),
    sector: str | None = Query(default=None, description="private / public"),
    session: Session = Depends(get_session),
):
    statement = select(JobOffer)

    if role:
        statement = statement.where(JobOffer.role.ilike(f"%{role}%"))

    if sector:
        statement = statement.where(JobOffer.sector == sector)

    return session.exec(statement).all()


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
        sector=job_in.sector or "private",
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


def run_single_scraper(scraper_instance, name: str):
    """Función auxiliar para ejecutar y capturar errores de un scraper individual"""
    print(f"🎯 [Orquestador API] Iniciando proceso de {name}...")
    try:
        scraper_instance.run()
        print(f"✨ [Orquestador API] Proceso de {name} finalizado con éxito.")
    except Exception as e:
        print(f"❌ [Orquestador API] Error ejecutando {name}: {e}")


def run_scrapers_background():
    """Ejecuta todos los scrapers registrados de forma concurrente (en paralelo)"""
    scrapers = [
        (WWRScraper(), "We Work Remotely"),
        (RemoteOKScraper(), "Remote OK"),
        (RemotiveScraper(), "Remotive"),
        (JobicyScraper(), "Jobicy"),
        (GetOnBoardScraper(), "Get On Board"),
    ]

    # Usamos ThreadPoolExecutor para correr las peticiones de red en paralelo
    with ThreadPoolExecutor(max_workers=len(scrapers)) as executor:
        for scraper, name in scrapers:
            executor.submit(run_single_scraper, scraper, name)


@router.post("/run-scrapers", status_code=202)
def trigger_scrapers(background_tasks: BackgroundTasks):
    """
    Endpoint para disparar la ingesta de todos los scrapers en paralelo en segundo plano.
    """
    background_tasks.add_task(run_scrapers_background)

    return {
        "message": "La sincronización con los portales de empleo ha sido iniciada en segundo plano en paralelo.",
        "status": "processing",
    }


@router.post("/process-queue")
def trigger_processing_queue(session: Session = Depends(get_session)):
    """Ejecuta el procesamiento por lotes de todas las ofertas 'Discovered' respetando el PAUSE_BETWEEN_REQUEST."""
    result = process_discovered_jobs(session)
    return result
