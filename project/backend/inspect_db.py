import sqlite3
import os

def inspect_db():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    db_path = os.path.join(repo_root, 'app.db')
    
    if not os.path.exists(db_path):
        print(f"[ERROR] Database file not found at: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print(f"Database: {db_path}")
    print(f"Tables found: {[t[0] for t in tables]}\n")
    
    for table_name in [t[0] for t in tables]:
        print(f"--- Table: {table_name} ---")
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
        
        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        count = cursor.fetchone()[0]
        print(f"  Total records: {count}\n")
    
    conn.close()

if __name__ == "__main__":
    inspect_db()
