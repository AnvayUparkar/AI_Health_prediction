import sqlite3
import os

def migrate():
    # Try several common locations for app.db
    possible_paths = [
        os.path.join(os.getcwd(), 'app.db'),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app.db'),
        os.path.join(os.path.dirname(__file__), 'app.db'),
        os.path.join(os.getcwd(), 'instance', 'health_app.db')
    ]
    
    db_path = None
    for path in possible_paths:
        if os.path.exists(path):
            db_path = path
            break
            
    if not db_path:
        print(f"Error: Database app.db not found in {possible_paths}")
        return

    print(f"Migrating database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Add new columns to 'appointments' table
        new_columns = [
            ("mode", "TEXT DEFAULT 'offline'"),
            ("meeting_link", "TEXT"),
            ("meeting_id", "TEXT"),
            ("meeting_password", "TEXT")
        ]

        for col_name, col_type in new_columns:
            try:
                cursor.execute(f"ALTER TABLE appointments ADD COLUMN {col_name} {col_type}")
                print(f"Added column: {col_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print(f"Column already exists: {col_name}")
                else:
                    raise e

        # Update existing records to 'offline' if needed
        cursor.execute("UPDATE appointments SET mode = 'offline' WHERE mode IS NULL")

        conn.commit()
        print("Migration completed successfully.")
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
