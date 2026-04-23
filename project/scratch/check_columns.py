
import sqlite3
conn = sqlite3.connect('app.db')
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(appointments);")
columns = cursor.fetchall()
for col in columns:
    print(col)
conn.close()
