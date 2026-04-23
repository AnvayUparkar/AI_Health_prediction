import sys
import os
from dotenv import load_dotenv
load_dotenv()
sys.path.append(os.getcwd())
from app import create_app
from backend.db_service import DBService
from backend.services.email_service import EmailService

app = create_app()
with app.app_context():
    # Find the latest pending appointment
    apt = DBService.list_appointments(filters={"status": "pending"})
    if not apt:
        print("No pending appointments found")
        # Try finding ANY appointment
        apt = DBService.list_appointments({})
    
    if apt:
        target = apt[0]
        apt_id = target['id'] if isinstance(target, dict) else target.id
        print(f"Testing approval for Appointment ID: {apt_id}")
        
        # Manually trigger the status update logic (or just simulation)
        status = "confirmed"
        
        # Simulation of the route logic
        full_apt = DBService.get_appointment(apt_id)
        if full_apt:
            print(f"Appointment Data: {full_apt}")
            patient_email = full_apt.get('email')
            meeting_link = full_apt.get('meeting_link')
            patient_name = full_apt.get('name', 'Patient')
            apt_time = f"{full_apt.get('appointment_date')} at {full_apt.get('appointment_time')}"
            mode = full_apt.get('mode', 'online')
            doctor_id = full_apt.get('doctor_id')
            
            print(f"Patient Email: {patient_email}")
            print(f"Doctor ID: {doctor_id}")
            
            if patient_email and mode == 'online' and meeting_link:
                EmailService.send_appointment_email(patient_email, meeting_link)
            else:
                print("Skipping patient email (missing link/email or not online)")
                
            if doctor_id:
                doctor_email = DBService.get_doctor_email(doctor_id)
                print(f"Doctor Email: {doctor_email}")
                if doctor_email:
                    EmailService.send_doctor_notification(
                        doctor_email, 
                        patient_name, 
                        apt_time, 
                        mode, 
                        meeting_link if mode == 'online' else None
                    )
                else:
                    print("Could not find doctor email")
    else:
        print("No appointments found at all")
