import sqlite3
import os

db_path = 'app.db'
if not os.path.exists(db_path):
    # Try project root
    db_path = os.path.join('project', 'app.db')

print(f"Connecting to {db_path}...")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

def add_column(table, column, col_type):
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        print(f"Added column {column} to {table}")
    except sqlite3.OperationalError:
        print(f"Column {column} already exists in {table}")

# 1. Update appointments
add_column('appointments', 'ward_number', 'VARCHAR(50)')
add_column('appointments', 'ward_assigned_at', 'DATETIME')

# 2. Update alerts
add_column('alerts', 'latitude', 'FLOAT')
add_column('alerts', 'longitude', 'FLOAT')
add_column('alerts', 'location_type', 'VARCHAR(20) DEFAULT "WARD"')
add_column('alerts', 'nearest_hospital', 'VARCHAR(120)')
add_column('alerts', 'distance_km', 'FLOAT')
add_column('alerts', 'notified_doctor_ids', 'TEXT')

# 3. Create audit_logs table
try:
    cursor.execute('''
        CREATE TABLE audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action VARCHAR(50) NOT NULL,
            appointment_id INTEGER,
            patient_id VARCHAR(50),
            doctor_id INTEGER,
            ward_number VARCHAR(50),
            details TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (appointment_id) REFERENCES appointments (id),
            FOREIGN KEY (doctor_id) REFERENCES users (id)
        )
    ''')
    print("Created table audit_logs")
except sqlite3.OperationalError:
    print("Table audit_logs already exists")

conn.commit()
conn.close()
print("Migration complete.")
