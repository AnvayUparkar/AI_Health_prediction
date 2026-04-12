from app import create_app
from backend.models import db, HealthAnalysis
import sys

app = create_app()
with app.app_context():
    # Targeted wipe for the current session's issues
    count = HealthAnalysis.query.filter(HealthAnalysis.user_id == 1).delete()
    db.session.commit()
    print(f"Purged {count} records. Ready for clean sync.")
