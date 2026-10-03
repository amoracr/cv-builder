import httpx
from config import JOB_TECHS, JOBICY_URL, JOBICY_LOCATIONS, JOBICY_INDUSTRIES
from .base_scraper import BaseScraper


class JobicyScraper(BaseScraper):
    def __init__(self):
        super().__init__(source_name="Jobicy", base_url="https://jobicy.com")
        # Endpoint de la API JSON pública de Jobicy (trae hasta 50 o los que configures)
    

    def fetch_jobs(self,rss_url: str):
        print(f"Obteniendo empleos de Jobicy desde la API: {rss_url}")
        jobs = []

        try:
            response = httpx.get(rss_url, timeout=15.0)
            if response.status_code != 200:
                print(f"Error al consultar Jobicy API: HTTP {response.status_code}")
                return []

            data = response.json()
            items = data.get("jobs", [])

            for item in items:
                original_title = item.get("jobTitle", "Sin título")
                company_name = item.get("companyName", "Unknown Company").strip()

                # Jobicy suele proveer la categoría o industria como el rol base
                industry = item.get("jobIndustry", original_title)
                if isinstance(industry, list):
                    # Si es una lista, unimos los elementos con comas (o tomamos el primero)
                    role = ", ".join([str(ind).strip() for ind in industry if ind]) if industry else original_title
                elif isinstance(industry, str):
                    role = industry.strip() or original_title
                else:
                    role = original_title

                # Región (Jobicy maneja geos como 'all', 'usa', 'emea', etc.)
                region = item.get("jobGeo", "Anywhere")
                region = self.clean_special_characters(region)

                # Limpieza de descripción HTML
                raw_description = item.get("jobDescription", "")
                description = self.clean_html(raw_description)
                description = self.clean_special_characters(description)

                # Extraer tags si vienen en el JSON (Jobicy suele incluir jobTags como string separado por comas o array)
                initial_tags = []
                tags_raw = item.get("jobTags", "")
                if isinstance(tags_raw, str):
                    initial_tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
                elif isinstance(tags_raw, list):
                    initial_tags = [str(t) for t in tags_raw]

                text_to_search = f"{original_title} {description}"
                techs = self.detect_techs(text_to_search, initial_tags)

                job_data = {
                    "title": original_title,
                    "company_name": company_name,
                    "role": role,
                    "region": region,
                    "techs": techs,
                    "description": description,
                    "url": item.get("url", ""),
                }
                jobs.append(job_data)

        except Exception as e:
            print(f"Excepción conectando con la API de Jobicy: {str(e)}")

        return jobs

    def run(self):
        print("📡 [Jobicy Scraper] Iniciando sincronización...")
        total_saved = 0
        target_tags = [t.strip().lower() for t in JOB_TECHS if t.strip()]
        locations = [loc.strip() for loc in JOBICY_LOCATIONS if loc.strip()]
        industries = [ind.strip() for ind in JOBICY_INDUSTRIES if ind.strip()]

        api_urls = []
        base_api = JOBICY_URL

        for geo in locations:
            for industry in industries:                
                    url = f"{base_api}?geo={geo}&industry={industry}"
                    api_urls.append(url)

        for geo in locations:
            for tag in target_tags:
                url = f"{base_api}?geo={geo}&tag={tag}"
                api_urls.append(url)
        
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
                        f"✨ [Guardada - Jobicy] {job['company_name']} -> {job['role']} | Techs: {job['techs']}"
                    )

        print(
            f"✅ [Jobicy Scraper] Sincronización completada. Guardadas: {total_saved} ofertas."
        )
