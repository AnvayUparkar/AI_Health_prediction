import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), '..', 'app.db')

def migrate_db():
    print(f"Connecting to database at {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("Checking if columns exist in 'users' table...")
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # 1. Add role
        if 'role' not in columns:
            print("Adding 'role' column to 'users' table...")
            cursor.execute("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'user'")
            conn.commit()
            print("[OK] Column 'role' added successfully.")
        else:
            print("[INFO] Column 'role' already exists.")

        # 2. Add created_at
        if 'created_at' not in columns:
            print("Adding 'created_at' column to 'users' table...")
            cursor.execute("ALTER TABLE users ADD COLUMN created_at DATETIME")
            conn.commit()
            print("[OK] Column 'created_at' added successfully.")
        else:
            print("[INFO] Column 'created_at' already exists.")
            
    except Exception as e:
        print(f"[FAIL] Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_db()
