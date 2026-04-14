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
    def create_user(name: str, email: str, password_hash: str, role: str = 'user'):
        # 1. Primary Write (SQL)
        user = User(name=name, email=email, password_hash=password_hash, role=role)
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
                    "created_at": datetime.utcnow()
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
            name=data['name'],
            email=data['email'],
            phone=data['phone'],
            mode=data['mode'],
            appointment_date=data['appointment_date'],
            appointment_time=data['appointment_time'],
            reason=data['reason'],
            status=data.get('status', 'pending')
        )
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
                "status": data.get('status', 'pending'),
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
            alert=alert_data.get('alert', False)
        )
        db.session.add(new_alert)
        db.session.commit()

        # 2. Mongo Write (Async)
        if os.environ.get('DB_MODE') in ['hybrid', 'mongo']:
            mongo_data = {
                "sql_id": new_alert.id,
                "patient_id": alert_data.get('patient_id'),
                "room_number": alert_data.get('room_number'),
                "status": alert_data.get('status'),
                "confidence": alert_data.get('confidence'),
                "reason": alert_data.get('reason'),
                "detected_issues": alert_data.get('detected_issues', []),
                "recommended_action": alert_data.get('recommended_action'),
                "alert": alert_data.get('alert', False),
                "acknowledged": False,
                "resolved": False,
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
