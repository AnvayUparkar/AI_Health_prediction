
from app import app
from backend.models import db, HealthAnalysis, User
import json

with app.app_context():
    print("--- Health Analysis Records ---")
    analyses = HealthAnalysis.query.all()
    for a in analyses:
        print(f"ID: {a.id} | User: {a.user_id} | Date: {a.created_at} | Steps: {a.steps}")
    print("--- End ---")
