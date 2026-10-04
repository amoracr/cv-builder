import re
import unicodedata
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

    def clean_special_characters(self, raw_text: str) -> str:
        """
        Limpia caracteres especiales invisibles, espacios no break,
        caracteres de control y normaliza los espacios múltiples.
        Mantiene tildes, eñes y puntuación estándar.
        """
        if not raw_text:
            return ""

        text = unescape(raw_text)
        text = text.replace("\xa0", " ")
        text = text.replace("\u200b", "")
        text = "".join(ch for ch in text if unicodedata.category(ch)[0] != "C")

        text = re.sub(r"\s+", " ", text)

        return text.strip()

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

    def save_job(self, job_data: dict) -> bool:
        """Guarda la oferta de forma segura y atómica para evitar colisiones en hilos paralelos."""
        with Session(engine) as session:
            try:
                # 1. Verificar o crear la Fuente (JobSource) usando .merge() o buscando con optimización
                source = session.exec(
                    select(JobSource).where(JobSource.name == self.source_name)
                ).first()

                if not source:
                    source = JobSource(name=self.source_name, base_url=self.base_url)
                    session.add(source)
                    session.flush()  # flush asigna el ID sin cerrar la transacción global

                # 2. Verificar o crear la Empresa (Company)
                company_name = job_data.get("company_name", "Unknown Company")
                company = session.exec(
                    select(Company).where(Company.name == company_name)
                ).first()

                if not company:
                    company = Company(name=company_name)
                    session.add(company)
                    session.flush()  # flush para obtener el ID de la empresa

                # 3. Evitar duplicados por URL de forma segura dentro de la misma sesión
                existing_offer = session.exec(
                    select(JobOffer).where(JobOffer.url == job_data["url"])
                ).first()

                if existing_offer:
                    return False  # Ya existe, salimos sin hacer commit innecesario

                # 4. Crear y guardar la oferta en un solo paso atómico
                new_offer = JobOffer(
                    title=job_data["title"],
                    role=job_data.get("role", "General"),
                    description=job_data["description"],
                    url=job_data["url"],
                    company_id=company.id,
                    source_id=source.id,
                )

                session.add(new_offer)
                session.commit()  # Único commit atómico para todo el flujo de este empleo
                return True

            except Exception as e:
                session.rollback()  # Revierte ante cualquier fallo de concurrencia o constraint
                print(
                    f"⚠️ [DB Rollback] No se pudo guardar '{job_data.get('title')}': {e}"
                )
                return False

    def validate_region(self, job_data: dict):
        region = job_data.get("region", "")
        if not region or not region.strip():
            return True
        else:
            return bool(
                re.search(
                    r"anywhere|anyw(a|e)re|worldwide|global|remot(e|o)",
                    region,
                    re.IGNORECASE,
                )
            )

    def validate_tech_stack(self, job_data: dict):
        required_techs = {t.strip().lower() for t in JOB_TECHS if t.strip()}
        job_techs = {t.strip().lower() for t in job_data.get("techs")}
        return any(req in job_techs for req in required_techs)

    @abstractmethod
    def fetch_jobs(self, rss_url: str):
        pass

    @abstractmethod
    def run(self):
        pass
