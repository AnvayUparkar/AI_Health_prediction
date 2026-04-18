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
    
    # Verification system for doctors
    isApproved = db.Column(db.Boolean, default=False)
    certificate_url = db.Column(db.String(512), nullable=True)
    certificate_type = db.Column(db.String(20), nullable=True) # "image" or "pdf"
    verification_attempts = db.Column(db.Integer, default=0)
    rejection_reason = db.Column(db.Text, nullable=True)
    
    # Profile fields
    age = db.Column(db.Integer, nullable=True)
    sex = db.Column(db.String(20), nullable=True)
    weight = db.Column(db.Float, nullable=True)
    height = db.Column(db.Float, nullable=True)
    hospitals = db.Column(db.Text, nullable=True) # JSON list of hospital names
    
    # Google OAuth fields
    google_token_json = db.Column(db.Text, nullable=True) # Stores the full creds JSON
    google_last_auth_at = db.Column(db.DateTime, nullable=True)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        try:
            hospitals_list = json.loads(self.hospitals) if self.hospitals else []
        except:
            hospitals_list = []
            
        return {
            "id": self.id, 
            "name": self.name, 
            "email": self.email,
            "role": self.role or "user",
            "points": self.points or 0,
            "streak": self.streak or 0,
            "isApproved": self.isApproved,
            "verification": {
                "certificate_url": self.certificate_url,
                "certificate_type": self.certificate_type,
                "attempts": self.verification_attempts,
                "rejection_reason": self.rejection_reason
            },
            "profile": {
                "age": self.age,
                "sex": self.sex,
                "weight": self.weight,
                "height": self.height,
                "hospitals": hospitals_list
            }
        }

class Doctor(db.Model):
    """Optional minimal Doctor model"""
    __tablename__ = 'doctors'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    speciality = db.Column(db.String(120), nullable=True)
    hospital_id = db.Column(db.String(120), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "hospital_id": self.hospital_id
        }

class Appointment(db.Model):
    """Optional minimal Appointment model (Extended for Doctor Management)"""
    __tablename__ = 'appointments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=True)
    date = db.Column(db.String(60), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    # New Extended Fields
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    status = db.Column(db.String(20), default="PENDING")
    requested_date = db.Column(db.String(20), nullable=True)
    requested_time = db.Column(db.String(20), nullable=True)
    suggested_dates = db.Column(db.Text, nullable=True) # JSON Array
    suggested_times = db.Column(db.Text, nullable=True) # JSON Array
    isChecked = db.Column(db.Boolean, default=False)
    isAdmitted = db.Column(db.Boolean, default=False)
    ward_number = db.Column(db.String(50), nullable=True)
    ward_assigned_at = db.Column(db.DateTime, nullable=True)
    hospital_name = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
    
    # New Geolocation/SOS fields
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    location_type = db.Column(db.String(20), default='WARD') # WARD | REMOTE
    nearest_hospital = db.Column(db.String(120), nullable=True)
    distance_km = db.Column(db.Float, nullable=True)
    notified_doctor_ids = db.Column(db.Text, nullable=True) # JSON list
    
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
            "latitude": self.latitude,
            "longitude": self.longitude,
            "location_type": self.location_type,
            "nearest_hospital": self.nearest_hospital,
            "distance_km": self.distance_km,
            "notified_doctors": json.loads(self.notified_doctor_ids) if self.notified_doctor_ids else [],
            "created_at": self.created_at.isoformat() + "Z"
        }

class AuditLog(db.Model):
    """Audit log for system actions"""
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(50), nullable=False) # WARD_ASSIGNED, SOS_TRIGGERED, etc.
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=True)
    patient_id = db.Column(db.String(50), nullable=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    ward_number = db.Column(db.String(50), nullable=True)
    details = db.Column(db.Text, nullable=True) # JSON details
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "action": self.action,
            "appointment_id": self.appointment_id,
            "patient_id": self.patient_id,
            "doctor_id": self.doctor_id,
            "ward_number": self.ward_number,
            "details": json.loads(self.details) if self.details else {},
            "timestamp": self.timestamp.isoformat()
        }

