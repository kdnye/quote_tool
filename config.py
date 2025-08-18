import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///app.db')
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    WORKBOOK_PATH = os.getenv('WORKBOOK_PATH', 'HotShot Quote.xlsx')
