import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from backend.db_service import DBService
from backend.models import Hospital

app = create_app()
with app.app_context():
    # Check Mongo first
    m = DBService.get_mongo_db()
    if m is not None:
        hospitals = list(m.hospitals.find())
        print(f"Found {len(hospitals)} hospitals in Mongo:")
        for h in hospitals:
            name = h.get('name', '?')
            lat = h.get('latitude', h.get('lat', 'MISSING'))
            lon = h.get('longitude', h.get('lon', 'MISSING'))
            print(f"  {name}: lat={lat}, lon={lon}")
    
    # Also check SQL
    sql_hospitals = Hospital.query.all()
    print(f"\nFound {len(sql_hospitals)} hospitals in SQL:")
    for h in sql_hospitals:
        d = h.to_dict()
        print(f"  {d.get('name')}: lat={d.get('latitude')}, lon={d.get('longitude')}")
