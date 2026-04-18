import os
import json
from backend.models import db, Appointment, User, Doctor
from backend.db_service import DBService
from app import create_app
from bson import ObjectId

def fix_mahesh_data():
    app = create_app()
    with app.app_context():
        target_hospital = "Avadhoot Hospital and Iccu"
        
        print(f"--- Synchronizing to: {target_hospital} ---")

        # 1. Update Mahesh's User Record (SQL + Mongo)
        all_users = User.query.all()
        mahesh_sql = None
        for u in all_users:
            if "Mahesh" in u.name or "महेश" in u.name:
                mahesh_sql = u
                break
        
        mahesh_id = None
        if mahesh_sql:
            print(f"Updating Mahesh SQL Profile (ID: {mahesh_sql.id})")
            mahesh_sql.hospitals = json.dumps([target_hospital])
            db.session.commit()
            mahesh_id = mahesh_sql.id
        
        # Sync to Mongo
        mongodb = DBService.get_mongo_db()
        if mongodb is not None:
            res = mongodb.users.update_many(
                {"name": {"$regex": "Mahesh|महेश", "$options": "i"}},
                {"$set": {"profile.hospitals": [target_hospital], "hospitals": [target_hospital]}}
            )
            print(f"Updated {res.modified_count} Mahesh records in MongoDB.")

        # 2. Update Admitted Appointments
        admitted = Appointment.query.filter_by(isAdmitted=True).all()
        for a in admitted:
            print(f"Updating Appt {a.id} hospital to '{target_hospital}'")
            a.hospital_name = target_hospital
            # Also ensure the doctor_id matches Mahesh's SQL ID if it was a mongo ID mismatch
            # (Only if it's currently null or points to a non-existent doctor)
            if mahesh_id and (not a.doctor_id or str(a.doctor_id).startswith('69')):
                 a.doctor_id = mahesh_id
            
        db.session.commit()
        print(f"Updated {len(admitted)} admitted appointments.")

        # 3. Update Doctor SQL Table
        doc = Doctor.query.filter(Doctor.name.like('%Mahesh%')).first()
        if doc:
            print(f"Updating Doctor Table Entry (ID: {doc.id})")
            doc.hospital_id = target_hospital
            db.session.commit()
        else:
            # Create if missing
            if mahesh_sql:
                new_doc = Doctor(id=mahesh_sql.id, name=mahesh_sql.name, hospital_id=target_hospital)
                db.session.add(new_doc)
                db.session.commit()
                print(f"Created new Doctor table entry for {mahesh_sql.name}")

        print("\n[SUCCESS] Data synchronization complete.")

if __name__ == "__main__":
    fix_mahesh_data()
