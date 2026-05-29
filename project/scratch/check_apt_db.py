import sys
import os

# Ensure repo root is on sys.path
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from backend.models import db, Appointment
from app import create_app

def check():
    app = create_app()
    with app.app_context():
        apt = Appointment.query.get(5)
        if apt:
            print("--- APPOINTMENT 5 DETAILS ---")
            print(f"Name: {apt.name}")
            print(f"Email: {apt.email}")
            print(f"Mode: {apt.mode}")
            print(f"Status: {apt.status}")
            print(f"Meeting Link: {apt.meeting_link}")
            print(f"Meeting ID: {apt.meeting_id}")
            print(f"Meeting Password: {apt.meeting_password}")
        else:
            print("Appointment 5 not found!")

if __name__ == "__main__":
    check()
