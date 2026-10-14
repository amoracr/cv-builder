import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import List, Optional
from zoneinfo import ZoneInfo

from config import CV_PREFIX, ENABLED_SCRAPERS
from database import get_session
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Response,
    status,
)
from fastapi.responses import FileResponse
from models import (
    Company,
    EmailRegisterRequest,
    JobEmail,
    JobOffer,
    JobOfferCreate,
    JobOfferDetailPublic,
    JobOfferPublic,
    JobOfferStatusUpdate,
    JobSource,
    JobStatus,
    TailoredCV,
    TailoredCVUpdate,
)
from scrapers.get_on_board import GetOnBoardScraper
from scrapers.jobicy import JobicyScraper
from scrapers.remote_first_jobs import RemoteFirstJobsScraper
from scrapers.remote_ok import RemoteOKScraper
from scrapers.remotive import RemotiveScraper
from scrapers.we_work_remotely import WeWorkRemotelyScraper
from services.job_processor import (
    analyze_discovered_jobs,
    generate_ats_cl_for_job,
    generate_ats_cv_for_job,
)
from services.pdf_generator import generate_cover_letter_pdf, generate_pdf_from_markdown
from sqlmodel import Session, func, select

router = APIRouter(prefix="/jobs", tags=["Jobs"])

COSTA_RICA_TZ = ZoneInfo("America/Costa_Rica")

AVAILABLE_SCRAPERS = {
    "we_work_remotely": (WeWorkRemotelyScraper, "We Work Remotely"),
    "remoteok": (RemoteOKScraper, "Remote OK"),
    "remotive": (RemotiveScraper, "Remotive"),
    "jobicy": (JobicyScraper, "Jobicy"),
    "get_on_board": (GetOnBoardScraper, "Get On Board"),
    "remote_first_jobs": (RemoteFirstJobsScraper, "Remote First Jobs"),
}


def run_single_scraper(scraper_cls, name: str):
    """Ejecuta un scraper individual de forma aislada"""
    print(f"🎯 [Orquestador API] Iniciando proceso de {name}...")
    try:
        scraper = scraper_cls()
        scraper.run()
        print(f"✨ [Orquestador API] Proceso de {name} finalizado con éxito.")
    except Exception as e:
        print(f"❌ [Orquestador API] Error crítico en {name}: {e}")


def run_scrapers_background():
    """Ejecuta únicamente los scrapers habilitados en la variable ENABLED_SCRAPERS del .env"""
    scrapers_to_run = []

    for key in ENABLED_SCRAPERS:
        if key in AVAILABLE_SCRAPERS:
            scrapers_to_run.append(AVAILABLE_SCRAPERS[key])
        else:
            print(
                f"⚠️ [Orquestador API] La clave '{key}' en ENABLED_SCRAPERS no coincide con ningún scraper registrado."
            )

    if not scrapers_to_run:
        print(
            "⚠️ [Orquestador API] No hay ningún scraper habilitado en el archivo .env."
        )
        return

    print(
        f"🚀 [Orquestador API] Ejecutando en paralelo {len(scrapers_to_run)} fuentes habilitadas..."
    )

    with ThreadPoolExecutor(max_workers=len(scrapers_to_run)) as executor:
        for scraper_cls, name in scrapers_to_run:
            executor.submit(run_single_scraper, scraper_cls, name)


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


