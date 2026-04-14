# Modified by Cursor integration: 2025-11-07 — added SQLAlchemy setup and User model
# Detected: original project had a single-file Flask app that loaded joblib models.
# Added: SQLAlchemy instance, User model with password helpers, optional Doctor/Appointment, and init_db().

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='user')
    points = db.Column(db.Integer, default=0)
    lastStepReward = db.Column(db.Integer, default=0)
    streak = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Google OAuth fields
    google_token_json = db.Column(db.Text, nullable=True) # Stores the full creds JSON
    google_last_auth_at = db.Column(db.DateTime, nullable=True)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id, 
            "name": self.name, 
            "email": self.email,
            "role": self.role or "user",
            "points": self.points or 0,
            "streak": self.streak or 0
        }

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

class ShopItem(db.Model):
    """Items available for purchase with points"""
    __tablename__ = 'shop_items'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(256))
    points_cost = db.Column(db.Integer, nullable=False)
    image_url = db.Column(db.String(512))
    category = db.Column(db.String(50), default='wellness')

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "pointsCost": self.points_cost,
            "imageUrl": self.image_url,
            "category": self.category
        }

class HealthAnalysis(db.Model):
    """Stores AI-powered health analysis results for a user"""
    __tablename__ = 'health_analyses'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    health_score = db.Column(db.Integer)
    risk_level = db.Column(db.String(50))
    health_status = db.Column(db.String(100))
    # Original metrics for trend reporting
    steps = db.Column(db.Integer, nullable=True)
    avg_heart_rate = db.Column(db.Float, nullable=True)
    sleep_hours = db.Column(db.Float, nullable=True)
    diet_plan = db.Column(db.Text)  # Stored as JSON string
    recommendations = db.Column(db.Text)  # Stored as JSON string
    data_source = db.Column(db.String(30), default='google_fit')  # google_fit | health_connect | manual
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        try:
            diet = json.loads(self.diet_plan) if self.diet_plan else []
        except:
            diet = []
        try:
            recs = json.loads(self.recommendations) if self.recommendations else []
        except:
            recs = []
            
        return {
            "id": self.id,
            "health_score": self.health_score,
            "risk_level": self.risk_level,
            "health_status": self.health_status,
            "metrics": {
                "steps": self.steps,
                "avg_heart_rate": self.avg_heart_rate,
                "sleep_hours": self.sleep_hours
            },
            "diet_plan": diet,
            "recommendations": recs,
            "data_source": self.data_source or "google_fit",
            "created_at": self.created_at.isoformat()
        }

class Alert(db.Model):
    """Alert model for patient monitoring system"""
    __tablename__ = 'alerts'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.String(50), nullable=False, index=True)
    room_number = db.Column(db.String(20), nullable=True)
    status = db.Column(db.String(20), nullable=False) # SAFE | WARNING | CRITICAL
    confidence = db.Column(db.String(20), nullable=False) # LOW | MEDIUM | HIGH
    reason = db.Column(db.Text, nullable=True)
    detected_issues = db.Column(db.Text, nullable=True) # JSON string
    recommended_action = db.Column(db.Text, nullable=True)
    alert = db.Column(db.Boolean, default=False)
    acknowledged = db.Column(db.Boolean, default=False)
    resolved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        try:
            issues = json.loads(self.detected_issues) if self.detected_issues else []
        except:
            issues = []
            
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "room_number": self.room_number,
            "status": self.status,
            "confidence": self.confidence,
            "reason": self.reason,
            "detected_issues": issues,
            "recommended_action": self.recommended_action,
            "alert": self.alert,
            "acknowledged": self.acknowledged,
            "resolved": self.resolved,
            "created_at": self.created_at.isoformat()
        }

def init_db(app):
    """
    Initialize the database and create tables if they don't exist.
    The backend app will call this at startup.
    """
    with app.app_context():
        db.create_all()