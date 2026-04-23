
import os
import sys
import json
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.getcwd())

from flask import Flask
from backend.models import db, Appointment, User, Doctor

app = Flask(__name__)
# It's in the root
db_path = os.path.join(os.getcwd(), 'app.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    print(f"Connecting to: {db_path}")
    try:
        appts = Appointment.query.all()
        print(f"Total Appointments: {len(appts)}")
        for a in appts:
            print(f"ID: {a.id}, PatientID: {a.patient_id}, ReqDate: {a.requested_date}, ReqTime: {a.requested_time}, Status: {a.status}")
    except Exception as e:
        print(f"Error checking appts: {e}")
