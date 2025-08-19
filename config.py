# config.py
import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = (
        os.getenv("DATABASE_URL") or  # e.g. mysql+pymysql://user:pass@host/db
        "sqlite:///app.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WORKBOOK_PATH = os.getenv("WORKBOOK_PATH", "HotShot Quote.xlsx")
    GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
    # Mail/reset settings (optional):
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "no-reply@example.com")
