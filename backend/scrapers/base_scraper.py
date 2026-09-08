import re
from abc import ABC, abstractmethod
from html import unescape

from config import JOB_TECHS
from database import engine
from models import Company, JobOffer, JobSource
from sqlmodel import Session, select


class BaseScraper(ABC):
    def __init__(self, source_name: str, base_url: str):
        self.source_name = source_name
        self.base_url = base_url

    def clean_html(self, raw_html: str) -> str:
        """Limpia etiquetas HTML para dejar texto plano."""
        if not raw_html:
            return ""
        clean_r = re.compile("<.*?>")
        text = re.sub(clean_r, "", raw_html)
        return unescape(text).strip()

    def detect_techs(self, text_to_search: str, initial_tags: list = None) -> list:
        """Detecta tecnologías combinando tags nativos y búsqueda en el texto por JOB_TECHS."""
        detected_techs = set()

        if initial_tags:
            for tag in initial_tags:
                if tag:
                    sub_skills = re.split(
                        r",|\sand\s|/|\s&\s", tag, flags=re.IGNORECASE
                    )
                    for s in sub_skills:
                        if s.strip():
                            detected_techs.add(s.strip())

        if JOB_TECHS:
            for tech in JOB_TECHS:
                tech_clean = tech.strip()
                if not tech_clean:
                    continue
                pattern = rf"\b{re.escape(tech_clean)}\b"
                if re.search(pattern, text_to_search, re.IGNORECASE):
                    detected_techs.add(tech_clean)

        return list(detected_techs)

    def save_job(self, job_data: dict):
        """Guarda la oferta, asegurando fuente y empresa de forma genérica."""
        with Session(engine) as session:
            # 1. Verificar o crear la Fuente (JobSource)
            source = session.exec(
                select(JobSource).where(JobSource.name == self.source_name)
            ).first()

            if not source:
                source = JobSource(name=self.source_name, base_url=self.base_url)
                session.add(source)
                session.commit()
                session.refresh(source)

            # 2. Verificar o crear la Empresa (Company)
            company = session.exec(
                select(Company).where(Company.name == job_data["company_name"])
            ).first()

            if not company:
                company = Company(name=job_data["company_name"])
                session.add(company)
                session.commit()
                session.refresh(company)

            # 3. Evitar duplicados por URL
            existing_offer = session.exec(
                select(JobOffer).where(JobOffer.url == job_data["url"])
            ).first()

            if existing_offer:
                return False  # Ya existe

            # 4. Guardar oferta
            new_offer = JobOffer(
                title=job_data["title"],
                role=job_data["role"],
                description=job_data["description"],
                url=job_data["url"],
                company_id=company.id,
                source_id=source.id,
            )

            session.add(new_offer)
            session.commit()
            return True

    @abstractmethod
    def fetch_jobs(self, rss_url: str):
        pass

    @abstractmethod
    def run(self):
        pass
