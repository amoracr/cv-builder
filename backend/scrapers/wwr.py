import re
from html import unescape

import feedparser
from config import JOB_TECHS, WWR_RSS_FEEDS
from database import engine
from models import Company, JobOffer, JobSource
from sqlmodel import Session, select


def clean_html(raw_html: str) -> str:
    """Elimina etiquetas HTML y limpia entidades para dejar texto plano."""
    if not raw_html:
        return ""
    clean_r = re.compile("<.*?>")
    text = re.sub(clean_r, "", raw_html)
    return unescape(text).strip()


def fetch_wwr_jobs(rss_url: str):
    """
    Obtiene y parsea los ítems de un feed RSS de We Work Remotely.
    Separa empresa y rol, y detecta tecnologías tanto en tags como en el texto.
    """
    print(f"Obteniendo empleos de: {rss_url}")
    feed = feedparser.parse(rss_url)

    jobs = []

    for entry in feed.entries:
        original_title = entry.get("title", "")

        # Separar el título por ':', '-' o '–' para aislar Empresa y Rol
        parts = re.split(r"[:–-]", original_title, maxsplit=1)

        if len(parts) > 1:
            company_name = parts[0].strip()
            role = parts[1].strip()
        else:
            company_name = "Unknown Company"
            role = original_title.strip()

        raw_description = entry.get("summary", entry.get("description", ""))
        description = clean_html(raw_description)

        text_to_search = f"{original_title} {description}"
        detected_techs = set()

        if hasattr(entry, "tags"):
            for tag in entry.tags:
                term = tag.get("term", "")
                if term:
                    sub_skills = re.split(
                        r",|\sand\s|/|\s&\s", term, flags=re.IGNORECASE
                    )
                    for s in sub_skills:
                        clean_s = s.strip()
                        if clean_s:
                            detected_techs.add(clean_s)

        if JOB_TECHS:
            for tech in JOB_TECHS:
                tech_clean = tech.strip()
                if not tech_clean:
                    continue

                escaped_tech = re.escape(tech_clean)
                pattern = rf"\b{escaped_tech}\b"

                if re.search(pattern, text_to_search, re.IGNORECASE):
                    detected_techs.add(tech_clean)

        job_data = {
            "title": original_title,
            "company_name": company_name,
            "role": role,
            "techs": list(detected_techs),
            "description": description,
            "url": entry.get("link", ""),
        }

        jobs.append(job_data)

    return jobs


def run():
    print(
        "📡 [WWR Scraper] Iniciando descarga con validación directa sobre techs detectadas..."
    )
    print(f"Feeds configurados: {WWR_RSS_FEEDS}")

    rss_urls = [url.strip() for url in WWR_RSS_FEEDS if url.strip()]
    if not rss_urls:
        rss_urls = ["https://weworkremotely.com/remote-jobs.rss"]

    with Session(engine) as session:
        total_saved = 0

        for rss_url in rss_urls:
            print(f"🔄 [WWR Scraper] Consultando feed: {rss_url}")
            found_jobs = fetch_wwr_jobs(rss_url=rss_url)

            for job in found_jobs:
                if JOB_TECHS:
                    required_techs = {t.strip().lower() for t in JOB_TECHS if t.strip()}
                    job_techs_lower = {t.strip().lower() for t in job["techs"]}

                    # Comprobamos si al menos una tecnología requerida está presente en las techs de la oferta
                    tech_matched = any(req in job_techs_lower for req in required_techs)
                    if not tech_matched:
                        continue

                source_name = "We Work Remotely"
                source = session.exec(
                    select(JobSource).where(JobSource.name == source_name)
                ).first()

                if not source:
                    source = JobSource(
                        name=source_name, base_url="https://weworkremotely.com"
                    )
                    session.add(source)
                    session.commit()
                    session.refresh(source)

                company = session.exec(
                    select(Company).where(Company.name == job["company_name"])
                ).first()

                if not company:
                    company = Company(name=job["company_name"])
                    session.add(company)
                    session.commit()
                    session.refresh(company)

                existing_offer = session.exec(
                    select(JobOffer).where(JobOffer.url == job["url"])
                ).first()

                if existing_offer:
                    continue

                new_offer = JobOffer(
                    title=job["title"],
                    role=job["role"],
                    description=job["description"],
                    url=job["url"],
                    company_id=company.id,
                    source_id=source.id,
                )

                session.add(new_offer)
                session.commit()
                total_saved += 1
                print(
                    f"✨ [Guardada] {job['company_name']} -> {job['role']} | Techs: {job['techs']}"
                )

        print(
            f"✅ [WWR Scraper] Sincronización completada. Guardadas: {total_saved} ofertas relevantes."
        )
