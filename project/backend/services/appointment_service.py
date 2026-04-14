import json
from datetime import datetime
import os
from backend.models import db, Appointment, User
from backend.db_service import DBService
from bson import ObjectId

class AppointmentService:
    @staticmethod
    def get_doctor_appointments(doctor_id, status_filter=None):
        mode = os.environ.get('READ_FROM', 'sql')
        
        # If Hybrid/Mongo
        if mode == 'mongo':
            mongodb = DBService.get_mongo_db()
            if mongodb is not None:
                query = {"doctor_id": doctor_id}
                if status_filter:
                    query['status'] = status_filter
                    
                cursor = mongodb.appointments.find(query).sort("created_at", -1)
                results = list(cursor)
                
                # Fetch patient info manually or trust Mongo has it
                for r in results:
                    r['id'] = str(r.pop('_id'))
                    if 'suggested_dates' in r and isinstance(r['suggested_dates'], str):
                        try: r['suggested_dates'] = json.loads(r['suggested_dates'])
                        except: pass
                    if 'suggested_times' in r and isinstance(r['suggested_times'], str):
                        try: r['suggested_times'] = json.loads(r['suggested_times'])
                        except: pass
                return results

        # SQL
        query = db.session.query(Appointment, User).join(User, Appointment.patient_id == User.id, isouter=True)
        query = query.filter(Appointment.doctor_id == doctor_id)
        if status_filter:
            query = query.filter(Appointment.status == status_filter)
            
        records = query.order_by(Appointment.created_at.desc()).all()
        results = []
        for appt, user in records:
            sd = []
            st = []
            try: sd = json.loads(appt.suggested_dates) if appt.suggested_dates else []
            except: pass
            try: st = json.loads(appt.suggested_times) if appt.suggested_times else []
            except: pass
            
            # fallback to legacy date/time fields if new ones are empty
            req_date = appt.requested_date
            if not req_date and hasattr(appt, 'appointment_date'):
                req_date = str(appt.appointment_date) # legacy backwards compatibility
                
            req_time = appt.requested_time
            if not req_time and hasattr(appt, 'appointment_time'):
                req_time = str(appt.appointment_time)

            results.append({
                "id": appt.id,
                "patient_id": appt.patient_id,
                "patient_name": user.name if user else "Unknown Patient",
                "doctor_id": appt.doctor_id,
                "status": appt.status,
                "requested_date": req_date,
                "requested_time": req_time,
                "suggested_dates": sd,
                "suggested_times": st,
                "isChecked": appt.isChecked,
                "isAdmitted": appt.isAdmitted,
                "created_at": appt.created_at.isoformat() if appt.created_at else None,
                "updated_at": appt.updated_at.isoformat() if appt.updated_at else None
            })
        return results

    @staticmethod
    def approve_appointment(appointment_id):
        return AppointmentService._update_status(appointment_id, "APPROVED")

    @staticmethod
    def reject_appointment(appointment_id, suggested_dates, suggested_times):
        if not suggested_dates or len(suggested_dates) != 3:
            raise ValueError("Exactly 3 suggested dates are required.")
        
        # Simple future date validation
        for d in suggested_dates:
            d_obj = datetime.strptime(d, "%Y-%m-%d")
            if d_obj.date() < datetime.now().date():
                raise ValueError("Suggested dates must be in the future.")
                
        update_data = {
            "status": "REJECTED",
            "suggested_dates": json.dumps(suggested_dates),
            "suggested_times": json.dumps(suggested_times or [])
        }
        return AppointmentService._update_record(appointment_id, update_data)

    @staticmethod
    def update_appointment_clinical_status(appointment_id, is_checked=None, is_admitted=None):
        update_data = {}
        if is_checked is not None:
            update_data["isChecked"] = is_checked
        if is_admitted is not None:
            update_data["isAdmitted"] = is_admitted
            
        return AppointmentService._update_record(appointment_id, update_data)

    @staticmethod
    def _update_status(appointment_id, status):
        return AppointmentService._update_record(appointment_id, {"status": status})

    @staticmethod
    def _update_record(appointment_id, update_data):
        # 1. SQL
        appt = None
        sql_id = None
        mongo_id = None
        try:
            sql_id = int(appointment_id)
            appt = Appointment.query.get(sql_id)
        except (ValueError, TypeError):
            if isinstance(appointment_id, str) and len(appointment_id) == 24:
                mongo_id = appointment_id
                mongodb = DBService.get_mongo_db()
                if mongodb is not None:
                    data = mongodb.appointments.find_one({"_id": ObjectId(appointment_id)})
                    if data and 'sql_id' in data:
                        sql_id = data['sql_id']
                        appt = Appointment.query.get(sql_id)

        if appt:
            for k, v in update_data.items():
                setattr(appt, k, v)
            appt.updated_at = datetime.utcnow()
            db.session.commit()
            
        # 2. Mongo
        if os.environ.get('DB_MODE') in ['hybrid', 'mongo']:
            try:
                oid = ObjectId(mongo_id) if mongo_id else None
                if not oid and isinstance(appointment_id, str) and len(appointment_id) == 24:
                    oid = ObjectId(appointment_id)
                
                filter_query = {"_id": oid} if oid else {"sql_id": sql_id}
                DBService._async_mongo_write('appointments', 'update', {**update_data, "updated_at": datetime.utcnow()}, filter_query)
            except Exception as e:
                print(f"Mongo async error in appointment_service: {e}")
                
        if appt:
            return {"id": appt.id, "status": appt.status}
        return {"id": appointment_id, **update_data}
