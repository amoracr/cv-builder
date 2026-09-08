import re
import requests
from .base_scraper import BaseScraper
from config import JOB_TECHS


class RemoteOKScraper(BaseScraper):
    def __init__(self):
        super().__init__(source_name="Remote OK", base_url="https://remoteok.com")

    def fetch_jobs(self, rss_url: str = None):
        api_url = "https://remoteok.com/api"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        print(f"Obteniendo empleos de Remote OK API: {api_url}")
        try:
            response = requests.get(api_url, headers=headers, timeout=15)
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
            role = entry.get("position", "")
            if not role:
                continue

            title = f"{company_name}: {role}"
            location = entry.get("location", "")
            raw_description = entry.get("description", "")
            description = self.clean_html(raw_description)
            job_url = entry.get("url", "") or entry.get("apply_url", "")
            if not job_url:
                continue

            raw_tags = entry.get("tags", [])
            text_to_search = f"{role} {description} {' '.join(raw_tags)}"

            # Detectar tecnologías usando el método heredado
            techs = self.detect_techs(text_to_search, raw_tags)

            job_data = {
                "title": title,
                "company_name": company_name,
                "role": role,
                "location": location,
                "techs": techs,
                "description": description,
                "url": job_url,
            }
            jobs.append(job_data)

        return jobs

    def run(self):
        print("📡 [Remote OK Scraper] Iniciando sincronización...")
        found_jobs = self.fetch_jobs()
        total_saved = 0

        for job in found_jobs:
            # 1. Filtro de Región global
            location_text = job.get("location", "")
            if not re.search(
                r"\b(anywhere|worldwide|remote)\b", location_text, re.IGNORECASE
            ):
                continue

            # 2. Filtro de Tecnologías
            if JOB_TECHS:
                required_techs = {t.strip().lower() for t in JOB_TECHS if t.strip()}
                job_techs_lower = {t.strip().lower() for t in job["techs"]}
                if not any(req in job_techs_lower for req in required_techs):
                    continue

            # 3. Guardar usando la clase base
            saved = self.save_job(job)
            if saved:
                total_saved += 1
                print(
                    f"✨ [Guardada - RemoteOK] {job['company_name']} -> {job['role']} | Techs: {job['techs']}"
                )

        print(
            f"✅ [Remote OK Scraper] Sincronización completada. Guardadas: {total_saved} ofertas."
        )
