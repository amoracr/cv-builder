import requests
from .base_scraper import BaseScraper
from config import JOB_TECHS, REMOTIVE_CATEGORY


class RemotiveScraper(BaseScraper):
    def __init__(self):
        super().__init__(source_name="Remotive", base_url="https://remotive.com")

    def fetch_jobs(self, rss_url: str):

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        print(" [Remotive Scraper] Conectando con la API...")
        try:
            response = requests.get(rss_url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"❌ Error al conectar con Remotive: {e}")
            return []

        entries = data.get("jobs", [])
        all_jobs = []

        for entry in entries:
            if not isinstance(entry, dict):
                continue

            job_url = entry.get("url", "")
            if not job_url:
                continue

            company_name = entry.get("company_name", "Unknown Company")
            role = entry.get("title", "")
            if not role:
                continue

            title = f"{company_name}: {role}"
            location = entry.get("candidate_required_location", "")

            raw_description = entry.get("description", "")
            description = self.clean_html(raw_description)
            description = self.clean_special_characters(description)

            raw_tags = entry.get("tags", [])
            text_to_search = f"{role} {description} {' '.join(raw_tags)}"

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
            all_jobs.append(job_data)

        return all_jobs

    def run(self):
        print("🚀 [Remotive Scraper] Iniciando procesamiento de ofertas...")
        api_url = "https://remotive.com/api/remote-jobs"
        target_tags = [t.strip().lower() for t in REMOTIVE_CATEGORY if t.strip()]
        api_urls = [f"{api_url}?category={tag}" for tag in target_tags]
        total_saved = 0

        for rss_url in api_urls:
            found_jobs = self.fetch_jobs(rss_url)

            for job in found_jobs:
                # 1. Validar región global/remota
                if not self.validate_region({"region": job.get("location", "")}):
                    continue

                # 2. Filtrar por tecnologías del .env
                if JOB_TECHS:
                    required_techs = {t.strip().lower() for t in JOB_TECHS if t.strip()}
                    job_techs_lower = {t.strip().lower() for t in job["techs"]}
                    if not any(req in job_techs_lower for req in required_techs):
                        continue

                # 3. Guardar en base de datos
                saved = self.save_job(job)
                if saved:
                    total_saved += 1
                    print(
                        f"✨ [Guardada - Remotive] {job['company_name']} -> {job['role']} | Ubicación: {job.get('location', 'Global')} | Techs: {job['techs']}"
                    )

        print(f"✅ [Remotive Scraper] Finalizado. Guardadas: {total_saved} ofertas.")
        return total_saved
