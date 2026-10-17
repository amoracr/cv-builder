import html
import re
import time
import unicodedata

import feedparser
import requests
import spacy
from bs4 import BeautifulSoup
from config import JOB_TECHS, RFJ_RSS, RFJ_URL

from .base_scraper import BaseScraper


class RemoteFirstJobsScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            source_name="Remote First Jobs", base_url="https://remotefirstjobs.com"
        )
        # Cargar el modelo ligero de spaCy en inglés para extracción de ubicaciones
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except Exception as e:
            print(f"⚠️ No se pudo cargar el modelo de spaCy: {e}")
            self.nlp = None

    def sanitize_job_description(self, text: str) -> str:
        """Elimina etiquetas HTML, caracteres especiales, emojis e inconsistencias

        de formato, dejando un texto en plano limpio y legible.
        """
        if not text:
            return ""

        # 1. Decodificar entidades HTML (&amp;, &lt;, &nbsp;, etc.)
        text = html.unescape(text)

        # 2. Remover etiquetas HTML residuales conservando saltos de línea
        soup = BeautifulSoup(text, "html.parser")
        for element in soup(["script", "style", "head", "meta", "noscript"]):
            element.extract()

        for br in soup.find_all("br"):
            br.replace_with("\n")
        for li in soup.find_all("li"):
            li.insert_before("- ")
            li.append("\n")

        text = soup.get_text(separator="\n")

        # 3. Normalizar caracteres Unicode
        text = unicodedata.normalize("NFKC", text)

        # 4. Remover emojis y símbolos gráficos Unicode
        emoji_pattern = re.compile(
            "["
            "\U0001f600-\U0001f64f"  # emoticons
            "\U0001f300-\U0001f5ff"  # symbols & pictographs
            "\U0001f680-\U0001f6ff"  # transport & map symbols
            "\U0001f1e0-\U0001f1ff"  # flags
            "\U00002702-\U000027b0"
            "\U000024c2-\U0001f251"
            "\U0001f900-\U0001f9ff"  # Supplemental Symbols and Pictographs
            "\U0001fa70-\U0001faf6"  # Symbols and Pictographs Extended-A
            "]+",
            flags=re.UNICODE,
        )
        text = emoji_pattern.sub("", text)

        # 5. Remover caracteres extraños preservando puntuación técnica (C++, C#, Node.js, etc.)
        text = re.sub(r"[^\w\s\.,;:\-\_\/\#\+\(\)\%\$\@\&\=\'\"]", "", text)

        # 6. Normalizar espaciado y saltos de línea múltiples
        lines = [line.strip() for line in text.splitlines()]
        cleaned_lines = []
        prev_empty = False

        for line in lines:
            if not line:
                if not prev_empty:
                    cleaned_lines.append("")
                    prev_empty = True
            else:
                cleaned_lines.append(line)
                prev_empty = False

        return "\n".join(cleaned_lines).strip()

    def extract_locations_with_spacy(self, text: str) -> list[str]:
        """Extrae países, ciudades y regiones usando entidades GPE y LOC de spaCy."""
        if not self.nlp or not text:
            return []

        # Analizar los primeros caracteres donde suele encontrarse la información clave
        doc = self.nlp(text[:2000])
        locations = set()
        ignore_list = {
            "remote",
            "hybrid",
            "full-time",
            "part-time",
            "engineer",
            "developer",
        }

        for ent in doc.ents:
            if ent.label_ in ("GPE", "LOC"):
                loc_clean = ent.text.strip()
                if len(loc_clean) > 2 and loc_clean.lower() not in ignore_list:
                    locations.add(loc_clean)

        return sorted(list(locations))

    def fetch_job_detail(self, url: str) -> tuple[str, str]:
        """Realiza una petición HTTP a la página de detalle de la oferta.

        Extrae la región (analizando tag <a> o usando spaCy) y la descripción limpia.
        Retorna una tupla: (region, description)
        """
        time.sleep(1)
        region = "Anywhere"
        description = ""

        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
            }
            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")

                # 1. Extracción de Ubicación (Estrategia DOM Tag -> spaCy Fallback)
                location_tag = soup.select_one("a[href*='/jobs/locations/']")
                if location_tag:
                    raw_location = location_tag.get_text(strip=True)
                    cleaned_location = re.sub(r"[^\w\s\-]", "", raw_location).strip()
                    if cleaned_location:
                        region = cleaned_location
                else:
                    # Respaldo inteligente con spaCy analizando el texto del DOM
                    header_text = soup.get_text()
                    detected_locs = self.extract_locations_with_spacy(header_text)
                    if detected_locs:
                        region = ", ".join(detected_locs)
                    else:
                        region = "Anywhere"

                # 2. Extracción y sanitización de la Descripción
                desc_elem = soup.select_one("article.prose")
                if desc_elem:
                    for br in desc_elem.find_all("br"):
                        br.replace_with("\n")
                    for li in desc_elem.find_all("li"):
                        li.insert_before("- ")
                        li.append("\n")

                    raw_description = desc_elem.get_text(separator="\n", strip=True)
                    description = self.sanitize_job_description(raw_description)

        except requests.exceptions.Timeout:
            print(f"⏱️ Timeout agotado al conectar con la oferta: {url}")
        except Exception as e:
            print(f"⚠️ Error al conectar con el detalle de la oferta {url} : {e}")

        return region, description

    def parse_job_heading(self, original_title: str) -> tuple[str, str]:
        """Extrae el rol y la empresa del título original utilizando patrones comunes.

        Retorna una tupla: (role, company_name)
        """
        role = original_title.strip() if original_title else "Unknown Role"
        company_name = "Unknown Company"

        if original_title:
            title_clean = original_title.strip()

            if " at " in title_clean:
                parts = title_clean.split(" at ", 1)
                role = parts[0].strip()
                company_name = parts[1].strip()
            elif " - " in title_clean:
                parts = title_clean.split(" - ", 1)
                role = parts[0].strip()
                company_name = parts[1].strip()
            elif " | " in title_clean:
                parts = title_clean.split(" | ", 1)
                role = parts[0].strip()
                company_name = parts[1].strip()

        return role, company_name

    def fetch_jobs(self, rss_url: str):
        print(f"🔄 [Remote First Jobs Scraper] Verificando feed RSS: {rss_url}")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        try:
            response = requests.head(rss_url, headers=headers, timeout=10)
            if response.status_code != 200:
                print(
                    f"❌ RSS no disponible (Status {response.status_code}): {rss_url}"
                )
                return []
        except Exception as e:
            print(f"❌ Error de conexión al verificar el RSS {rss_url}: {e}")
            return []

        feed = feedparser.parse(rss_url)
        if not hasattr(feed, "entries") or not feed.entries:
            print(f"⚠️ El RSS existe pero está vacío: {rss_url}")
            return []

        jobs = []

        for entry in feed.entries:
            original_title = entry.get("title", "")
            job_url = entry.get("link", "")
            role, company_name = self.parse_job_heading(original_title)
            region, description = self.fetch_job_detail(job_url)
            techs = self.detect_techs(f"{original_title} {description}")

            job_data = {
                "title": original_title,
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
        print("📡 [Remote First Jobs Scraper] Iniciando sincronización...")
        rss_urls = [url.strip() for url in RFJ_RSS if url.strip()]

        target_tags = [t.strip().lower() for t in JOB_TECHS if t.strip()]
        base_api = RFJ_URL
        for tag in target_tags:
            url = f"{base_api}{tag}.rss"
            rss_urls.append(url)

        total_saved = 0

        for rss_url in rss_urls:
            print(f"🔄 [Remote First Jobs Scraper] Consultando feed: {rss_url}")
            found_jobs = self.fetch_jobs(rss_url)

            for job in found_jobs:
                if self.job_offer_exists(job["url"]):
                    print(f"Job {job['url']} already in db")
                    continue

                print(
                    f"Job: [{job['title']}, {job['role']}, {job['region']},"
                    f" {job['techs']}]"
                )
                if not self.validate_region(job_data=job):
                    continue

                if not self.validate_tech_stack(job_data=job):
                    continue

                saved = self.save_job(job)
                if saved:
                    total_saved += 1

        print(
            f"✅ [Remote First Jobs Scraper] Sincronización completada. Guardadas:"
            f" {total_saved} ofertas."
        )
