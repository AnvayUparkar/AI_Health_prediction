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
        
        # 1. Add isApproved
        if 'isApproved' not in columns:
            print("Adding 'isApproved' column...")
            cursor.execute("ALTER TABLE users ADD COLUMN isApproved BOOLEAN DEFAULT 0")
        
        # 2. Add certificate_url
        if 'certificate_url' not in columns:
            print("Adding 'certificate_url' column...")
            cursor.execute("ALTER TABLE users ADD COLUMN certificate_url VARCHAR(512)")
            
        # 3. Add certificate_type
        if 'certificate_type' not in columns:
            print("Adding 'certificate_type' column...")
            cursor.execute("ALTER TABLE users ADD COLUMN certificate_type VARCHAR(20)")

        # 4. Add verification_attempts
        if 'verification_attempts' not in columns:
            print("Adding 'verification_attempts' column...")
            cursor.execute("ALTER TABLE users ADD COLUMN verification_attempts INTEGER DEFAULT 0")

        # 5. Add rejection_reason
        if 'rejection_reason' not in columns:
            print("Adding 'rejection_reason' column...")
            cursor.execute("ALTER TABLE users ADD COLUMN rejection_reason TEXT")
            
        conn.commit()
        print("[OK] Migration successful.")
            
    except Exception as e:
        print(f"[FAIL] Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_db()
