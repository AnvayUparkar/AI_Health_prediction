import os
import sys
import json
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.join(os.getcwd(), 'project'))

from app import create_app
from backend.models import db, HealthAnalysis

def populate_weekly_data():
    app = create_app()
    with app.app_context():
        user_id = 1
        base_date = datetime.utcnow()
        
        # Add 5 records for the previous 5 days
        for i in range(5, 0, -1):
            created_at = base_date - timedelta(days=i)
            # Use deterministic but varying metrics
            steps = 5000 + (i * 1200)
            score = 70 + (i * 4)
            
            analysis = HealthAnalysis(
                user_id=user_id,
                health_score=score,
                risk_level='Low',
                health_status='Good',
                steps=steps,
                avg_heart_rate=70.0 + (i * 0.5),
                sleep_hours=6.0 + (i * 0.3),
                diet_plan=json.dumps(["Protein rich diet", "Green vegetables", "Low carb"]),
                recommendations=json.dumps(["Walk 10k steps", "Hydrate more"]),
                created_at=created_at
            )
            db.session.add(analysis)
            print(f"Adding record for {created_at.strftime('%A')} ({created_at.date()}) with {steps} steps")
            
        db.session.commit()
        print("Successfully populated 5 historical records.")

if __name__ == "__main__":
    populate_weekly_data()
