import os
from pathlib import Path

from dotenv import load_dotenv

# Sube un nivel desde 'backend/config.py' hacia la raíz del proyecto para buscar el .env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

PORT = int(os.getenv("PORT", 8000))
DB_PATH = os.getenv("DB_PATH", "sqlite:///./data/cv_builder.db")
JOB_TECHS = os.getenv("JOB_TECHS", "").split(",")
WWR_RSS_FEEDS = os.getenv("WWR_RSS", "").split(",")
REMOTIVE_CATEGORY = os.getenv("REMOTIVE_CATEGORY","").split(",")