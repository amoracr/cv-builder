from database import get_session
from fastapi import APIRouter, Depends, HTTPException, status
from models import JobSource, JobSourcePublic
from sqlmodel import Session, select

router = APIRouter(prefix="/sources", tags=["Jobs Sources"])


@router.get("/", response_model=list[JobSourcePublic])
def get_job_sources(session: Session = Depends(get_session)):
    """Obtiene el listado completo de fuentes de empleo (Job Sources) registradas."""
    sources = session.exec(select(JobSource)).all()
    return sources
