import sqlite3
import os

db_path = os.path.join('backend', 'app.db')
if not os.path.exists(db_path):
    print(f"DB not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

columns = [
    ("age", "INTEGER"),
    ("sex", "VARCHAR(20)"),
    ("weight", "FLOAT"),
    ("height", "FLOAT"),
    ("hospitals", "TEXT")
]

for col_name, col_type in columns:
    try:
        cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
        print(f"Added column {col_name}")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print(f"Column {col_name} already exists")
        else:
            print(f"Error adding {col_name}: {e}")

conn.commit()
conn.close()
print("Migration complete.")
