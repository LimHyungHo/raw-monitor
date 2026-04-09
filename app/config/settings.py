import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    LAW_API_KEY = os.getenv("LAW_API_KEY")

    MAIL_HOST = os.getenv("MAIL_HOST", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 465))
    MAIL_USER = os.getenv("MAIL_USER")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_TO = os.getenv("MAIL_TO")

settings = Settings()