import sys
import os
sys.path.append(os.getcwd())
from app import create_app
from backend.models import Appointment

app = create_app()
with app.app_context():
    apt = Appointment.query.order_by(Appointment.id.desc()).first()
    if apt:
        print(f"ID: {apt.id}")
        # print(f"Name: {apt.name}") # Appointment model has no name
        print(f"Status: {apt.status}")
        print(f"Meeting Link: {apt.meeting_link}")
        print(f"User ID: {apt.user_id}")
        print(f"Mode: {apt.mode}")
    else:
        print("No appointments found")
