
import sqlite3
import os

db_path = os.path.join(os.getcwd(), 'app.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

new_cols = [
    ('name', 'VARCHAR(120)'),
    ('email', 'VARCHAR(120)'),
    ('phone', 'VARCHAR(20)'),
    ('reason', 'TEXT')
]

for col_name, col_type in new_cols:
    try:
        cursor.execute(f"ALTER TABLE appointments ADD COLUMN {col_name} {col_type};")
        print(f"Added column {col_name}")
    except sqlite3.OperationalError:
        print(f"Column {col_name} already exists or error.")

conn.commit()
conn.close()
