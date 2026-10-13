import os
import time

from fastapi import HTTPException
from models import JobOffer, JobStatus, TailoredCV
from services.ai_matcher import (
    evaluate_job_offer,
    generate_ats_cv,
    generate_ats_cl,
)
from sqlmodel import Session, select


def analyze_discovered_jobs(session: Session) -> dict:
    """
    Tarea 1: Busca ofertas en estado 'Discovered' ordenadas por ID ascendente,
    las evalúa rápidamente con IA y actualiza su estado a 'to_apply' o 'Discarded'.
    """
    pause_time = float(os.getenv("PAUSE_BETWEEN_REQUEST", "1.0"))

    # Obtenemos el engine directamente de la sesión actual de FastAPI
    engine = session.bind

    # Consultar ofertas 'Discovered' ordenadas por updated_at de forma ascendente
    statement = (
        select(JobOffer)
        .where(JobOffer.status == JobStatus.DISCOVERED)
        .order_by(JobOffer.updated_at.asc())
    )
    discovered_jobs = session.exec(statement).all()

    if not discovered_jobs:
        return {
            "status": "success",
            "processed_count": 0,
            "message": "No hay ofertas pendientes por analizar.",
        }

    processed_count = 0
    approved_count = 0
    discarded_count = 0
    manual_review_count = 0

    for job in discovered_jobs:
        try:
            # Guardamos los datos básicos antes de llamar a la IA
            job_id = job.id
            job_description = job.description

            if not job_description or len(job_description.strip()) < 20:
                new_status = JobStatus.DISCARDED
                reasoning = "Descripción vacía o insuficiente para evaluar."
                match_pct = 0
            else:
                # Evaluación con la IA (fuera de cualquier transacción de BD)
                eval_result = evaluate_job_offer(job_description)
                match_pct = eval_result.match_percentage
                reasoning = eval_result.reasoning

                # Actualizar contadores según el nuevo estado devuelto por el LLM
                if match_pct >= 80:
                    new_status = JobStatus.TO_APPLY
                    approved_count += 1
                elif 65 <= match_pct < 80:
                    new_status = JobStatus.MANUAL_REVIEW
                    manual_review_count += 1
                else:
                    new_status = JobStatus.DISCARDED
                    discarded_count += 1

            # Abrimos una mini-sesión aislada para guardar el resultado de esta oferta
            with Session(engine) as update_session:
                db_job = update_session.get(JobOffer, job_id)
                if db_job:
                    db_job.match_percentage = match_pct
                    db_job.ai_reasoning = reasoning
                    db_job.status = new_status
                    update_session.add(db_job)
                    update_session.commit()

            processed_count += 1
            time.sleep(pause_time)

        except Exception as e:
            print(f"Error analizando la oferta ID {job.id} ('{job.title}'): {str(e)}")
            time.sleep(pause_time * 2)

    return {
        "status": "success",
        "processed_count": processed_count,
        "to_apply_count": approved_count,
        "to_manual_review": manual_review_count,
        "discarded_count": discarded_count,
    }


def generate_ats_cv_for_job(job_id: int, session: Session) -> dict:
    """
    Genera y guarda únicamente el CV adaptado para una única oferta de empleo.
    """
    job = session.get(JobOffer, job_id)
    if not job:
        raise HTTPException(
            status_code=404, detail=f"Oferta con ID {job_id} no encontrada."
        )

    existing_cv = session.exec(
        select(TailoredCV).where(TailoredCV.job_offer_id == job.id)
    ).first()

    if existing_cv and existing_cv.markdown_content:
        return {
            "status": "success",
            "message": "Esta oferta ya cuenta con su CV generado.",
            "cv_id": existing_cv.id,
        }

    try:
        cv_result = generate_ats_cv(job.description)

        if existing_cv:
            # Si ya existía el registro, solo actualizamos el CV
            existing_cv.markdown_content = cv_result.markdown_content
            session.add(existing_cv)
            session.commit()
            session.refresh(existing_cv)
            target_id = existing_cv.id
        else:
            # Si no existe nada, creamos el registro nuevo
            new_cv = TailoredCV(
                job_offer_id=job.id, markdown_content=cv_result.markdown_content
            )
            session.add(new_cv)
            session.commit()
            session.refresh(new_cv)
            target_id = new_cv.id

        return {
            "status": "success",
            "message": "CV generado y guardado exitosamente.",
            "cv_id": target_id,
        }

    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error generando el CV para la oferta ID {job.id}: {str(e)}",
        )


def generate_ats_cl_for_job(job_id: int, session: Session) -> dict:
    """
    Genera y guarda la carta de presentación adaptada para una única oferta de empleo.
    """
    job = session.get(JobOffer, job_id)
    if not job:
        raise HTTPException(
            status_code=404, detail=f"Oferta con ID {job_id} no encontrada."
        )

    # Verificar si ya existe un documento previo para esta oferta
    existing_doc = session.exec(
        select(TailoredCV).where(TailoredCV.job_offer_id == job.id)
    ).first()

    if existing_doc and existing_doc.cover_letter:
        return {
            "status": "success",
            "message": "Esta oferta ya cuenta con su carta de presentación generada.",
            "cv_id": existing_doc.id,
        }

    try:
        # Generar la carta de presentación mediante IA
        cl_result = generate_ats_cl(job.description)

        if existing_doc:
            # Si ya existía el registro (ej. se generó primero el CV), actualizamos la carta
            existing_doc.cover_letter = cl_result.cover_letter
            session.add(existing_doc)
            session.commit()
            session.refresh(existing_doc)
            target_id = existing_doc.id
        else:
            # Si no existe nada previo, creamos el registro completo en TailoredCV
            new_doc = TailoredCV(
                job_offer_id=job.id, cover_letter=cl_result.cover_letter
            )
            session.add(new_doc)
            session.commit()
            session.refresh(new_doc)
            target_id = new_doc.id

        return {
            "status": "success",
            "message": "Carta de presentación generada y guardada exitosamente.",
            "cv_id": target_id,
        }

    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error generando la carta de presentación para la oferta ID {job.id}: {str(e)}",
        )
