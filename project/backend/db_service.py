import os
import logging
import json
import threading
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pymongo import MongoClient
from bson import ObjectId
from backend.models import db, User, HealthAnalysis, Appointment, Doctor, ShopItem, Alert
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

class DBService:
    _mongo_client = None
    _mongo_db = None

    @staticmethod
    def get_mongo_obj_id(obj_id: Any):
        if not obj_id:
            return None
        try:
            return ObjectId(obj_id) if isinstance(obj_id, str) and len(obj_id) == 24 else None
        except:
            return None

    @classmethod
    def get_mongo_db(cls):
        if cls._mongo_db is None:
            uri = os.environ.get('MONGODB_URI')
            if not uri:
                logger.warning("MONGODB_URI not set in environment")
                return None
            try:
                # Use a short timeout for connection to avoid hanging
                cls._mongo_client = MongoClient(uri, serverSelectionTimeoutMS=2000)
                # Try to ping to confirm connection
                cls._mongo_client.admin.command('ping')
                
                # Extract DB name from URI or use default
                db_name = uri.split('/')[-1].split('?')[0] or 'health_db'
                cls._mongo_db = cls._mongo_client[db_name]
                logger.info(f"Connected to MongoDB: {db_name}")
            except Exception as e:
                logger.error(f"Failed to connect to MongoDB: {e}")
                return None
        return cls._mongo_db

    @classmethod
    def _async_mongo_write(cls, collection_name: str, operation: str, data: Dict[str, Any], filter_query: Optional[Dict] = None):
        """Internal method to perform MongoDB write in a background thread."""
        def run_write():
            try:
                mongodb = cls.get_mongo_db()
                if mongodb is None:
                    return

                collection = mongodb[collection_name]
                if operation == 'insert':
                    # Ensure no _id if it's a new insert from SQL
                    data.pop('_id', None)
                    collection.insert_one(data)
                elif operation == 'update':
                    collection.update_one(filter_query, {"$set": data}, upsert=True)
                elif operation == 'delete':
                    collection.delete_one(filter_query)
                
                logger.debug(f"Async Mongo {operation} successful for {collection_name}")
            except Exception as e:
                logger.error(f"Async Mongo {operation} failed for {collection_name}: {e}")
                # Log to a file or retry queue in production

        thread = threading.Thread(target=run_write)
        thread.daemon = True
        thread.start()

    # --- User Operations ---

    @staticmethod
    def get_user_by_email(email: str):
        mode = os.environ.get('READ_FROM', 'sql')
        if mode == 'mongo':
            mongodb = DBService.get_mongo_db()
            if mongodb is not None:
                user_data = mongodb.users.find_one({"email": email.lower()})
                if user_data:
                    user_data['id'] = str(user_data.pop('_id'))
                    if 'role' not in user_data:
                        user_data['role'] = 'user'
                    return user_data
        
        return User.query.filter_by(email=email.lower()).first()

    @staticmethod
    def get_user_by_id(user_id: Any):
        mode = os.environ.get('READ_FROM', 'sql')
        if mode == 'mongo':
            mongodb = DBService.get_mongo_db()
            if mongodb is not None:
                try:
                    oid = ObjectId(user_id) if isinstance(user_id, str) and len(user_id) == 24 else None
                    user_data = None
                    if oid:
                        user_data = mongodb.users.find_one({"_id": oid})
                    if not user_data:
                        user_data = mongodb.users.find_one({"sql_id": int(user_id)})
                    
                    if user_data:
                        user_data['id'] = str(user_data.pop('_id'))
                        return user_data
                except:
                    pass
        
        try:
            return User.query.get(int(user_id))
        except:
            return User.query.get(user_id)

    @staticmethod
    def create_user(name: str, email: str, password_hash: str, role: str = 'user', is_approved: bool = False, certificate_url: str = None, certificate_type: str = None):
        # 1. Primary Write (SQL)
        user = User(
            name=name, 
            email=email, 
            password_hash=password_hash, 
            role=role,
            isApproved=is_approved,
            certificate_url=certificate_url,
            certificate_type=certificate_type,
            verification_attempts=0
        )
        db.session.add(user)
        try:
            db.session.commit()
            
            # 2. Secondary Write (Mongo) - Async
            if os.environ.get('DB_MODE') in ['hybrid', 'mongo']:
                mongo_data = {
                    "sql_id": user.id,
                    "name": name,
                    "email": email.lower(),
                    "password_hash": password_hash,
                    "role": role,
                    "isApproved": is_approved,
                    "verification": {
                        "certificate_url": certificate_url,
                        "certificate_type": certificate_type,
                        "attempts": 0,
                        "rejection_reason": None
                    },
                    "created_at": datetime.utcnow(),
                    "profile": {
                        "age": None,
                        "sex": None,
                        "weight": None,
                        "height": None,
                        "hospitals": []
                    }
                }
                DBService._async_mongo_write('users', 'insert', mongo_data)
                
            return user
        except IntegrityError as e:
            db.session.rollback()
            raise e

    @staticmethod
    def update_user_gamification(user_id: Any, points: int, last_step_reward: int, streak: int):
        # 1. SQL Write
        user = User.query.get(user_id)
        if user:
            user.points = points
            user.lastStepReward = last_step_reward
            user.streak = streak
            db.session.commit()
            
            # 2. Mongo Write (Async)
            if os.environ.get('DB_MODE') in ['hybrid', 'mongo']:
                mongo_data = {
                    "points": points,
                    "lastStepReward": last_step_reward,
                    "streak": streak
                }
                filter_query = {"sql_id": int(user_id)}
                DBService._async_mongo_write('users', 'update', mongo_data, filter_query)
        return user

    @staticmethod
    def update_user_profile(user_id: Any, profile_data: Dict[str, Any]):
        # Handle ID conversion safely
        sql_id = None
        mongo_id = None
        
        try:
            if isinstance(user_id, str):
                if user_id.isdigit():
                    sql_id = int(user_id)
                elif len(user_id) == 24:
                    mongo_id = user_id
            elif isinstance(user_id, int):
                sql_id = user_id
        except:
            pass

        # 1. SQL Write
        user = None
        if sql_id:
            user = User.query.get(sql_id)
            if user:
                if 'age' in profile_data: user.age = profile_data['age']
                if 'sex' in profile_data: user.sex = profile_data['sex']
                if 'weight' in profile_data: user.weight = profile_data['weight']
                if 'height' in profile_data: user.height = profile_data['height']
                if 'hospitals' in profile_data: 
                    user.hospitals = json.dumps(profile_data['hospitals'])
                db.session.commit()
        
        # 2. Mongo Write (Async)
        if os.environ.get('DB_MODE') in ['hybrid', 'mongo']:
            mongo_update = {}
            if 'age' in profile_data: mongo_update["profile.age"] = profile_data['age']
            if 'sex' in profile_data: mongo_update["profile.sex"] = profile_data['sex']
            if 'weight' in profile_data: mongo_update["profile.weight"] = profile_data['weight']
            if 'height' in profile_data: mongo_update["profile.height"] = profile_data['height']
            if 'hospitals' in profile_data: mongo_update["profile.hospitals"] = profile_data['hospitals']
            
            if mongo_update:
                if mongo_id:
                    filter_query = {"_id": ObjectId(mongo_id)}
                elif sql_id:
                    filter_query = {"sql_id": sql_id}
                else:
                    filter_query = None
                
                if filter_query:
                    DBService._async_mongo_write('users', 'update', mongo_update, filter_query)
        
        # If we don't have a SQL user but we are in Mongo mode, we should fetch the user from Mongo for the return
        if not user and mongo_id:
            # We can't easily return a Mongo dict that mimics the to_dict() easily here without more logic
            # but let's at least ensure we don't crash
            return DBService.get_user_by_id(user_id)
            
        return user

    @staticmethod
    def get_pending_doctors():
        """List all doctors who are not yet approved."""
        mode = os.environ.get('READ_FROM', 'sql')
        if mode == 'mongo':
            mongodb = DBService.get_mongo_db()
            if mongodb is not None:
                docs = list(mongodb.users.find({"role": "doctor", "isApproved": False}))
                for d in docs:
                    d['id'] = str(d.pop('_id'))
                return docs
        
        return User.query.filter_by(role='doctor', isApproved=False).all()

    @staticmethod
    def approve_doctor(user_id: Any):
        """Approve a doctor's certificate."""
        user = DBService.get_user_by_id(user_id)
        if not user: return False
        
        # SQL Update
        if not isinstance(user, dict):
            user.isApproved = True
            db.session.commit()
        
        # Mongo Update
        if os.environ.get('DB_MODE') in ['hybrid', 'mongo']:
            update_data = {"isApproved": True}
            filter_q = {"sql_id": int(user_id)} if not isinstance(user_id, str) or user_id.isdigit() else {"_id": ObjectId(user_id)}
            DBService._async_mongo_write('users', 'update', update_data, filter_q)
        
        return True

    @staticmethod
    def reject_doctor(user_id: Any, reason: str):
        """Reject a doctor's certificate and increment attempt counter."""
        user = DBService.get_user_by_id(user_id)
        if not user: return False
        
        # SQL Update
        if not isinstance(user, dict):
            user.isApproved = False
            user.rejection_reason = reason
            user.verification_attempts = (user.verification_attempts or 0) + 1
            db.session.commit()
        
        # Mongo Update
        if os.environ.get('DB_MODE') in ['hybrid', 'mongo']:
            # Calculate new attempts
            current_attempts = 0
            if isinstance(user, dict):
                current_attempts = (user.get('verification', {}).get('attempts') or 0) + 1
            else:
                current_attempts = user.verification_attempts or 1
                
            update_data = {
                "isApproved": False,
                "verification.rejection_reason": reason,
                "verification.attempts": current_attempts
            }
            filter_q = {"sql_id": int(user_id)} if not isinstance(user_id, str) or user_id.isdigit() else {"_id": ObjectId(user_id)}
            DBService._async_mongo_write('users', 'update', update_data, filter_q)
            
        return True


    @staticmethod
    def search_users(query: str):
        """Search users by name or email (for doctors/nurses)"""
        mode = os.environ.get('READ_FROM', 'sql')
        if mode == 'mongo':
            mongodb = DBService.get_mongo_db()
            if mongodb is not None:
                mongo_query = {
                    "$or": [
                        {"name": {"$regex": query, "$options": "i"}},
                        {"email": {"$regex": query, "$options": "i"}}
                    ],
                    "role": "user" # Usually searching for patients
                }
                cursor = mongodb.users.find(mongo_query).limit(10)
                results = list(cursor)
                for r in results:
                    r['id'] = str(r.pop('_id'))
                return results

        # SQL
        q = f"%{query}%"
        users = User.query.filter(
            (User.role == 'user') & 
            ((User.name.ilike(q)) | (User.email.ilike(q)))
        ).limit(10).all()
        return users

    @staticmethod
    def get_doctors_by_hospital(hospital_name: str):
        """Fetch all doctors associated with a given hospital.
        
        Uses multi-pass matching to handle name variations between
        OSM facility names and what doctors typed in their profiles.
        E.g. 'Avdhoot Hospital' (internal) vs 'Avadhoot Hospital' (doctor profile)
        """
        from backend.utils.geocode import resolve_canonical_hospital
        import difflib
        
        # Resolve to our internal canonical name if possible
        canonical_name, _ = resolve_canonical_hospital(hospital_name)
        if canonical_name != hospital_name:
            print(f"  [DB_SERVICE] hospital_name resolved: '{hospital_name}' -> '{canonical_name}'")

        # Build a list of name variants to search for
        search_names = list(set([hospital_name, canonical_name]))
        
        mode = os.environ.get('READ_FROM', 'sql')
        if mode == 'mongo':
            mongodb = DBService.get_mongo_db()
            if mongodb is not None:
                # Build regex that matches ANY variant
                regex_pattern = "|".join(n.replace("(", r"\(").replace(")", r"\)") for n in search_names)
                cursor = mongodb.users.find({
                    "role": "doctor",
                    "profile.hospitals": {"$regex": regex_pattern, "$options": "i"}
                })
                results = list(cursor)
                for r in results:
                    r['id'] = str(r.pop('_id'))
                    
                if results:
                    return results

                # Fallback: search all doctors then fuzzy match their hospital list
                all_doctors = list(mongodb.users.find({"role": "doctor"}))
                matched = []
                for doc in all_doctors:
                    doc_hospitals = doc.get('profile', {}).get('hospitals', [])
                    if isinstance(doc_hospitals, str):
                        try:
                            doc_hospitals = json.loads(doc_hospitals)
                        except:
                            doc_hospitals = [doc_hospitals]
                    
                    for doc_h in doc_hospitals:
                        # Bidirectional substring check
                        if (doc_h.lower() in hospital_name.lower() or
                            hospital_name.lower() in doc_h.lower() or
                            doc_h.lower() in canonical_name.lower() or
                            canonical_name.lower() in doc_h.lower()):
                            doc['id'] = str(doc.pop('_id'))
                            matched.append(doc)
                            break
                        # Fuzzy match (handles Avdhoot vs Avadhoot)
                        ratio = difflib.SequenceMatcher(None, doc_h.lower(), canonical_name.lower()).ratio()
                        if ratio >= 0.85:
                            doc['id'] = str(doc.pop('_id'))
                            matched.append(doc)
                            break
                return matched

        # SQL — Multi-pass search
        all_results = []
        seen_ids = set()
        
        # Pass 1: Try each name variant with ILIKE
        for name in search_names:
            q = f"%{name}%"
            doctors = User.query.filter(
                (User.role == 'doctor') & 
                (User.hospitals.ilike(q))
            ).all()
            for d in doctors:
                if d.id not in seen_ids:
                    all_results.append(d)
                    seen_ids.add(d.id)

        if all_results:
            return all_results

        # Pass 2: Bidirectional substring + fuzzy match against each doctor's hospitals list
        all_doctors = User.query.filter(User.role == 'doctor').all()
        for doc in all_doctors:
            if doc.id in seen_ids:
                continue
            try:
                doc_hospitals = json.loads(doc.hospitals) if doc.hospitals else []
            except:
                doc_hospitals = []
            
            for doc_h in doc_hospitals:
                doc_h_lower = doc_h.lower()
                # Bidirectional substring (catches "Avadhoot Hospital" in "Avdhoot Hospital" and vice versa)
                if (doc_h_lower in hospital_name.lower() or
                    hospital_name.lower() in doc_h_lower or
                    doc_h_lower in canonical_name.lower() or
                    canonical_name.lower() in doc_h_lower):
                    all_results.append(doc)
                    seen_ids.add(doc.id)
                    break
                # Fuzzy match (handles typos like Avdhoot vs Avadhoot)
                ratio = difflib.SequenceMatcher(None, doc_h_lower, canonical_name.lower()).ratio()
                if ratio >= 0.85:
                    print(f"  [DB_SERVICE] Fuzzy doctor match: '{doc_h}' ~ '{canonical_name}' ({ratio:.0%})")
                    all_results.append(doc)
                    seen_ids.add(doc.id)
                    break

        return all_results

    @staticmethod
    def get_medical_staff_by_hospital(hospital_name: str):
        """Fetch all doctors and nurses associated with a given hospital"""
        from backend.utils.geocode import resolve_canonical_hospital
        
        # Resolve to our internal canonical name if possible
        canonical_name, _ = resolve_canonical_hospital(hospital_name)
        if canonical_name != hospital_name:
            print(f"  [DB_SERVICE] hospital_name resolved: '{hospital_name}' -> '{canonical_name}'")
            hospital_name = canonical_name

        mode = os.environ.get('READ_FROM', 'sql')
        if mode == 'mongo':
            mongodb = DBService.get_mongo_db()
            if mongodb is not None:
                cursor = mongodb.users.find({
                    "role": {"$in": ["doctor", "nurse"]},
                    "profile.hospitals": {"$regex": hospital_name, "$options": "i"}
                })
                results = list(cursor)
                for r in results:
                    r['id'] = str(r.pop('_id'))
                return results

        # SQL
        q = f"%{hospital_name}%"
        staff = User.query.filter(
            (User.role.in_(['doctor', 'nurse'])) & 
            (User.hospitals.ilike(q))
        ).all()
        return staff

    # --- Shop Operations ---

    @staticmethod
    def get_shop_items():
        mode = os.environ.get('READ_FROM', 'sql')
        if mode == 'mongo':
            mongodb = DBService.get_mongo_db()
            if mongodb is not None:
                items = list(mongodb.shop_items.find())
                for item in items:
                    item['id'] = str(item.pop('_id'))
                return items
        
        return ShopItem.query.all()

    @staticmethod
    def process_purchase(user_id: Any, item_id: Any):
        # 1. Fetch user and item
        user = User.query.get(user_id)
        # Handle string IDs for items if they came from Mongo
        if isinstance(item_id, str) and len(item_id) == 24:
             # This is a Mongo ID case, but currently we rely on SQL for logic
             # We should probably fetch the item first
             pass
        
        item = ShopItem.query.get(item_id)
        if not user or not item:
            return False, "User or Item not found"
        
        if user.points < item.points_cost:
            return False, "Insufficient points"
        
        # 2. Deduct points (SQL)
        user.points -= item.points_cost
        db.session.commit()
        
        # 3. Sync to Mongo (Async)
        if os.environ.get('DB_MODE') in ['hybrid', 'mongo']:
            DBService._async_mongo_write('users', 'update', {"points": user.points}, {"sql_id": int(user_id)})
            
        return True, "Purchase successful"

    # --- Health Analysis Operations ---

    @staticmethod
    def save_health_analysis(user_id: Any, analysis_data: Dict[str, Any]):
        # 1. SQL Write
        new_analysis = HealthAnalysis(
            user_id=user_id,
            health_score=analysis_data.get("health_score"),
            risk_level=analysis_data.get("risk_level"),
            health_status=analysis_data.get("health_status"),
            steps=analysis_data.get("steps"),
            avg_heart_rate=analysis_data.get("avg_heart_rate"),
            sleep_hours=analysis_data.get("sleep_hours"),
            diet_plan=json.dumps(analysis_data.get("diet_plan", [])),
            recommendations=json.dumps(analysis_data.get("recommendations", []))
        )
        db.session.add(new_analysis)
        db.session.commit()

        # 2. Mongo Write (Async)
        if os.environ.get('DB_MODE') in ['hybrid', 'mongo']:
            mongo_data = {
                "sql_id": new_analysis.id,
                "user_id": str(user_id),
                "health_score": analysis_data.get("health_score"),
                "risk_level": analysis_data.get("risk_level"),
                "health_status": analysis_data.get("health_status"),
                "metrics": {
                    "steps": analysis_data.get("steps"),
                    "avg_heart_rate": analysis_data.get("avg_heart_rate"),
                    "sleep_hours": analysis_data.get("sleep_hours")
                },
                "diet_plan": analysis_data.get("diet_plan", []),
                "recommendations": analysis_data.get("recommendations", []),
                "created_at": datetime.utcnow()
            }
            DBService._async_mongo_write('health_analyses', 'insert', mongo_data)
            
        return new_analysis

    @staticmethod
    def get_latest_health_analysis(user_id: Any):
        mode = os.environ.get('READ_FROM', 'sql')
        if mode == 'mongo':
            mongodb = DBService.get_mongo_db()
            if mongodb is not None:
                latest = mongodb.health_analyses.find_one(
                    {"user_id": str(user_id)},
                    sort=[("created_at", -1)]
                )
                if latest:
                    latest['id'] = str(latest.pop('_id'))
                    return latest
        
        return HealthAnalysis.query.filter_by(user_id=user_id).order_by(HealthAnalysis.created_at.desc()).first()

    @staticmethod
    def sync_health_analysis_to_mongo(record: HealthAnalysis):
        """Surgically sync a HealthAnalysis SQL record to MongoDB."""
        if os.environ.get('DB_MODE') not in ['hybrid', 'mongo']:
            return

        try:
            # Prepare data from model object
            analysis_data = {
                "sql_id": record.id,
                "user_id": str(record.user_id),
                "health_score": record.health_score,
                "risk_level": record.risk_level,
                "health_status": record.health_status,
                "metrics": {
                    "steps": record.steps,
                    "avg_heart_rate": record.avg_heart_rate,
                    "sleep_hours": record.sleep_hours
                },
                "diet_plan": json.loads(record.diet_plan) if isinstance(record.diet_plan, str) else record.diet_plan,
                "recommendations": json.loads(record.recommendations) if isinstance(record.recommendations, str) else record.recommendations,
                "data_source": record.data_source,
                "created_at": record.created_at
            }
            
            # Use date-based filter for Mongo upsert to match SQL behavior
            date_str = record.created_at.strftime('%Y-%m-%d')
            filter_query = {"user_id": str(record.user_id), "date": date_str}
            
            # Also add literal date for easier Mongo queries
            analysis_data["date"] = date_str
            
            DBService._async_mongo_write('health_analyses', 'update', analysis_data, filter_query)
        except Exception as e:
            logger.error(f"Failed to sync record {record.id} to Mongo: {e}")

    @staticmethod
    def upsert_health_analysis_by_date(user_id: Any, date_str: str, analysis_data: Dict[str, Any], data_source: str = 'google_fit'):
        # 1. SQL
        day_start = datetime.strptime(date_str, '%Y-%m-%d')
        day_end = day_start + timedelta(days=1)
        
        existing = HealthAnalysis.query.filter(
            HealthAnalysis.user_id == user_id,
            HealthAnalysis.created_at >= day_start,
            HealthAnalysis.created_at < day_end
        ).order_by(HealthAnalysis.created_at.desc()).first()

        if existing:
            existing.health_score = analysis_data.get('health_score', 0)
            existing.risk_level = analysis_data.get('risk_level', 'Low')
            existing.health_status = analysis_data.get('health_status', 'N/A')
            existing.steps = analysis_data['steps']
            existing.avg_heart_rate = analysis_data['avg_heart_rate']
            existing.sleep_hours = analysis_data['sleep_hours']
            existing.diet_plan = json.dumps(analysis_data.get('diet_plan', []))
            existing.recommendations = json.dumps(analysis_data.get('recommendations', []))
            existing.data_source = data_source
        else:
            existing = HealthAnalysis(
                user_id=user_id,
                health_score=analysis_data.get('health_score', 0),
                risk_level=analysis_data.get('risk_level', 'Low'),
                health_status=analysis_data.get('health_status', 'N/A'),
                steps=analysis_data['steps'],
                avg_heart_rate=analysis_data['avg_heart_rate'],
                sleep_hours=analysis_data['sleep_hours'],
                diet_plan=json.dumps(analysis_data.get('diet_plan', [])),
                recommendations=json.dumps(analysis_data.get('recommendations', [])),
                data_source=data_source,
                created_at=day_start + timedelta(hours=12)
            )
            db.session.add(existing)
        
        db.session.commit()

        # 2. Mongo (Async)
        if os.environ.get('DB_MODE') in ['hybrid', 'mongo']:
            mongo_data = {
                "sql_id": existing.id,
                "user_id": str(user_id),
                "date": date_str,
                "health_score": analysis_data.get('health_score', 0),
                "risk_level": analysis_data.get('risk_level', 'Low'),
                "health_status": analysis_data.get('health_status', 'N/A'),
                "metrics": {
                    "steps": analysis_data['steps'],
                    "avg_heart_rate": analysis_data['avg_heart_rate'],
                    "sleep_hours": analysis_data['sleep_hours']
                },
                "diet_plan": analysis_data.get('diet_plan', []),
                "recommendations": analysis_data.get('recommendations', []),
                "data_source": data_source,
                "created_at": day_start + timedelta(hours=12)
            }
            # Use date-based filter for Mongo upsert
            filter_query = {"user_id": str(user_id), "date": date_str}
            DBService._async_mongo_write('health_analyses', 'update', mongo_data, filter_query)
            
        return existing

    @staticmethod
    def get_health_report(user_id: Any, days: int = 14):
        mode = os.environ.get('READ_FROM', 'sql')
        if mode == 'mongo':
            mongodb = DBService.get_mongo_db()
            if mongodb is not None:
                cursor = mongodb.health_analyses.find(
                    {"user_id": str(user_id)}
                ).sort("created_at", -1).limit(50)
                
                results = list(cursor)
                for r in results:
                    r['id'] = str(r.pop('_id'))
                return results

        return HealthAnalysis.query.filter(HealthAnalysis.user_id == user_id).order_by(HealthAnalysis.created_at.desc()).all()

    # --- Appointment Operations ---

    @staticmethod
    def create_appointment(data: Dict[str, Any]):
        # SQL Write
        appointment = Appointment(
             user_id=data.get('patient_id', 1), # Fallback to 1 if missing for legacy
             patient_id=data.get('patient_id'),
             doctor_id=data.get('doctor_id'),
             status=data.get('status', 'PENDING'),
             requested_date=str(data.get('appointment_date')),
             requested_time=data.get('appointment_time')
        )
        # Assuming legacy generic payload attributes exist dynamically or are safely skipped
        for key in ['name', 'email', 'phone', 'mode', 'appointment_date', 'appointment_time', 'reason']:
            if hasattr(appointment, key) or key in data:
                try: setattr(appointment, key, data[key])
                except: pass
                
        db.session.add(appointment)
        db.session.commit()

        # Mongo Write (Async)
        if os.environ.get('DB_MODE') in ['hybrid', 'mongo']:
            mongo_data = {
                "sql_id": appointment.id,
                "name": data['name'],
                "email": data['email'],
                "phone": data['phone'],
                "mode": data['mode'],
                "appointment_date": str(data['appointment_date']),
                "appointment_time": data['appointment_time'],
                "reason": data['reason'],
                "status": data.get('status', 'PENDING'),
                "patient_id": data.get('patient_id'),
                "doctor_id": data.get('doctor_id'),
                "created_at": datetime.utcnow()
            }
            DBService._async_mongo_write('appointments', 'insert', mongo_data)
        
        return appointment

    @staticmethod
    def get_appointment(appointment_id: Any):
        mode = os.environ.get('READ_FROM', 'sql')
        if mode == 'mongo':
            mongodb = DBService.get_mongo_db()
            if mongodb is not None:
                try:
                    oid = ObjectId(appointment_id) if isinstance(appointment_id, str) and len(appointment_id) == 24 else appointment_id
                    data = mongodb.appointments.find_one({"_id": oid})
                    if not data:
                        data = mongodb.appointments.find_one({"sql_id": int(appointment_id)})
                    if data:
                        data['id'] = str(data.pop('_id'))
                        return data
                except:
                    pass
        return Appointment.query.get(appointment_id)

    @staticmethod
    def list_appointments(filters: Dict[str, Any]):
        mode = os.environ.get('READ_FROM', 'sql')
        if mode == 'mongo':
            mongodb = DBService.get_mongo_db()
            if mongodb is not None:
                mongo_query = {}
                if filters.get('status'): mongo_query['status'] = filters['status']
                if filters.get('mode'): mongo_query['mode'] = filters['mode']
                if filters.get('date'): mongo_query['appointment_date'] = filters['date']
                
                cursor = mongodb.appointments.find(mongo_query).sort("created_at", -1)
                results = list(cursor)
                for r in results:
                    r['id'] = str(r.pop('_id'))
                return results

        # SQL
        query = Appointment.query
        if filters.get('status'): query = query.filter_by(status=filters['status'])
        if filters.get('mode'): query = query.filter_by(mode=filters['mode'])
        if filters.get('date'): 
            date_obj = datetime.strptime(filters['date'], '%Y-%m-%d').date()
            query = query.filter_by(appointment_date=date_obj)
        
        return query.order_by(Appointment.created_at.desc()).all()

    @staticmethod
    def update_appointment_status(appointment_id: Any, status: str):
        # 1. SQL
        appointment = None
        try:
            sql_id = int(appointment_id)
            appointment = Appointment.query.get(sql_id)
        except (ValueError, TypeError):
            # Might be a Mongo ID
            if isinstance(appointment_id, str) and len(appointment_id) == 24:
                mongodb = DBService.get_mongo_db()
                if mongodb is not None:
                    data = mongodb.appointments.find_one({"_id": ObjectId(appointment_id)})
                    if data and 'sql_id' in data:
                        appointment = Appointment.query.get(data['sql_id'])

        if appointment:
            appointment.status = status
            db.session.commit()
        
        # 2. Mongo (Async)
        if os.environ.get('DB_MODE') in ['hybrid', 'mongo']:
            try:
                oid = ObjectId(appointment_id) if isinstance(appointment_id, str) and len(appointment_id) == 24 else None
                filter_query = {"_id": oid} if oid else {"sql_id": int(appointment_id)}
                DBService._async_mongo_write('appointments', 'update', {"status": status}, filter_query)
            except:
                pass
        
        return appointment

    @staticmethod
    def delete_appointment(appointment_id: Any):
        # 1. SQL
        appointment = Appointment.query.get(appointment_id)
        if appointment:
            db.session.delete(appointment)
            db.session.commit()
            
        # 2. Mongo (Async)
        if os.environ.get('DB_MODE') in ['hybrid', 'mongo']:
            try:
                oid = ObjectId(appointment_id) if isinstance(appointment_id, str) and len(appointment_id) == 24 else None
                filter_query = {"_id": oid} if oid else {"sql_id": int(appointment_id)}
                DBService._async_mongo_write('appointments', 'delete', {}, filter_query)
            except:
                pass
        
        return True

    # --- Alert Operations ---

    @staticmethod
    def create_alert(alert_data: Dict[str, Any]):
        # 1. SQL Write
        new_alert = Alert(
            patient_id=alert_data.get('patient_id'),
            room_number=alert_data.get('room_number'),
            status=alert_data.get('status'),
            confidence=alert_data.get('confidence'),
            reason=alert_data.get('reason'),
            detected_issues=json.dumps(alert_data.get('detected_issues', [])),
            recommended_action=alert_data.get('recommended_action'),
            alert=alert_data.get('alert', False),
            # SOS geolocation fields
            latitude=alert_data.get('latitude'),
            longitude=alert_data.get('longitude'),
            location_type=alert_data.get('location_type', 'WARD'),
            nearest_hospital=alert_data.get('nearest_hospital'),
            distance_km=alert_data.get('distance_km'),
            notified_doctor_ids=alert_data.get('notified_doctor_ids'),
            ward_number=alert_data.get('ward_number')
        )
        db.session.add(new_alert)
        db.session.commit()

        # 2. Mongo Write (Async)
        if os.environ.get('DB_MODE') in ['hybrid', 'mongo']:
            mongo_data = {
                "sql_id": new_alert.id,
                "patient_id": alert_data.get('patient_id'),
                "room_number": alert_data.get('room_number'),
                "ward_number": alert_data.get('ward_number'),
                "status": alert_data.get('status'),
                "confidence": alert_data.get('confidence'),
                "reason": alert_data.get('reason'),
                "detected_issues": alert_data.get('detected_issues', []),
                "recommended_action": alert_data.get('recommended_action'),
                "alert": alert_data.get('alert', False),
                "acknowledged": False,
                "resolved": False,
                # SOS geolocation fields
                "latitude": alert_data.get('latitude'),
                "longitude": alert_data.get('longitude'),
                "location_type": alert_data.get('location_type', 'WARD'),
                "nearest_hospital": alert_data.get('nearest_hospital'),
                "distance_km": alert_data.get('distance_km'),
                "notified_doctor_ids": alert_data.get('notified_doctor_ids'),
                "created_at": datetime.utcnow()
            }
            DBService._async_mongo_write('alerts', 'insert', mongo_data)
            
        return new_alert

    @staticmethod
    def list_alerts(filters: Dict[str, Any]):
        mode = os.environ.get('READ_FROM', 'sql')
        if mode == 'mongo':
            mongodb = DBService.get_mongo_db()
            if mongodb is not None:
                mongo_query = {}
                if filters.get('patient_id'): mongo_query['patient_id'] = filters['patient_id']
                if filters.get('status'): mongo_query['status'] = filters['status']
                if filters.get('alert') is not None: mongo_query['alert'] = filters['alert']
                
                cursor = mongodb.alerts.find(mongo_query).sort("created_at", -1)
                results = list(cursor)
                for r in results:
                    r['id'] = str(r.pop('_id'))
                    if 'created_at' in r and isinstance(r['created_at'], datetime):
                        r['created_at'] = r['created_at'].isoformat() + "Z"
                return results

        # SQL
        query = Alert.query
        if filters.get('patient_id'): query = query.filter_by(patient_id=filters['patient_id'])
        if filters.get('status'): query = query.filter_by(status=filters['status'])
        if filters.get('alert') is not None: query = query.filter_by(alert=filters['alert'])
        
        return query.order_by(Alert.created_at.desc()).all()

    @staticmethod
    def update_alert_status(alert_id: Any, updates: Dict[str, Any]):
        # 1. SQL
        alert = None
        try:
            sql_id = int(alert_id)
            alert = Alert.query.get(sql_id)
        except (ValueError, TypeError):
            # Might be a Mongo ID
            if isinstance(alert_id, str) and len(alert_id) == 24:
                mongodb = DBService.get_mongo_db()
                if mongodb is not None:
                    data = mongodb.alerts.find_one({"_id": ObjectId(alert_id)})
                    if data and 'sql_id' in data:
                        alert = Alert.query.get(data['sql_id'])

        if alert:
            if 'acknowledged' in updates: alert.acknowledged = updates['acknowledged']
            if 'resolved' in updates: alert.resolved = updates['resolved']
            db.session.commit()
        
        # 2. Mongo (Async)
        if os.environ.get('DB_MODE') in ['hybrid', 'mongo']:
            try:
                oid = ObjectId(alert_id) if isinstance(alert_id, str) and len(alert_id) == 24 else None
                filter_query = {"_id": oid} if oid else {"sql_id": int(alert_id)}
                DBService._async_mongo_write('alerts', 'update', updates, filter_query)
            except:
                pass
        
        return alert
