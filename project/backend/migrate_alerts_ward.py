import sqlite3
import os

backend_dir = os.path.dirname(__file__)
db_path = os.path.abspath(os.path.join(backend_dir, '..', 'app.db'))

def migrate_db():
    print(f"Connecting to database at {db_path}...")
    if not os.path.exists(db_path):
        print(f"[ERROR] Database file not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("Checking if columns exist in 'alerts' table...")
        cursor.execute("PRAGMA table_info(alerts)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # 1. Add ward_number
        if 'ward_number' not in columns:
            print("Adding 'ward_number' column to 'alerts' table...")
            cursor.execute("ALTER TABLE alerts ADD COLUMN ward_number VARCHAR(50)")
            conn.commit()
            print("[OK] Migration successful.")
        else:
            print("[INFO] 'ward_number' column already exists.")
            
    except Exception as e:
        print(f"[FAIL] Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_db()
