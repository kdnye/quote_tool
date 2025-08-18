import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration.

    The database URL is resolved using the following precedence:

    1. ``DATABASE_URL`` environment variable.
    2. Individual MySQL settings via ``MYSQL_HOST``, ``MYSQL_PORT``,
       ``MYSQL_USER``, ``MYSQL_PASSWORD`` and ``MYSQL_DATABASE``/``MYSQL_DB``.
    3. Fallback to a local SQLite database.
    """

    _db_url = os.getenv("DATABASE_URL")

    if not _db_url:
        mysql_host = os.getenv("MYSQL_HOST")
        mysql_port = os.getenv("MYSQL_PORT", "3306")
        mysql_user = os.getenv("MYSQL_USER")
        mysql_password = os.getenv("MYSQL_PASSWORD", "")
        mysql_db = os.getenv("MYSQL_DATABASE") or os.getenv("MYSQL_DB")

        if mysql_host and mysql_user and mysql_db:
            _db_url = (
                f"mysql+pymysql://{mysql_user}:{mysql_password}"
                f"@{mysql_host}:{mysql_port}/{mysql_db}"
            )

    DATABASE_URL = _db_url or "sqlite:///app.db"
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    WORKBOOK_PATH = os.getenv("WORKBOOK_PATH", "HotShot Quote.xlsx")
