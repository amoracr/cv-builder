import httpx
from config import JOB_TECHS, GET_ON_BOARD_URL

from .base_scraper import BaseScraper


class GetOnBoardScraper(BaseScraper):
    def __init__(self):
        super().__init__(source_name="GetOnBoard", base_url="https://www.getonbrd.com")

    def fetch_jobs(self, rss_url: str):
        print(f"Obteniendo empleos de GetOnBoard: {rss_url}")
        jobs = []
        page = 1
        separator = "&" if "?" in rss_url else "?"
        current_url = f"{rss_url}{separator}page={page}"

        while current_url:
            try:
                response = httpx.get(current_url, timeout=15.0)
                if response.status_code != 200:
                    print(
                        f"Error al consultar GetOnBoard API: HTTP {response.status_code}"
                    )
                    return []

                data = response.json()
                items = data.get("data", [])

                for item in items:
                    attributes = item.get("attributes", {})

                    is_remote = attributes.get("remote", False)
                    if not is_remote:
                        continue

                    original_title = attributes.get("title", "Sin título")
                    company_id = (
                        attributes.get("company", {}).get("data", {}).get("id", 0)
                    )
                    company_name = self.get_company_name(company_id)

                    role = " ".join(
                        [original_title, attributes.get("category_name", "")]
                    )

                    # Región / Ubicación
                    country = attributes.get("countries", [])
                    region = ",".join(country) if len(country) > 0 else ""

                    # Descripcion
                    raw_description = []
                    raw_description.append(attributes.get("description", ""))
                    raw_description.append(attributes.get("projects", ""))
                    raw_description.append(attributes.get("benefits", ""))
                    raw_description.append(attributes.get("desirable", ""))
                    raw_description = " ".join(raw_description)
                    description = self.clean_html(raw_description)
                    description = self.clean_special_characters(description)

                    # URL
                    url = item.get("links", {}).get("public_url", "")

                    # Tags o tecnologías si vienen especificadas

                    text_to_search = f"{original_title} {description}"
                    techs = self.detect_techs(text_to_search)

                    job_data = {
                        "title": original_title,
                        "company_name": company_name,
                        "role": role,
                        "region": region,
                        "techs": techs,
                        "description": description,
                        "url": url,
                    }
                    jobs.append(job_data)

                total_pages = data.get("meta", {}).get("total_pages", 1)
                if page < total_pages:
                    # Construimos la páginación
                    page += 1
                    separator = "&" if "?" in rss_url else "?"
                    current_url = f"{rss_url}{separator}page={page}"
                else:
                    # Terminamos la paginación para esta URL
                    current_url = None

            except Exception as e:
                print(f"Excepción conectando con GetOnBoard: {str(e)}")

        return jobs

    def run(self):
        print("📡 [GetOnBoard Scraper] Iniciando sincronización...")
        total_saved = 0

        base_api = GET_ON_BOARD_URL
        api_urls = []
        target_tags = [t.strip().lower() for t in JOB_TECHS if t.strip()]

        for tag in target_tags:
            url = f"{base_api}/search/jobs?query={tag}"
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
                        f"✨ [Guardada - GetOnBoard] {job['company_name']} -> {job['title']}"
                    )

        print(
            f"✅ [GetOnBoard Scraper] Sincronización completada. Guardadas: {total_saved} ofertas."
        )

    def get_company_name(self, id: str):
        base_url = GET_ON_BOARD_URL
        api_url = f"{base_url}/companies/{id}"
        name = "Unknown Company"

        try:
            response = httpx.get(api_url, timeout=15.0)
            if response.status_code != 200:
                print(f"Error al consultar GetOnBoard API: HTTP {response.status_code}")

            data = response.json()
            name = (
                data.get("data", {})
                .get("attributes", {})
                .get("name", "Unknown Company")
            )

        except Exception as e:
            print(f"Excepción conectando con la API de GetOnBoard: {str(e)}")

        return name
