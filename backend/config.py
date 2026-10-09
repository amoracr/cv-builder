import os
from pathlib import Path

from dotenv import load_dotenv

# Sube un nivel desde 'backend/config.py' hacia la raíz del proyecto para buscar el .env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

PORT = int(os.getenv("BACKEND_PORT", 8000))
DB_PATH = os.getenv("DB_PATH", "sqlite:///./data/cv_builder.db")
JOB_TECHS = os.getenv("JOB_TECHS", "").split(",")
WWR_RSS_FEEDS = os.getenv("WWR_RSS", "").split(",")
REMOTEOK_URL = os.getenv("REMOTEOK_URL", "")
REMOTIVE_URL = os.getenv("REMOTIVE_URL", "")
REMOTIVE_CATEGORY = os.getenv("REMOTIVE_CATEGORY", "").split(",")
JOBICY_URL = os.getenv("JOBICY_URL", "")
JOBICY_LOCATIONS = os.getenv("JOBICY_LOCATIONS", "").split(",")
JOBICY_INDUSTRIES = os.getenv("JOBICY_INDUSTRIES", "").split(",")
GET_ON_BOARD_URL = os.getenv("GET_ON_BOARD_URL", "")
