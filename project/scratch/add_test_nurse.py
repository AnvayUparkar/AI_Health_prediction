# add_test_nurse.py
from app import create_app
from backend.db_service import DBService
from backend.models import db, User
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    name = "Nurse Joy"
    email = "nurse.joy@example.com"
    hospital = "Avdhoot Hospital"
    
    existing = DBService.get_user_by_email(email)
    if not existing:
        # Note: roles are usually lowercase like 'doctor', 'nurse'
        nurse = User(
            name=name,
            email=email,
            password_hash=generate_password_hash("password123"),
            role="nurse",
            hospitals='["' + hospital + '"]'
        )
        db.session.add(nurse)
        db.session.commit()
        print(f"✅ Success: Created {name} (Nurse) at {hospital}")
        print(f"🔑 Login with: {email} / password123")
    else:
        print(f"ℹ️ User {email} already exists.")
