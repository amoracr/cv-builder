from database import get_session
from fastapi import APIRouter, Depends, HTTPException, status
from models import Company
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

router = APIRouter(prefix="/company", tags=["Companies"])


@router.get("/{company_id}/jobs")
def get_company_jobs_summary(company_id: int, session: Session = Depends(get_session)):
    # Buscamos la empresa cargando sus ofertas relacionadas
    statement = (
        select(Company)
        .where(Company.id == company_id)
        .options(selectinload(Company.jobs))
    )
    company = session.exec(statement).first()

    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    # Mapeamos la lista de puestos con los campos requeridos
    jobs_summary = [
        {
            "id": job.id,
            "title": job.title,
            "status": job.status,
            "updated_at": job.updated_at,
        }
        for job in company.jobs
    ]

    return {"company_name": company.name, "jobs": jobs_summary}
