import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), '..', 'app.db')

def list_users():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email FROM users")
    users = cursor.fetchall()
    for u in users:
        print(u)
    conn.close()

if __name__ == "__main__":
    list_users()
