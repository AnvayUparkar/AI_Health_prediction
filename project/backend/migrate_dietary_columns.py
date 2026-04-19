
import sys
import os
import sqlite3

# Ensure we can find the app.db
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(repo_root, 'app.db')

def migrate():
    if not os.path.exists(db_path):
        print(f"[ERROR] Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"Connecting to database: {db_path}")

    try:
        # Add diet_preference
        print("Adding 'diet_preference' column to 'users' table...")
        cursor.execute("ALTER TABLE users ADD COLUMN diet_preference VARCHAR(20) DEFAULT 'veg'")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("  [SKIP] 'diet_preference' already exists")
        else:
            print(f"  [ERROR] {e}")

    try:
        # Add non_veg_preferences
        print("Adding 'non_veg_preferences' column to 'users' table...")
        cursor.execute("ALTER TABLE users ADD COLUMN non_veg_preferences TEXT")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("  [SKIP] 'non_veg_preferences' already exists")
        else:
            print(f"  [ERROR] {e}")

    try:
        # Add allergies
        print("Adding 'allergies' column to 'users' table...")
        cursor.execute("ALTER TABLE users ADD COLUMN allergies TEXT")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("  [SKIP] 'allergies' already exists")
        else:
            print(f"  [ERROR] {e}")

    conn.commit()
    conn.close()
    print("\n[OK] Migration complete.")

if __name__ == "__main__":
    migrate()
