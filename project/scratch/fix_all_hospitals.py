"""Restore hospital coordinates to known-good values, then re-verify with improved geocoder."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from backend.models import db, Hospital
from backend.utils.geocode import geocode_hospital

# Known-good approximate coordinates (close enough for the geocoder's 50km radius)
KNOWN_COORDS = {
    "Avdhoot Hospital":       (19.1597689, 72.9925981),
    "Shatabdi Hospital":      (19.0496, 72.915),
    "City Medical Center":    (18.53, 73.86),
    "General Wellness Clinic": (18.51, 73.84),
}

app = create_app()
with app.app_context():
    hospitals = Hospital.query.all()
    print(f"Fixing {len(hospitals)} hospitals...\n")

    for h in hospitals:
        known = KNOWN_COORDS.get(h.name)
        if known:
            # Restore to known-good first
            h.latitude, h.longitude = known

        # Now geocode with distance validation
        lat, lon = geocode_hospital(h.name, h.latitude, h.longitude)
        if lat is not None and lon is not None:
            h.latitude = lat
            h.longitude = lon
        
        print(f"  FINAL: {h.name} -> ({h.latitude}, {h.longitude})\n")
        time.sleep(1.1)

    db.session.commit()
    print("All hospitals fixed and saved.")
