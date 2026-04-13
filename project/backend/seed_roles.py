import os
import sys
from datetime import datetime

# Ensure the project root is in sys.path
# If this script is in project/backend/seed_roles.py, then project root is ..
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app import create_app
from backend.models import db, User
from backend.db_service import DBService

app = create_app()

def seed_roles():
    with app.app_context():
        print("--- Starting Role Seeding ---")
        
        # 1. Mahesh Bhaskar Uparkar -> doctor
        mahesh = User.query.filter_by(email="maheshbu@gmail.com").first()
        if mahesh:
            print(f"Updating {mahesh.name} (ID: {mahesh.id}) to doctor...")
            mahesh.role = "doctor"
            db.session.commit()
            
            # Sync to Mongo
            if os.environ.get('DB_MODE') in ['hybrid', 'mongo']:
                mongodb = DBService.get_mongo_db()
                if mongodb is not None:
                    mongodb.users.update_one(
                        {"email": mahesh.email.lower()},
                        {"$set": {"role": "doctor"}}
                    )
            print(f"[OK] {mahesh.name} updated to doctor")
        else:
            print("[WARN] maheshbu@gmail.com not found in database")

        # 2. Anvay Mahesh Uparkar -> user
        anvay = User.query.filter_by(email="anvaymuparkar@gmail.com").first()
        if anvay:
            print(f"Updating {anvay.name} (ID: {anvay.id}) to user...")
            anvay.role = "user"
            db.session.commit()
            
            # Sync to Mongo
            if os.environ.get('DB_MODE') in ['hybrid', 'mongo']:
                mongodb = DBService.get_mongo_db()
                if mongodb is not None:
                    mongodb.users.update_one(
                        {"email": anvay.email.lower()},
                        {"$set": {"role": "user"}}
                    )
            print(f"[OK] {anvay.name} updated to user")
        else:
            print("[WARN] anvaymuparkar@gmail.com not found in database")

        # 3. Default all others to 'user'
        others = User.query.filter((User.role.is_(None)) | (User.role == '')).all()
        if others:
            print(f"Defaulting {len(others)} other users to 'user'...")
            for u in others:
                u.role = "user"
            db.session.commit()
            
            # Sync to Mongo
            if os.environ.get('DB_MODE') in ['hybrid', 'mongo']:
                mongodb = DBService.get_mongo_db()
                if mongodb is not None:
                    mongodb.users.update_many(
                        {"role": {"$exists": False}},
                        {"$set": {"role": "user"}}
                    )
            print(f"[OK] {len(others)} users defaulted to 'user'")

        print("--- Role Seeding Complete ---")

if __name__ == "__main__":
    seed_roles()