class Hospital(db.Model):
    """Hospital Registry for SOS tracking"""
    __tablename__ = 'hospitals'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    capacity = db.Column(db.Integer, default=100)
    emergency_available = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "capacity": self.capacity,
            "emergency_available": self.emergency_available
        }

class PatientMonitoring(db.Model):
    """Vitals & diet tracking for admitted patients (3x daily)"""
    __tablename__ = 'patient_monitoring'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.String(50), nullable=False, index=True)  # SQL int or Mongo ObjectId string
    date = db.Column(db.String(10), nullable=False)  # YYYY-MM-DD
    time_slot = db.Column(db.String(20), nullable=False)  # morning | afternoon | evening

    # Vitals
    glucose = db.Column(db.Float, nullable=True)
    bp_systolic = db.Column(db.Float, nullable=True)
    bp_diastolic = db.Column(db.Float, nullable=True)
    spo2 = db.Column(db.Float, nullable=True)

    # Diet compliance
    breakfast_done = db.Column(db.Boolean, default=False)
    lunch_done = db.Column(db.Boolean, default=False)
    snacks_done = db.Column(db.Boolean, default=False)
    dinner_done = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('ix_monitoring_patient_date', 'patient_id', 'date'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "date": self.date,
            "time_slot": self.time_slot,
            "glucose": self.glucose,
            "bp_systolic": self.bp_systolic,
            "bp_diastolic": self.bp_diastolic,
            "spo2": self.spo2,
            "breakfast_done": self.breakfast_done,
            "lunch_done": self.lunch_done,
            "snacks_done": self.snacks_done,
            "dinner_done": self.dinner_done,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

def init_db(app):
    """
    Initialize the database and create tables if they don't exist.
    The backend app will call this at startup.
    """
    with app.app_context():
        db.create_all()
        
        # Seed hospitals if table is empty
        if Hospital.query.count() == 0:
            from backend.utils.geocode import geocode_hospital

            seed_data = [
                ("Avdhoot Hospital", 19.1597689, 72.9925981, 200),
                ("Shatabdi Hospital", 19.0496, 72.9150, 500),
                ("City Medical Center", 18.5300, 73.8600, 150),
                ("General Wellness Clinic", 18.5100, 73.8400, 50),
            ]

            hospitals = []
            print("[INFO] Seeding hospitals with geocoded coordinates...")
            for name, fallback_lat, fallback_lon, capacity in seed_data:
                lat, lon = geocode_hospital(name, fallback_lat, fallback_lon)
                hospitals.append(Hospital(
                    name=name,
                    latitude=lat or fallback_lat,
                    longitude=lon or fallback_lon,
                    capacity=capacity,
                ))

            db.session.bulk_save_objects(hospitals)
            db.session.commit()
            print("[INFO] Seeded hospitals into SQL database.")

        # Seed doctors strictly assigned to hospitals
        if Doctor.query.count() == 0:
            # Note: We use OSM/mock IDs if the frontend passes them, or internal SQL hospital IDs.
            # To ensure it always works regardless of what ID the frontend passes, we will 
            # dynamically create doctors on the fly in the API if needed, 
            # but we seed some defaults here just in case.
            seed_doctors = [
                Doctor(name="Dr. Mahesh Bhaskar Uparkar", speciality="Cardiology", hospital_id="1"),
                Doctor(name="Dr. Rajesh Patil", speciality="Neurology", hospital_id="2"),
                Doctor(name="Dr. Sunita Sharma", speciality="Pediatrics", hospital_id="3")
            ]
            db.session.bulk_save_objects(seed_doctors)
            db.session.commit()
            print("[INFO] Seeded doctors into SQL database.")