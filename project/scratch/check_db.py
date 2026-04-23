import os
import sys
from datetime import datetime

# Ensure project root is in sys.path
sys.path.append(os.getcwd())

from app import create_app
from backend.models import db, MedicationLog, Medication, User

app = create_app()
with app.app_context():
    today = datetime.now().strftime('%Y-%m-%d')
    print(f"Checking for logs on {today}...")
    
    logs = db.session.query(MedicationLog, Medication, User).join(
        Medication, MedicationLog.medication_id == Medication.id
    ).join(
        User, Medication.patient_id == User.id
    ).filter(MedicationLog.date == today).all()
    
    if not logs:
        print("No logs found for today.")
    else:
        for log, med, user in logs:
            print(f"Log: {med.name} for {user.name} at {log.scheduled_time}, Status: {log.status}")

    now = datetime.now()
    current_time = now.strftime("%H:%M")
    print(f"Current server time: {current_time}")
