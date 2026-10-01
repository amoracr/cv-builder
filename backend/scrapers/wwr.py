import re

import feedparser
from config import JOB_TECHS, WWR_RSS_FEEDS

from .base_scraper import BaseScraper


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

            region = entry.get("region", "Anywhere")
            region = self.clean_special_characters(region)
            raw_description = entry.get("summary", entry.get("description", ""))
            description = self.clean_html(raw_description)
            description = self.clean_special_characters(description)

            initial_tags = []
            if hasattr(entry, "tags"):
                for tag in entry.tags:
                    term = tag.get("term", "")
                    if term:
                        initial_tags.append(term)

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
                if not self.validate_region(job_data=job):
                    continue

                if not self.validate_tech_stack(job_data=job):
                    continue

                saved = self.save_job(job)
                if saved:
                    total_saved += 1
                    print(
                        f"✨ [Guardada - WWR] {job['company_name']} -> {job['role']} | Techs: {job['techs']}"
                    )

        print(
            f"✅ [WWR Scraper] Sincronización completada. Guardadas: {total_saved} ofertas."
        )
