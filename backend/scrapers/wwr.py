import re
from html import unescape

import feedparser
from config import JOB_ROLES, JOB_TECHS, WWR_CATEGORIES, WWR_RSS_FEEDS
from database import engine
from models import JobOffer
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
    Retorna una lista de diccionarios con title, skills, category, description y link.
    """
    print(f"Obteniendo empleos de: {rss_url}")
    feed = feedparser.parse(rss_url)

    jobs = []

    for entry in feed.entries:
        # 1. Título del puesto
        title = entry.get("title", "")

        # 2. Categoría (WWR suele ponerla en 'category' o dentro de las etiquetas 'tags')
        category = entry.get("category", "")
        if not category and hasattr(entry, "tags") and entry.tags:
            category = entry.tags[0].get("term", "")

        # 3. Descripción (el RSS suele traer HTML en 'summary' o 'description')
        raw_description = entry.get("summary", entry.get("description", ""))
        description = clean_html(raw_description)

        # 4. Skills / Tech Stack con limpieza inteligente de compuestos (ej. "Django and Python")
        skills = []
        if hasattr(entry, "tags"):
            for tag in entry.tags:
                term = tag.get("term", "")
                if term:
                    # Separa por comas, 'and', barras o ampersands para aislar habilidades individuales
                    sub_skills = re.split(
                        r",|\sand\s|/|\s&\s", term, flags=re.IGNORECASE
                    )
                    for s in sub_skills:
                        clean_s = s.strip()
                        if clean_s:
                            skills.append(clean_s)

        job_data = {
            "title": title,
            "skills": skills,
            "category": category,
            "description": description,
            "link": entry.get("link", ""),
        }

        jobs.append(job_data)

    return jobs


def run():
    print(
        "📡 [WWR Scraper] Iniciando descarga con filtro estricto por Categoría y Stack..."
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
                # 1. Filtro de Categoría (si se configuraron categorías en el .env)
                if WWR_CATEGORIES:
                    job_cat_lower = job["category"].lower()
                    if not any(cat in job_cat_lower for cat in WWR_CATEGORIES):
                        continue  # Descarta si la categoría no coincide

                # Unimos el título, descripción y skills en un solo bloque de texto para buscar
                text_to_search = (
                    f"{job['title']} {job['description']} {' '.join(job['skills'])}"
                )

                # 2. Filtro de Roles (ej: Backend, Full Stack) usando límites de palabra \b
                if JOB_ROLES:
                    role_matched = any(
                        re.search(
                            rf"\b{re.escape(role)}\b", text_to_search, re.IGNORECASE
                        )
                        for role in JOB_ROLES
                    )
                    if not role_matched:
                        continue

                # 3. Filtro de Tecnologías / Stack (ej: Python, Django) usando límites de palabra \b
                if JOB_TECHS:
                    tech_matched = any(
                        re.search(
                            rf"\b{re.escape(tech)}\b", text_to_search, re.IGNORECASE
                        )
                        for tech in JOB_TECHS
                    )
                    if not tech_matched:
                        continue

                # 4. Verificar si ya existe en la base de datos por el link (evitar duplicados)
                existing_offer = session.exec(
                    select(JobOffer).where(JobOffer.link == job["link"])
                ).first()

                if existing_offer:
                    continue  # Ya la tenemos registrada, saltamos

                # 5. Guardar la oferta relevante en la base de datos
                new_offer = JobOffer(
                    title=job["title"],
                    description=job["description"],
                    category=job["category"],
                    link=job["link"],
                )

                session.add(new_offer)
                session.commit()
                total_saved += 1
                print(f"✨ [Guardada] {job['title']}")

        print(
            f"✅ [WWR Scraper] Sincronización completada. Guardadas: {total_saved} ofertas relevantes."
        )
