import os
import json
from backend.models import db, Appointment, User, Doctor
from backend.db_service import DBService
from app import create_app
from bson import ObjectId

def inspect_monitoring_state():
    app = create_app()
    with app.app_context():
        print("=== DOCTORS (SQL Table) ===")
        all_docs = Doctor.query.all()
        for d in all_docs:
            print(f"ID: {d.id}, Name: {d.name}, HospitalID: {d.hospital_id}")

        print("\n=== USER (Doctor Search) ===")
        # Finding महेश or Mahesh
        all_users = User.query.all()
        mahesh = None
        for u in all_users:
            if "Mahesh" in u.name or "महेश" in u.name:
                mahesh = u
                break
        
        if not mahesh:
            print("Mahesh not found in SQL, checking Mongo...")
            mongodb = DBService.get_mongo_db()
            if mongodb is not None:
                mahesh = mongodb.users.find_one({"name": {"$regex": "Mahesh|महेश", "$options": "i"}})
        
        if mahesh:
            m_id = mahesh.get('id') if isinstance(mahesh, dict) else mahesh.id
            m_name = mahesh.get('name') if isinstance(mahesh, dict) else mahesh.name
            m_hospitals = []
            if isinstance(mahesh, dict):
                m_hospitals = mahesh.get('profile', {}).get('hospitals') or mahesh.get('hospitals') or []
            else:
                try:
                    m_hospitals = json.loads(mahesh.hospitals) if mahesh.hospitals else []
                except:
                    m_hospitals = []
            print(f"Doctor Name: {m_name}, ID: {m_id}, Hospitals: {m_hospitals}")
        else:
            print("Doctor not found in either DB.")

        print("\n=== ADMITTED APPOINTMENTS ===")
        admitted = Appointment.query.filter_by(isAdmitted=True).all()
        for a in admitted:
            print(f"Appt ID: {a.id}, PatientID: {a.patient_id}, DocID: {a.doctor_id}, HospitalName: '{a.hospital_name}'")

if __name__ == "__main__":
    inspect_monitoring_state()
