
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from backend.models import db, User
import sqlalchemy

app = create_app()

def check_table_columns(table_name):
    inspector = sqlalchemy.inspect(db.engine)
    columns = inspector.get_columns(table_name)
    print(f"\nColumns in '{table_name}' table:")
    for column in columns:
        print(f"- {column['name']} ({column['type']})")

if __name__ == "__main__":
    with app.app_context():
        check_table_columns('users')
        check_table_columns('appointments')
        check_table_columns('alerts')
