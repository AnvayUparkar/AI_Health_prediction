import sqlite3
import os

def migrate():
    db_path = os.path.join(os.path.dirname(__file__), '..', 'app.db')
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print("Adding 'hospital_name' column to appointments table...")
        cursor.execute("ALTER TABLE appointments ADD COLUMN hospital_name VARCHAR(120)")
        conn.commit()
        print("Column added successfully.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("Column 'hospital_name' already exists.")
        else:
            print(f"Error adding column: {e}")

    # Backfill: For existing admitted patients, use their doctor's hospital
    print("Backfilling existing admitted patients...")
    try:
        cursor.execute("""
            UPDATE appointments 
            SET hospital_name = (
                SELECT hospital_id 
                FROM doctors 
                WHERE doctors.id = appointments.doctor_id
            )
            WHERE isAdmitted = 1 AND hospital_name IS NULL
        """)
        conn.commit()
        print(f"Backfilled {cursor.rowcount} appointments.")
    except Exception as e:
        print(f"Error during backfill: {e}")

    conn.close()

if __name__ == "__main__":
    migrate()
