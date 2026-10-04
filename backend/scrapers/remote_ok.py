import re

import requests
from config import JOB_TECHS, REMOTEOK_URL

from .base_scraper import BaseScraper


class RemoteOKScraper(BaseScraper):
    def __init__(self):
        super().__init__(source_name="Remote OK", base_url="https://remoteok.com")

    def fetch_jobs(self, rss_url: str):

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        print(f"Obteniendo empleos de Remote OK API: {rss_url}")
        try:
            response = requests.get(rss_url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"❌ Error al conectar con Remote OK: {e}")
            return []

        jobs = []
        entries = data[1:] if len(data) > 1 else data

        for entry in entries:
            if not isinstance(entry, dict):
                continue

            company_name = entry.get("company", "Unknown Company")
            company_name = self.clean_special_characters(company_name)
            role = entry.get("position", "")
            role = self.clean_special_characters(role)
            if not role:
                continue

            title = f"{company_name}: {role}"
            region = entry.get("location", "Anywhere")
            region = self.clean_special_characters(region)
            raw_description = entry.get("description", "")
            description = self.clean_html(raw_description)
            description = self.clean_special_characters(description)
            job_url = entry.get("url", "") or entry.get("apply_url", "")
            if not job_url:
                continue

            raw_tags = entry.get("tags", [])
            text_to_search = f"{role} {description} {' '.join(raw_tags)}"

            techs = self.detect_techs(text_to_search, raw_tags)

            job_data = {
                "title": title,
                "company_name": company_name,
                "role": role,
                "region": region,
                "techs": techs,
                "description": description,
                "url": job_url,
            }
            jobs.append(job_data)

        return jobs

    def run(self):
        print("📡 [Remote OK Scraper] Iniciando sincronización...")
        api_url = REMOTEOK_URL
        target_tags = [t.strip().lower() for t in JOB_TECHS if t.strip()]
        api_urls = [f"{api_url}?tags={tag}" for tag in target_tags]
        total_saved = 0

        for rss_url in api_urls:
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
                        f"✨ [Guardada - RemoteOK] {job['company_name']} -> {job['role']} | Techs: {job['techs']}"
                    )

        print(
            f"✅ [Remote OK Scraper] Sincronización completada. Guardadas: {total_saved} ofertas."
        )
