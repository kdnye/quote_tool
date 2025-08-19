# app/models.py
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, index=True, nullable=False)
    name = db.Column(db.String(120))
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

class Quote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quote_type = db.Column(db.String(20), nullable=False)  # "Hotshot" or "Air"
    origin_zip = db.Column(db.String(10), nullable=False)
    dest_zip = db.Column(db.String(10), nullable=False)
    weight_actual = db.Column(db.Float, default=0.0)
    weight_dim = db.Column(db.Float, default=0.0)
    accessorials = db.Column(db.Text)  # JSON-serialized string
    price = db.Column(db.Float, default=0.0)
    warnings = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_by = db.relationship("User", backref="quotes")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
