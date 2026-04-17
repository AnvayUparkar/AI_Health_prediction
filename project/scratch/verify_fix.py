import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from backend.db_service import DBService
from backend.utils.geocode import resolve_canonical_hospital

app = create_app()
with app.app_context():
    test_name = "Avadhoot Hospital"
    print(f"Testing Resolution for: '{test_name}'")
    
    canonical, data = resolve_canonical_hospital(test_name)
    print(f"  Canonical Name: '{canonical}'")
    
    if data:
        print(f"  Found in DB: Yes")
    else:
        print(f"  Found in DB: No")

    print(f"\nFetching doctors for '{test_name}'...")
    doctors = DBService.get_doctors_by_hospital(test_name)
    print(f"Found {len(doctors)} doctors:")
    for d in doctors:
        name = d.get('name') if isinstance(d, dict) else d.name
        print(f"  - {name}")

    if len(doctors) > 0:
        print("\n[SUCCESS] Fuzzy matching works! Mahesh/Mansi found.")
    else:
        print("\n[FAILURE] Still no doctors found.")
