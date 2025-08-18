# db.py
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
from sqlalchemy.sql import func
import uuid
from flask_login import UserMixin

DB_PATH = "sqlite:///app.db"
engine = create_engine(DB_PATH)
Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()

class User(Base, UserMixin):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    phone = Column(String(50))
    business_name = Column(String(100))
    business_phone = Column(String(50))
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="user")
    is_approved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    quotes = relationship("Quote", back_populates="user")

class Quote(Base):
    __tablename__ = 'quotes'
    id = Column(Integer, primary_key=True)
    quote_id = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    user_email = Column(String(100))
    quote_type = Column(String(20))
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
    quote_metadata = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="quotes")
    
class EmailQuoteRequest(Base):
    __tablename__ = 'email_quote_requests'
    id = Column(Integer, primary_key=True)
    quote_id = Column(String(36), ForeignKey('quotes.quote_id'), nullable=False)
    shipper_name = Column(String)
    shipper_address = Column(String)
    shipper_contact = Column(String)
    shipper_phone = Column(String)
    consignee_name = Column(String)
    consignee_address = Column(String)
    consignee_contact = Column(String)
    consignee_phone = Column(String)
    total_weight = Column(Float)
    special_instructions = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(engine)
