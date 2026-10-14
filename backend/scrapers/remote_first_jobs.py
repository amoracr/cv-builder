import re

import feedparser
from config import JOB_TECHS, RFJ_RSS, RFJ_URL

from .base_scraper import BaseScraper


class RemoteFirstJobsScraper(BaseScraper):

  def __init__(self):
    super().__init__(
        source_name="Remote First Jobs", base_url="https://remotefirstjobs.com"
    )

  def fetch_jobs(self, rss_url: str):
    print(f"Obteniendo empleos de Remote First Jobs: {rss_url}")
    feed = feedparser.parse(rss_url)
    jobs = []

    for entry in feed.entries:
      original_title = entry.get("title", "")

      # En este RSS el formato suele ser: "Rol (Ubicación) at Empresa"
      # Ejemplo: "Senior Data Engineer (India) at Karat"
      company_name = "Unknown Company"
      role = original_title

      if " at " in original_title:
        parts = original_title.split(" at ", 1)
        role = parts[0].strip()
        company_name = parts[1].strip()

      # Intentamos extraer región del título o usar un valor por defecto
      region = "Anywhere"
      match_region = re.search(r"\((.*?)\)", role)
      if match_region:
        region = match_region.group(1).strip()
        role = re.sub(r"\s*\(.*?\)", "", role).strip()

      region = self.clean_special_characters(region)
      raw_description = entry.get("description", "")
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
    print("📡 [Remote First Jobs Scraper] Iniciando sincronización...")
    rss_urls = [url.strip() for url in RFJ_RSS if url.strip()]

    target_tags = [t.strip().lower() for t in JOB_TECHS if t.strip()]
    base_api = RFJ_URL
    for tag in target_tags:
      url = f"{base_api}{tag}.rss"
      rss_urls.append(url)

    total_saved = 0

    for rss_url in rss_urls:
      print(
          f"🔄 [Remote First Jobs Scraper] Consultando feed: {rss_url}"
      )
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
        f"✅ [Remote First Jobs Scraper] Sincronización completada. Guardadas:"
        f" {total_saved} ofertas."
    )