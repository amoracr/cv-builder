import os
import time
from sqlmodel import Session, select
from models import JobOffer, TailoredCV  # Ajusta el import según tu estructura
from services.ai_matcher import evaluate_job_offer, generate_ats_cv

def process_discovered_jobs(session: Session) -> dict:
    """
    Busca todas las ofertas en estado 'Discovered', las evalúa con IA,
    genera su CV adaptado si son aprobadas, y respeta la pausa configurada en el .env.
    """
    # 1. Leer el tiempo de pausa desde el .env (por defecto 4 segundos si no está definido)
    pause_time = float(os.getenv("PAUSE_BETWEEN_REQUEST", "4.0"))

    # 2. Consultar todas las ofertas con estado 'Discovered'
    statement = select(JobOffer).where(JobOffer.status == "Discovered")
    discovered_jobs = session.exec(statement).all()

    if not discovered_jobs:
        return {"status": "success", "processed_count": 0, "message": "No hay ofertas pendientes por procesar."}

    processed_count = 0
    approved_count = 0
    discarded_count = 0

    for job in discovered_jobs:
        try:
            # Si la oferta no tiene descripción, la marcamos como descartada por falta de datos
            if not job.description or len(job.description.strip()) < 20:
                job.status = "Discarded"
                job.ai_reasoning = "Descripción vacía o insuficiente para evaluar."
                session.add(job)
                session.commit()
                continue

            # A. Evaluación rápida (Filtro)
            eval_result = evaluate_job_offer(job.description)
            job.match_percentage = eval_result.match_percentage
            job.ai_reasoning = eval_result.reasoning

            # B. Validación de aprobación basada en la regla del modelo o el porcentaje
            if eval_result.should_apply and eval_result.match_percentage >= 80:
                job.status = "to_apply"
                session.add(job)
                session.commit()  # Commit previo para asegurar que el JobOffer tenga ID asignado

                # C. Generar el CV adaptado (Modelo Pro) y guardarlo en su tabla normalizada
                cv_result = generate_ats_cv(job.description)
                
                # Verificamos si ya existía un CV previo para evitar duplicados en reintentos
                existing_cv = session.exec(select(TailoredCV).where(TailoredCV.job_offer_id == job.id)).first()
                if existing_cv:
                    existing_cv.markdown_content = cv_result.markdown_content
                    existing_cv.summary_of_changes = cv_result.summary_of_changes
                    session.add(existing_cv)
                else:
                    new_cv = TailoredCV(
                        job_offer_id=job.id,
                        markdown_content=cv_result.markdown_content,
                        summary_of_changes=cv_result.summary_of_changes
                    )
                    session.add(new_cv)

                approved_count += 1
            else:
                job.status = "Discarded"
                discarded_count += 1

            session.add(job)
            session.commit()
            processed_count = processed_count + 1

            # D. Pausa crítica para respetar el RPM de la API de Gemini
            time.sleep(pause_time)

        except Exception as e:
            print(f"Error procesando la oferta ID {job.id} ('{job.title}'): {str(e)}")
            # En caso de error de red o rate limit de la API, damos una pausa de seguridad más larga antes de continuar
            time.sleep(pause_time * 2)

    return {
        "status": "success",
        "processed_count": processed_count,
        "to_apply_count": approved_count,
        "discarded_count": discarded_count
    }