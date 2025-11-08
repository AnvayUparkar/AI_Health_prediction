# Modified by Cursor integration: 2025-11-07 — added SQLAlchemy setup and User model
# Detected: original project had a single-file Flask app that loaded joblib models.
# Added: SQLAlchemy instance, User model with password helpers, optional Doctor/Appointment, and init_db().

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

db = SQLAlchemy()

class User(db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "email": self.email}

class Doctor(db.Model):
    """Optional minimal Doctor model"""
    __tablename__ = 'doctors'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    speciality = db.Column(db.String(120), nullable=True)

class Appointment(db.Model):
    """Optional minimal Appointment model"""
    __tablename__ = 'appointments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=True)
    date = db.Column(db.String(60), nullable=True)
    notes = db.Column(db.Text, nullable=True)

def init_db(app):
    """
    Initialize the database and create tables if they don't exist.
    The backend app will call this at startup.
    """
    with app.app_context():
        db.create_all()