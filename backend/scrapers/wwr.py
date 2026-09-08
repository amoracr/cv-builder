import re

import feedparser
from .base_scraper import BaseScraper
from config import JOB_TECHS, WWR_RSS_FEEDS


class WWRScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            source_name="We Work Remotely", base_url="https://weworkremotely.com"
        )

    def fetch_jobs(self, rss_url: str):
        print(f"Obteniendo empleos de WWR: {rss_url}")
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

            region = entry.get("region", "")
            raw_description = entry.get("summary", entry.get("description", ""))
            description = self.clean_html(raw_description)

            # Obtener tags iniciales de WWR
            initial_tags = []
            if hasattr(entry, "tags"):
                for tag in entry.tags:
                    term = tag.get("term", "")
                    if term:
                        initial_tags.append(term)

            # Usar el método heredado para detectar tecnologías
            text_to_search = f"{original_title} {description}"
            techs = self.detect_techs(text_to_search, initial_tags)

            job_data = {
                "title": original_title,
                "company_name": company_name,
                "role": role,
                "region": region,
                "techs": techs,
                "description": description,
                "url": entry.get("link", ""),
            }
            jobs.append(job_data)

        return jobs

    def run(self):
        print("📡 [WWR Scraper] Iniciando sincronización...")
        rss_urls = [url.strip() for url in WWR_RSS_FEEDS if url.strip()]
        if not rss_urls:
            rss_urls = ["https://weworkremotely.com/remote-jobs.rss"]

        total_saved = 0

        for rss_url in rss_urls:
            print(f"🔄 [WWR Scraper] Consultando feed: {rss_url}")
            found_jobs = self.fetch_jobs(rss_url)

            for job in found_jobs:
                # 1. Filtro de Región: Debe incluir "Anyware" o "Anywhere"
                region_text = job.get("region", "")
                if not re.search(
                    r"anywhere|anyw(a|e)re|worldwide|global", region_text, re.IGNORECASE
                ):
                    continue

                # 2. Filtro de Tecnologías
                if JOB_TECHS:
                    required_techs = {t.strip().lower() for t in JOB_TECHS if t.strip()}
                    job_techs_lower = {t.strip().lower() for t in job["techs"]}
                    if not any(req in job_techs_lower for req in required_techs):
                        print(
                            f"Skipping techs [RAW WWR] Título: {job['title']} | Región: {job['region']} | Techs detectadas: {job['techs']}"
                        )
                        continue

                # 3. Guardar usando el método genérico de la clase base
                saved = self.save_job(job)
                if saved:
                    total_saved += 1
                    print(
                        f"✨ [Guardada - WWR] {job['company_name']} -> {job['role']} | Techs: {job['techs']}"
                    )

        print(
            f"✅ [WWR Scraper] Sincronización completada. Guardadas: {total_saved} ofertas."
        )
