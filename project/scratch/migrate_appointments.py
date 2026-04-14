import sqlite3
import os

db_path = 'app.db'
if not os.path.exists(db_path):
    print(f"DB not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

columns = [
    ("patient_id", "INTEGER"),
    ("status", "VARCHAR(20) DEFAULT 'PENDING'"),
    ("requested_date", "VARCHAR(20)"),
    ("requested_time", "VARCHAR(20)"),
    ("suggested_dates", "TEXT"),
    ("suggested_times", "TEXT"),
    ("isChecked", "BOOLEAN DEFAULT 0"),
    ("isAdmitted", "BOOLEAN DEFAULT 0"),
    ("created_at", "DATETIME DEFAULT CURRENT_TIMESTAMP"),
    ("updated_at", "DATETIME DEFAULT CURRENT_TIMESTAMP")
]

for col_name, col_type in columns:
    try:
        cursor.execute(f"ALTER TABLE appointments ADD COLUMN {col_name} {col_type}")
        print(f"Added column {col_name}")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print(f"Column {col_name} already exists")
        else:
            print(f"Error adding {col_name}: {e}")

conn.commit()
conn.close()
print("Migration complete on project/app.db")