@router.get("/")
def list_jobs(
    status: Optional[JobStatus] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    query = select(JobOffer)
    if status:
        query = query.where(JobOffer.status == status.value)

    total_query = select(func.count(JobOffer.id))
    if status:
        total_query = total_query.where(JobOffer.status == status.value)
    total_jobs = session.exec(total_query).one()

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(JobOffer.created_at.desc())

    jobs = session.exec(query).all()
    jobs_public = [JobOfferPublic.model_validate(job) for job in jobs]
    total_pages = max(1, (total_jobs + page_size - 1) // page_size)

    return {
        "page": page,
        "page_size": page_size,
        "total_jobs": total_jobs,
        "total_pages": total_pages,
        "jobs": jobs_public,
    }


@router.post("/", response_model=JobOffer)
def create_job(job_in: JobOfferCreate, session: Session = Depends(get_session)):
    """Crea una oferta buscando o creando automáticamente la empresa y la fuente por su nombre."""
    company_name = job_in.company_name or "Manual"
    company = session.exec(select(Company).where(Company.name == company_name)).first()
    if not company:
        company = Company(name=company_name)
        session.add(company)
        session.commit()
        session.refresh(company)

    source_name = job_in.source_name or "Direct Message"
    source = session.exec(
        select(JobSource).where(JobSource.name == source_name)
    ).first()
    if not source:
        source = JobSource(name=source_name)
        session.add(source)
        session.commit()
        session.refresh(source)

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


@router.get("/counts")
def get_job_status_counts(session: Session = Depends(get_session)):
    status_counts_query = select(JobOffer.status, func.count(JobOffer.id)).group_by(
        JobOffer.status
    )
    status_counts_result = session.exec(status_counts_query).all()

    counts_dict = {
        str(st.value if hasattr(st, "value") else st).lower(): count
        for st, count in status_counts_result
        if st
    }

    return counts_dict


@router.get("/statuses")
def get_job_statuses():
    statuses = [
        {"value": status.value, "label": status.name.replace("_", " ").title()}
        for status in JobStatus
    ]
    return statuses


@router.post("/archive-expired")
def archive_expired_jobs(session: Session = Depends(get_session)):
    """
    Revisa todas las ofertas activas y las archiva si han superado el tiempo límite sin actualizaciones:
    - Sector privado: 30 días desde updated_at
    - Sector público: 360 días desde updated_at
    """
    now = datetime.now(COSTA_RICA_TZ)

    statement = select(JobOffer).where(
        JobOffer.status.in_([JobStatus.WAITING, JobStatus.APPLIED])
    )
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
            job.status = JobStatus.GHOSTED
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


@router.post("/scrap-offers", status_code=202)
def trigger_scrapers(background_tasks: BackgroundTasks):
    """
    Endpoint para disparar la ingesta de los scrapers habilitados en el .env en segundo plano.
    """
    background_tasks.add_task(run_scrapers_background)

    return {
        "message": "La sincronización con los portales de empleo habilitados ha sido iniciada en segundo plano.",
        "status": "processing",
    }


@router.post("/analyze-offers")
def trigger_processing_queue(session: Session = Depends(get_session)):
    """Ejecuta el procesamiento por lotes de todas las ofertas 'Discovered'."""
    result = analyze_discovered_jobs(session)
    return result


@router.get("/{job_id}", response_model=JobOfferDetailPublic)
def get_job_detail(job_id: int, session: Session = Depends(get_session)):
    job = session.get(JobOffer, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Oferta de empleo no encontrada")
    return job


@router.patch("/{job_id}", response_model=JobOfferPublic)
def update_job_status(
    job_id: int,
    status_update: JobOfferStatusUpdate,
    session: Session = Depends(get_session),
):
    job = session.get(JobOffer, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Oferta con id {job_id} no encontrada",
        )

    job.status = status_update.status.value
    job.updated_at = datetime.now(COSTA_RICA_TZ)

    session.add(job)
    session.commit()
    session.refresh(job)

    return JobOfferPublic.model_validate(job)


@router.post("/{job_id}/register-email")
def register_job_email(
    job_id: int, payload: EmailRegisterRequest, session: Session = Depends(get_session)
):
    job = session.get(JobOffer, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Oferta no encontrada")

    new_email = JobEmail(
        job_offer_id=job.id,
        subject=payload.subject,
        sender=payload.sender,
        content=payload.content,
        received_at=datetime.now(COSTA_RICA_TZ),
    )
    session.add(new_email)

    job.updated_at = datetime.now(COSTA_RICA_TZ)
    session.add(job)

    session.commit()
    session.refresh(new_email)

    return {
        "message": "Correo registrado exitosamente",
        "job_id": job.id,
        "email_id": new_email.id,
    }


@router.post("/{job_id}/generate-cv")
def generate_job_cv(job_id: int, session: Session = Depends(get_session)):
    result = generate_ats_cv_for_job(job_id, session)
    return result


@router.get("/{job_id}/download-cv-pdf")
def download_tailored_cv_pdf(job_id: int, session: Session = Depends(get_session)):
    # 1. Buscar la oferta de empleo
    job = session.get(JobOffer, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Oferta de empleo no encontrada.")

    # 2. Validar que exista la relación tailored_cv y contenga el markdown
    if not job.tailored_cv or not job.tailored_cv.markdown_content:
        raise HTTPException(
            status_code=404,
            detail="No se encontró un CV optimizado en Markdown para esta oferta.",
        )

    # 3. Preparar ruta temporal y compilar PDF
    os.makedirs("./data/temp", exist_ok=True)
    pdf_path = f"./data/temp/CV_{job_id}.pdf"

    # Generamos el PDF utilizando el texto Markdown de la relación
    generate_pdf_from_markdown(job.tailored_cv.markdown_content, pdf_path)

    # 4. Retornar la respuesta como archivo descargable
    safe_title = job.title.replace(" ", "_").replace("/", "_")
    return FileResponse(
        path=pdf_path,
        filename=f"{CV_PREFIX}-{safe_title}.pdf",
        media_type="application/pdf",
    )


@router.post("/{job_id}/generate-cl")
def generate_job_cl(job_id: int, session: Session = Depends(get_session)):
    result = generate_ats_cl_for_job(job_id, session)
    return result


@router.get("/{job_id}/download-cl-pdf")
def download_tailored_cl_pdf(job_id: int, session: Session = Depends(get_session)):
    # 1. Buscar la oferta de empleo
    job = session.get(JobOffer, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Oferta de empleo no encontrada.")

    # 2. Validar que exista la relación tailored_cv y contenga el markdown
    if not job.tailored_cv or not job.tailored_cv.cover_letter:
        raise HTTPException(
            status_code=404,
            detail="No se encontró un Cover Letter en Markdown para esta oferta.",
        )

    # 3. Preparar ruta temporal y compilar PDF
    os.makedirs("./data/temp", exist_ok=True)
    pdf_path = f"./data/temp/CL_{job_id}.pdf"

    # Generamos el PDF utilizando el texto Markdown de la relación
    generate_cover_letter_pdf(job.tailored_cv.cover_letter, pdf_path)

    # 4. Retornar la respuesta como archivo descargable
    safe_title = job.title.replace(" ", "_").replace("/", "_")
    return FileResponse(
        path=pdf_path,
        filename=f"{CV_PREFIX}-{safe_title}.pdf",
        media_type="application/pdf",
    )


@router.patch("/{job_id}/tailored-cv")
def update_tailored_cv(
    job_id: int, payload: TailoredCVUpdate, session: Session = Depends(get_session)
):
    """
    Actualiza parcialmente el CV adaptado y/o la carta de presentación
    asociados a una oferta de empleo específica.
    """
    # 1. Verificar que la oferta exista
    job = session.get(JobOffer, job_id)
    if not job:
        raise HTTPException(
            status_code=404, detail=f"Oferta con ID {job_id} no encontrada."
        )

    # 2. Buscar el registro TailoredCV asociado a la oferta
    tailored_cv = session.exec(
        select(TailoredCV).where(TailoredCV.job_offer_id == job_id)
    ).first()

    if not tailored_cv:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No se encontró un documento generado (CV/Carta) para la oferta"
                f" ID {job_id}."
            ),
        )

    # 3. Actualizar dinámicamente solo los campos proporcionados en el payload
    update_data = payload.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail=(
                "No se proporcionaron campos para actualizar (markdown_content"
                " o cover_letter)."
            ),
        )

    for key, value in update_data.items():
        setattr(tailored_cv, key, value)

    try:
        session.add(tailored_cv)
        session.commit()
        session.refresh(tailored_cv)

        return {
            "status": "success",
            "message": "Documento actualizado correctamente.",
            "cv_id": tailored_cv.id,
            "updated_fields": list(update_data.keys()),
        }

    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al actualizar el documento en la base de datos: {str(e)}",
        )
