import sqlite3
import os
from backend.models import db, Appointment, Doctor
from app import app

def check_db():
    with app.app_context():
        print("--- Admitted Appointments ---")
        appts = Appointment.query.filter_by(isAdmitted=True).all()
        for a in appts:
            print(f"ID: {a.id}, DocID: {a.doctor_id}, Hospital: '{a.hospital_name}'")
        
        print("\n--- Doctors ---")
        docs = Doctor.query.all()
        for d in docs:
            print(f"ID: {d.id}, Name: {d.name}, HospitalID: '{d.hospital_id}'")

if __name__ == "__main__":
    check_db()
