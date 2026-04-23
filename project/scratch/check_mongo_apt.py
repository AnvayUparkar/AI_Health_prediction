import sys
import os
from dotenv import load_dotenv
load_dotenv()
sys.path.append(os.getcwd())
from backend.db_service import DBService

mongodb = DBService.get_mongo_db()
if mongodb is not None:
    apt = mongodb.appointments.find_one(sort=[("created_at", -1)])
    if apt:
        print(f"ID: {apt.get('_id')}")
        print(f"Name: {apt.get('name')}")
        print(f"Email: {apt.get('email')}")
        print(f"Status: {apt.get('status')}")
        print(f"Meeting Link: {apt.get('meeting_link')}")
    else:
        print("No appointments in Mongo")
else:
    print("Could not connect to Mongo")
