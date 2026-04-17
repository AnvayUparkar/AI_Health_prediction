import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from backend.db_service import DBService
from backend.models import User

app = create_app()
with app.app_context():
    # Check SQL
    users = User.query.filter(User.role.in_(['doctor', 'nurse'])).all()
    print(f"Found {len(users)} staff in SQL:")
    for u in users:
        print(f"  {u.name} ({u.role}): hospitals={u.hospitals}")
    
    # Check Mongo
    m = DBService.get_mongo_db()
    if m is not None:
        mongo_users = list(m.users.find({"role": {"$in": ["doctor", "nurse"]}}))
        print(f"\nFound {len(mongo_users)} staff in Mongo:")
        for u in mongo_users:
            name = u.get('name', '?')
            role = u.get('role', '?')
            hospitals = u.get('profile', {}).get('hospitals', '?')
            print(f"  {name} ({role}): hospitals={hospitals}")
    else:
        print("\nMongo connection failed.")
