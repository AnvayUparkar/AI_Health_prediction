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
        
        # 1. Add points
        if 'points' not in columns:
            print("Adding 'points' column to 'users' table...")
            cursor.execute("ALTER TABLE users ADD COLUMN points INTEGER DEFAULT 0")
            conn.commit()
            print("[OK] Column 'points' added successfully.")
        
        # 2. Add lastStepReward
        if 'lastStepReward' not in columns:
            print("Adding 'lastStepReward' column to 'users' table...")
            cursor.execute("ALTER TABLE users ADD COLUMN lastStepReward INTEGER DEFAULT 0")
            conn.commit()
            print("[OK] Column 'lastStepReward' added successfully.")

        # 3. Add streak
        if 'streak' not in columns:
            print("Adding 'streak' column to 'users' table...")
            cursor.execute("ALTER TABLE users ADD COLUMN streak INTEGER DEFAULT 0")
            conn.commit()
            print("[OK] Column 'streak' added successfully.")

        # 4. Create shop_items table
        print("Creating 'shop_items' table if it doesn't exist...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shop_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                description VARCHAR(256),
                points_cost INTEGER NOT NULL,
                image_url VARCHAR(512),
                category VARCHAR(50) DEFAULT 'wellness'
            )
        ''')
        conn.commit()
        print("[OK] Table 'shop_items' is ready.")
            
    except Exception as e:
        print(f"[FAIL] Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_db()
