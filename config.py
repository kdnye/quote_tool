# config.py
import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = (
        os.getenv("DATABASE_URL") or  # e.g. mysql+pymysql://user:pass@host/db
        "sqlite:///app.db"
    )
    # Legacy configuration expected by old modules/tests
    DATABASE_URL = SQLALCHEMY_DATABASE_URI
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WORKBOOK_PATH = os.getenv("WORKBOOK_PATH", "HotShot Quote.xlsx")
    GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
    # Mail/reset settings (optional):
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "no-reply@example.com")
    WTF_CSRF_ENABLED = True
