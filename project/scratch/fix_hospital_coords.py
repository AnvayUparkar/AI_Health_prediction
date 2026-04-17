import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from backend.models import db, Hospital

app = create_app()
with app.app_context():
    h = Hospital.query.filter(Hospital.name.ilike("%avdhoot%")).first()
    if h:
        print(f"BEFORE: {h.name} -> lat={h.latitude}, lon={h.longitude}")
        h.latitude = 19.1597689
        h.longitude = 72.9925981
        db.session.commit()
        print(f"AFTER:  {h.name} -> lat={h.latitude}, lon={h.longitude}")
    else:
        print("Hospital not found in SQL")
