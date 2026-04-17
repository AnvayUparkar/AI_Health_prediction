import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.utils.geocode import search_nearby_hospitals_osm, geocode_hospital

def test_location(name, lat, lon):
    print(f"\n{'='*60}")
    print(f"TESTING: {name} ({lat}, {lon})")
    print(f"{'='*60}")
    
    # Test nearby search (Overpass)
    results = search_nearby_hospitals_osm(lat, lon, radius_km=15)
    print(f"Nearby Results: {len(results)}")
    for r in results[:3]:
        print(f"  - {r['name']} ({r['distance']}km) | Source: {r['source']}")

    if not results:
        print("  [!] No hospitals found.")

# Common global test points
LOCATIONS = [
    ("New York City, USA", 40.7128, -74.0060),
    ("London, UK", 51.5074, -0.1278),
    ("Tokyo, Japan", 35.6895, 139.6917),
    ("Airoli, Navi Mumbai, India", 19.1590, 72.9985),
]

for name, lat, lon in LOCATIONS:
    test_location(name, lat, lon)
