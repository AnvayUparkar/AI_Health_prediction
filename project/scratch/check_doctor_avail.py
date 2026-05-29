import sys
import os

# Ensure repo root is on sys.path
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from backend.models import db
from app import create_app
import sqlite3

def check():
    db_path = os.path.join("backend", "app.db")
    if not os.path.exists(db_path):
         db_path = "app.db"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Let's list tables in sqlite db to see the doctor availability table name
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print("Tables:", [t[0] for t in tables])
    
    # Check if doctor_availability exists
    if "doctor_availability" in [t[0] for t in tables]:
        cursor.execute("SELECT * FROM doctor_availability")
        rows = cursor.fetchall()
        print("\nDoctor Availability rows:")
        for row in rows:
            print(row)
            
    conn.close()

if __name__ == "__main__":
    check()
