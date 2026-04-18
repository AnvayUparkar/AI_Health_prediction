import json
from datetime import datetime
import os
import math
from backend.models import db, Appointment, User, AuditLog, Hospital
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
                    
                    # Fetch patient info from users collection manually
                    patient_id = r.get('patient_id')
                    if patient_id:
                        try:
                            # Might be stored as ObjectId string or regular string
                            user_doc = mongodb.users.find_one({"_id": ObjectId(patient_id)})
                        except Exception:
                            user_doc = mongodb.users.find_one({"_id": patient_id})
                            
                        if user_doc:
                            r['patient_name'] = user_doc.get('name', 'Unknown')
                            r['patient_email'] = user_doc.get('email')
                            
                    # Map legacy fields to current fields
                    r['requested_date'] = r.get('requested_date') or r.get('appointment_date')
                    r['requested_time'] = r.get('requested_time') or r.get('appointment_time')

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
                "patient_email": user.email if user else None,
                "patient_age": user.age if user else None,
                "patient_sex": user.sex if user else None,
                "patient_weight": user.weight if user else None,
                "patient_height": user.height if user else None,
                "doctor_id": appt.doctor_id,
                "status": appt.status,
                "reason": appt.reason if hasattr(appt, 'reason') else None,
                "requested_time": req_time,
                "suggested_dates": sd,
                "suggested_times": st,
                "isChecked": appt.isChecked,
                "isAdmitted": appt.isAdmitted,
                "ward_number": appt.ward_number,
                "hospital_name": appt.hospital_name,
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
            # If admitted, record which hospital they are in
            if is_admitted:
                appt_record = AppointmentService.get_appointment(appointment_id)
                if appt_record:
                    # Handle both object and dict
                    doc_id = appt_record.doctor_id if hasattr(appt_record, 'doctor_id') else appt_record.get('doctor_id')
                    if doc_id:
                        from backend.models import Doctor, User
                        # 1. Try SQL Doctor lookup
                        doc = Doctor.query.get(doc_id)
                        if doc and doc.hospital_id:
                            update_data["hospital_name"] = doc.hospital_id
                        else:
                            # 2. Try User profile lookup (Mahesh might be a User with role='doctor')
                            staff = DBService.get_user_by_id(doc_id)
                            if staff:
                                staff_hospitals = []
                                if isinstance(staff, dict):
                                    staff_hospitals = staff.get('profile', {}).get('hospitals') or staff.get('hospitals') or []
                                else:
                                    staff_hospitals = staff.to_dict().get('profile', {}).get('hospitals', [])
                                
                                if staff_hospitals:
                                    # Fallback to the first associated hospital
                                    update_data["hospital_name"] = staff_hospitals[0]

            # If discharged, reset ward
            if is_admitted is False:
                update_data["ward_number"] = None
                update_data["ward_assigned_at"] = None
                update_data["hospital_name"] = None
            
        return AppointmentService._update_record(appointment_id, update_data)

    @staticmethod
    def get_appointment(appointment_id):
        try:
            sql_id = int(appointment_id)
            appt = Appointment.query.get(sql_id)
            if appt:
                return appt
        except (ValueError, TypeError):
            pass
            
        if isinstance(appointment_id, str) and len(appointment_id) == 24:
            mongodb = DBService.get_mongo_db()
            if mongodb is not None:
                return mongodb.appointments.find_one({"_id": ObjectId(appointment_id)})
        return None

    @staticmethod
    def assign_ward(appointment_id, ward_number):
        # 1. Fetch record first for validation
        appt = AppointmentService.get_appointment(appointment_id)
        
        if not appt:
            raise ValueError("Appointment not found")
        
        # Check current state (handles both SQL objects and dicts from Mongo)
        is_checked = appt.isChecked if hasattr(appt, 'isChecked') else appt.get('isChecked')
        is_admitted = appt.isAdmitted if hasattr(appt, 'isAdmitted') else appt.get('isAdmitted')
        
        if not is_checked or not is_admitted:
            raise ValueError("Ward can only be assigned to Verified and Admitted patients.")
            
        update_data = {
            "ward_number": ward_number,
            "ward_assigned_at": datetime.utcnow()
        }
        
        result = AppointmentService._update_record(appointment_id, update_data)
        
        # 2. Log Action
        patient_id = appt.patient_id if hasattr(appt, 'patient_id') else appt.get('patient_id')
        doctor_id = appt.doctor_id if hasattr(appt, 'doctor_id') else appt.get('doctor_id')
        
        AppointmentService.log_audit_action(
            action="WARD_ASSIGNED",
            appointment_id=appointment_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            ward_number=ward_number,
            details={"timestamp": datetime.utcnow().isoformat()}
        )
        
        return result

    @staticmethod
    def get_patient_ward_info(patient_id):
        # Check Mongo First if we are in hybrid/mongo mode
        mode = os.environ.get('READ_FROM', 'sql')
        if mode == 'mongo':
            mongodb = DBService.get_mongo_db()
            if mongodb is not None:
                doc = mongodb.appointments.find_one({"patient_id": str(patient_id), "isAdmitted": True})
                if not doc:
                    user_doc = mongodb.users.find_one({"name": patient_id})
                    if user_doc:
                        doc = mongodb.appointments.find_one({"patient_id": str(user_doc["_id"]), "isAdmitted": True})
                if doc:
                    return {
                        "patient_id": patient_id,
                        "ward_number": doc.get('ward_number'),
                        "doctor_id": doc.get('doctor_id'),
                        "status": "ADMITTED" if doc.get('isAdmitted') else "CHECKED"
                    }
        
        # Fallback to SQL
        appt = Appointment.query.filter_by(patient_id=str(patient_id), isAdmitted=True).first()
        if not appt:
            user = User.query.filter_by(name=patient_id).first()
            if user:
                appt = Appointment.query.filter_by(patient_id=str(user.id), isAdmitted=True).first()
                
        if appt:
            return {
                "patient_id": patient_id,
                "ward_number": appt.ward_number,
                "doctor_id": appt.doctor_id,
                "status": "ADMITTED" if appt.isAdmitted else "CHECKED"
            }
        return None

    @staticmethod
    def calculate_nearest_hospital(lat, lon):
        def haversine(lat1, lon1, lat2, lon2):
            R = 6371 # Earth radius in km
            dLat = math.radians(lat2 - lat1)
            dLon = math.radians(lon2 - lon1)
            a = math.sin(dLat/2) * math.sin(dLat/2) + \
                math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
                math.sin(dLon/2) * math.sin(dLon/2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            return R * c

        # Query all hospitals
        mode = os.environ.get('READ_FROM', 'sql')
        hospitals = []
        if mode == 'mongo':
            mongodb = DBService.get_mongo_db()
            if mongodb is not None:
                hospitals = list(mongodb.hospitals.find())
                if not hospitals:
                    # Fallback to SQL if mongo collection doesn't exist yet/not synced
                    hospitals = [h.to_dict() for h in Hospital.query.all()]
        else:
            hospitals = [h.to_dict() for h in Hospital.query.all()]
            
        if not hospitals:
            return None

        print(f"\n[SOS ROUTING] Calculating nearest hospital to [Lat: {lat}, Lon: {lon}]...")
        
        # Calculate distances
        evaluated_hospitals = []
        for h in hospitals:
            h_lat = h.get('latitude', h.get('lat'))
            h_lon = h.get('longitude', h.get('lon'))
            if h_lat is None or h_lon is None: continue
                
            dist = haversine(lat, lon, h_lat, h_lon)
            h['distance'] = dist
            evaluated_hospitals.append(h)
            
        # Sort by distance
        evaluated_hospitals.sort(key=lambda x: x['distance'])
        
        # Print top 4
        print("[SOS ROUTING] Top 4 Nearest Results:")
        for h in evaluated_hospitals[:4]:
            print(f"  -> Evaluated '{h.get('name')}': {h['distance']:.2f} km away")
        
        if evaluated_hospitals:
            nearest = evaluated_hospitals[0]
            print(f"[SOS ROUTING] Selected NEAREST: {nearest.get('name')} at {nearest['distance']:.2f} km\n")
            return {
                "_id": nearest.get('id') or str(nearest.get('_id', '')),
                "name": nearest.get('name'),
                "distance": round(nearest['distance'], 2),
                "lat": nearest.get('latitude', nearest.get('lat')),
                "lon": nearest.get('longitude', nearest.get('lon')),
                "capacity": nearest.get('capacity', 0)
            }
        return None

    @staticmethod
    def log_audit_action(action, appointment_id=None, patient_id=None, doctor_id=None, ward_number=None, details=None):
        try:
            log = AuditLog(
                action=action,
                appointment_id=int(appointment_id) if appointment_id and str(appointment_id).isdigit() else None,
                patient_id=str(patient_id),
                doctor_id=doctor_id,
                ward_number=ward_number,
                details=json.dumps(details or {})
            )
            db.session.add(log)
            db.session.commit()
            return True
        except Exception as e:
            print(f"Error logging audit action: {e}")
            return False

    @staticmethod
    def delete_appointment(appointment_id):
        # Hard Delete implementation
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

        # 1. SQL Delete
        if appt:
            db.session.delete(appt)
            db.session.commit()

        # 2. Mongo Delete
        if os.environ.get('DB_MODE') in ['hybrid', 'mongo']:
            try:
                oid = ObjectId(mongo_id) if mongo_id else None
                if not oid and isinstance(appointment_id, str) and len(appointment_id) == 24:
                    oid = ObjectId(appointment_id)
                
                filter_query = {"_id": oid} if oid else {"sql_id": sql_id}
                DBService._async_mongo_write('appointments', 'delete', {}, filter_query)
            except Exception as e:
                print(f"Mongo async error on hard delete: {e}")

        return {"success": True, "id": appointment_id}

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
