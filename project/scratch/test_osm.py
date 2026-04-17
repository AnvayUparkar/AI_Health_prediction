import sys
sys.path.insert(0, ".")
from backend.utils.geocode import search_nearby_hospitals_osm

# Test 1: New York City, USA (should find real hospitals)
print("=== TEST: NYC, USA ===")
results = search_nearby_hospitals_osm(40.7128, -74.0060, 25)
print(f"Found {len(results)} hospitals\n")
for h in results[:3]:
    print(f"  {h['name']}: {h['distance']}km")

# Test 2: London, UK
print("\n=== TEST: London, UK ===")
results = search_nearby_hospitals_osm(51.5074, -0.1278, 10)
print(f"Found {len(results)} hospitals\n")
for h in results[:3]:
    print(f"  {h['name']}: {h['distance']}km")

# Test 3: Tokyo, Japan
print("\n=== TEST: Tokyo, Japan ===")
results = search_nearby_hospitals_osm(35.6762, 139.6503, 10)
print(f"Found {len(results)} hospitals\n")
for h in results[:3]:
    print(f"  {h['name']}: {h['distance']}km")
