import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_ENV_PATH = BASE_DIR / ".env"
LOCAL_ENV_PATH = BASE_DIR / ".env.local"

load_dotenv(DEFAULT_ENV_PATH)
load_dotenv(LOCAL_ENV_PATH, override=True)

class Settings:
    LAW_API_KEY = os.getenv("LAW_API_KEY")
    ENV_PATH = str(DEFAULT_ENV_PATH)
    DB_PATH = os.getenv(
        "DB_PATH",
        os.path.expanduser("~/workspace/raw-monitor/raw_monitor.db")
    )
    SECRET_KEY = os.getenv("SECRET_KEY", "raw-monitor-dev-secret")
    WEB_HOST = os.getenv("WEB_HOST", "127.0.0.1")
    WEB_PORT = int(os.getenv("WEB_PORT", 5000))
    WEB_DEBUG = os.getenv("WEB_DEBUG", "false").lower() == "true"

    MAIL_HOST = os.getenv("MAIL_HOST", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 465))
    MAIL_USER = os.getenv("MAIL_USER")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_TO = os.getenv("MAIL_TO")

settings = Settings()
