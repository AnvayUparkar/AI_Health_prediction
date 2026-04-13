import os
import sys
import json
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

# Ensure repo root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.models import db
from flask import Flask
from sqlalchemy import text

def migrate_data():
    # Load .env
    load_dotenv()
    
    mongo_uri = os.environ.get('MONGODB_URI')
    if not mongo_uri:
        print("[ERROR] MONGODB_URI not found in environment")
        return

    # Initialize Flask app to access SQLAlchemy models
    app = Flask(__name__)
    # Repo root is one level up from backend/
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    db_path = os.path.join(repo_root, 'app.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    # Initialize Mongo
    try:
        mongo_client = MongoClient(mongo_uri)
        db_name = mongo_uri.split('/')[-1].split('?')[0] or 'health_db'
        mongodb = mongo_client[db_name]
        print(f"[OK] Connected to MongoDB: {db_name}")
    except Exception as e:
        print(f"[ERROR] Mongo connection failed: {e}")
        return

    with app.app_context():
        print("\n--- Starting Migration ---\n")

        # 1. Migrate Users
        print("Fetching users from SQLite...")
        user_rows = db.session.execute(text("SELECT * FROM users")).mappings().all()
        print(f"Migrating {len(user_rows)} users...")
        for u in user_rows:
            mongodb.users.update_one(
                {"email": u["email"]},
                {"$set": {
                    "sql_id": u["id"],
                    "name": u["name"],
                    "email": u["email"],
                    "password_hash": u["password_hash"],
                    "created_at": u.get("created_at") or datetime.utcnow()
                }},
                upsert=True
            )
        print("[OK] Users migrated")

        # 2. Migrate Health Analyses
        print("Fetching health analysis records from SQLite...")
        analysis_rows = db.session.execute(text("SELECT * FROM health_analyses")).mappings().all()
        print(f"Migrating {len(analysis_rows)} health analysis records...")
        for a in analysis_rows:
            # Try to parse diet/recs JSON strings
            try:
                diet = json.loads(a["diet_plan"]) if a["diet_plan"] else []
            except:
                diet = []
            try:
                recs = json.loads(a["recommendations"]) if a["recommendations"] else []
            except:
                recs = []
        
            mongodb.health_analyses.update_one(
                {"sql_id": a["id"]},
                {"$set": {
                    "user_id": str(a["user_id"]),
                    "health_score": a["health_score"],
                    "risk_level": a["risk_level"],
                    "health_status": a["health_status"],
                    "metrics": {
                        "steps": a["steps"],
                        "avg_heart_rate": a["avg_heart_rate"],
                        "sleep_hours": a["sleep_hours"]
                    },
                    "diet_plan": diet,
                    "recommendations": recs,
                    "data_source": a.get("data_source"),
                    "created_at": a.get("created_at") or datetime.utcnow()
                }},
                upsert=True
            )
        print("[OK] Health Analyses migrated")

        # 3. Migrate Appointments
        print("Fetching appointments from SQLite...")
        apt_rows = db.session.execute(text("SELECT * FROM appointments")).mappings().all()
        print(f"Migrating {len(apt_rows)} appointments...")
        for apt in apt_rows:
            mongodb.appointments.update_one(
                {"sql_id": apt["id"]},
                {"$set": {
                    "user_id": str(apt["user_id"]) if apt["user_id"] else None,
                    "doctor_id": apt.get("doctor_id"),
                    "name": apt.get("name"),
                    "email": apt.get("email"),
                    "phone": apt.get("phone"),
                    "mode": apt.get("mode"),
                    "appointment_date": str(apt.get("date")) if apt.get("date") else None,
                    "appointment_time": apt.get("appointment_time"),
                    "reason": apt.get("reason"),
                    "status": apt.get("status"),
                    "notes": apt.get("notes"),
                    "created_at": apt.get("created_at") or datetime.utcnow()
                }},
                upsert=True
            )
        print("[OK] Appointments migrated")

        print("\n--- Migration Complete ---\n")

if __name__ == "__main__":
    migrate_data()
