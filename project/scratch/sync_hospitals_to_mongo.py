import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from backend.models import db, Hospital
from backend.db_service import DBService

app = create_app()
with app.app_context():
    mongodb = DBService.get_mongo_db()
    if mongodb is None:
        print("Error: Could not connect to MongoDB.")
        sys.exit(1)

    # 1. Fetch from SQL (Geocoded recently)
    sql_hospitals = Hospital.query.all()
    print(f"Found {len(sql_hospitals)} hospitals in SQL.")

    # 2. Update Mongo
    collection = mongodb.hospitals
    print("Syncing hospitals to MongoDB...")

    for h in sql_hospitals:
        data = h.to_dict()
        # Use name as a unique identifier for now
        collection.update_one(
            {"name": h.name},
            {"$set": {
                "latitude": h.latitude,
                "longitude": h.longitude,
                "capacity": h.capacity,
                "emergency_available": h.emergency_available,
                "sql_id": h.id
            }},
            upsert=True
        )
        print(f"  Synced: {h.name}")

    print("\n[OK] Synchronization complete.")
