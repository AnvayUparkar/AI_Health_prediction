import sqlite3
import os

def test():
    db_path = os.path.join("backend", "app.db")
    if not os.path.exists(db_path):
         db_path = "app.db"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, role, email FROM users")
    rows = cursor.fetchall()
    print("Users table:")
    for row in rows:
        print(f"ID: {row[0]}, Name: {row[1]}, Role: {row[2]}, Email: {row[3]}")
    
    conn.close()

if __name__ == "__main__":
    test()
