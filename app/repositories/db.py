import oracledb
from app.config.settings import settings

def get_connection():
    return oracledb.connect(
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        dsn=settings.DB_DSN
    )