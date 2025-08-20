#init_db.py
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, Text, DateTime, ForeignKey, inspect
from sqlalchemy.orm import declarative_base, sessionmaker
from werkzeug.security import generate_password_hash
from sqlalchemy.sql import func
import uuid
from config import Config

# === Database Path ===
engine = create_engine(Config.DATABASE_URL, echo=True)
Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()

# === Models ===
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False, unique=True)
    phone = Column(String(50))
    business_name = Column(String(100))
    business_phone = Column(String(50))
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="user")  # 'admin' or 'user'
    is_approved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Quote(Base):
    __tablename__ = "quotes"
    id = Column(Integer, primary_key=True)
    quote_id = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    quote_type = Column(String(20))  # hotshot or air
    origin = Column(String(20))
    destination = Column(String(20))
    weight = Column(Float)
    weight_method = Column(String(20))
    actual_weight = Column(Float)
    dim_weight = Column(Float)
    pieces = Column(Integer)
    length = Column(Float)
    width = Column(Float)
    height = Column(Float)
    zone = Column(String(5))
    total = Column(Float)
    quote_metadata = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)



# === Create Tables if Missing ===
inspector = inspect(engine)
tables = inspector.get_table_names()

if "users" not in tables or "quotes" not in tables:
    Base.metadata.create_all(engine)
    print("✅ Database schema initialized.")
else:
    print("ℹ️ Tables already exist. Skipping creation.")

# === Seed Default Admin ===
admin_email = os.getenv("ADMIN_EMAIL")
admin_password = os.getenv("ADMIN_PASSWORD")

if admin_email and admin_password:
    existing_admin = session.query(User).filter_by(email=admin_email).first()

    if not existing_admin:
        admin_user = User(
            name="Admin",
            email=admin_email,
            phone="555-0000",
            business_name="FSI",
            business_phone="555-1111",
            password_hash=generate_password_hash(admin_password),
            role="admin",
            is_approved=True,
        )
        session.add(admin_user)
        session.commit()
        print("✅ Default admin user created.")
    else:
        print("ℹ️ Admin user already exists.")
else:
    print("ℹ️ ADMIN_EMAIL or ADMIN_PASSWORD not set. Skipping admin user creation.")
