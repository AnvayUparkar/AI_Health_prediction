"""One-time script: resolve old alerts that have no notified_doctor_ids (leak to all staff)"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from backend.db_service import DBService
from backend.models import db, Alert

app = create_app()
with app.app_context():
    # 1. SQL cleanup
    old_sql = Alert.query.filter(
        Alert.notified_doctor_ids == None,
        Alert.alert == True,
        Alert.resolved == False
    ).count()
    print(f"SQL: Found {old_sql} old alerts without notified_doctor_ids")
    if old_sql > 0:
        Alert.query.filter(
            Alert.notified_doctor_ids == None,
            Alert.alert == True,
            Alert.resolved == False
        ).update({Alert.resolved: True})
        db.session.commit()
        print(f"SQL: Resolved {old_sql} old leaky alerts")

    # 2. Mongo cleanup
    m = DBService.get_mongo_db()
    if m is not None:
        r = m.alerts.update_many(
            {"notified_doctor_ids": {"$exists": False}, "alert": True},
            {"$set": {"resolved": True}}
        )
        print(f"Mongo: Resolved {r.modified_count} old leaky alerts")
    else:
        print("Mongo not available, skipping")

    print("Done. Old alerts will no longer leak to all staff.")
