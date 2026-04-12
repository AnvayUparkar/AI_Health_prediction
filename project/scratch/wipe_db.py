import os
import sys

# Add the root directory to path so we can import project modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from backend.models import db

def wipe_database():
    app = create_app()
    with app.app_context():
        print("Wiping database...")
        db.drop_all()
        db.create_all()
        print("Database wiped and tables re-created successfully.")

if __name__ == "__main__":
    wipe_database()
