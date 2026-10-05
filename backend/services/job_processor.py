import os
import time

from models import JobOffer, TailoredCV
from services.ai_matcher import evaluate_job_offer, generate_ats_cv
from sqlmodel import Session, select


def analyze_discovered_jobs(session: Session) -> dict:
    """
    Tarea 1: Busca ofertas en estado 'Discovered' ordenadas por ID ascendente,
    las evalúa rápidamente con IA y actualiza su estado a 'to_apply' o 'Discarded'.
    """
    pause_time = float(os.getenv("PAUSE_BETWEEN_REQUEST", "1.0"))

    # Obtenemos el engine directamente de la sesión actual de FastAPI
    engine = session.bind

    # Consultar ofertas 'Discovered' ordenadas por ID de forma ascendente
    statement = (
        select(JobOffer)
        .where(JobOffer.status == "Discovered")
        .order_by(JobOffer.id.asc())
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

    for job in discovered_jobs:
        try:
            # Guardamos los datos básicos antes de llamar a la IA
            job_id = job.id
            job_title = job.title
            job_description = job.description

            if not job_description or len(job_description.strip()) < 20:
                new_status = "Discarded"
                reasoning = "Descripción vacía o insuficiente para evaluar."
                match_pct = 0
            else:
                # Evaluación con la IA (fuera de cualquier transacción de BD)
                eval_result = evaluate_job_offer(job_description)
                match_pct = eval_result.match_percentage
                reasoning = eval_result.reasoning

                if eval_result.should_apply and match_pct >= 80:
                    new_status = "to_apply"
                    approved_count += 1
                else:
                    new_status = "Discarded"
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
        "discarded_count": discarded_count,
    }


def generate_ats_cvs_for_approved(session: Session) -> dict:
    """
    Tarea 2: Busca ofertas en estado 'to_apply' ordenadas por ID ascendente
    y genera/actualiza su CV adaptado si aún no lo tienen creado.
    """
    pause_time = float(os.getenv("PAUSE_BETWEEN_REQUEST", "1.0"))

    # Consultar ofertas aprobadas ordenadas por ID ascendente
    statement = (
        select(JobOffer)
        .where(JobOffer.status == "to_apply")
        .order_by(JobOffer.id.asc())
    )
    approved_jobs = session.exec(statement).all()

    if not approved_jobs:
        return {
            "status": "success",
            "generated_count": 0,
            "message": "No hay ofertas aprobadas pendientes de CV.",
        }

    generated_count = 0

    for job in approved_jobs:
        try:
            # Verificar si ya existe un CV previo para evitar duplicados
            existing_cv = session.exec(
                select(TailoredCV).where(TailoredCV.job_offer_id == job.id)
            ).first()

            if existing_cv:
                continue  # Ya lo tiene, pasamos al siguiente

            # Generar el CV adaptado
            cv_result = generate_ats_cv(job.description)

            new_cv = TailoredCV(
                job_offer_id=job.id,
                markdown_content=cv_result.markdown_content,
                summary_of_changes=cv_result.summary_of_changes,
            )
            session.add(new_cv)
            session.commit()
            generated_count += 1

            time.sleep(pause_time)

        except Exception as e:
            session.rollback()
            print(
                f"Error generando CV para la oferta ID {job.id} ('{job.title}'): {str(e)}"
            )
            time.sleep(pause_time * 2)

    return {"status": "success", "generated_count": generated_count}
