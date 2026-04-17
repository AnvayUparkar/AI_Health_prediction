"""
Geocoding utility for precise hospital coordinates.
Uses OpenStreetMap Nominatim (free, no API key needed).
"""
import urllib.request
import urllib.parse
import json
import math


def _haversine_km(lat1, lon1, lat2, lon2):
    """Quick haversine distance in km."""
    R = 6371
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = (math.sin(dLat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dLon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def geocode_hospital(name: str, fallback_lat: float = None, fallback_lon: float = None,
                     city: str = None, max_distance_km: float = 50.0):
    """
    Geocode a hospital name using OpenStreetMap Nominatim.
    Returns (latitude, longitude) tuple.
    """
    # Build search queries
    search_queries = []
    if city:
        search_queries.append(f"{name} {city}")
    
    # Generic global search
    search_queries.extend([
        f"{name} hospital",
        name,
    ])

    for query in search_queries:
        try:
            params = {
                "q": query, 
                "format": "json", 
                "limit": 5, 
            }
            
            # If we have fallback coords, focus the search around them (within ~50km)
            if fallback_lat is not None and fallback_lon is not None:
                delta = 0.5 # ~50km
                params["viewbox"] = f"{fallback_lon-delta},{fallback_lat+delta},{fallback_lon+delta},{fallback_lat-delta}"
                params["bounded"] = 1

            url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(url, headers={"User-Agent": "HealthApp/2.0"})
            res = urllib.request.urlopen(req, timeout=5)
            data = json.loads(res.read())

            if not data:
                continue

            # Pick the absolute closest match to our fallback coordinates
            if fallback_lat is not None and fallback_lon is not None:
                best = None
                best_dist = float("inf")
                for item in data:
                    lat = float(item["lat"])
                    lon = float(item["lon"])
                    dist = _haversine_km(fallback_lat, fallback_lon, lat, lon)
                    if dist < best_dist:
                        best_dist = dist
                        best = item

                if best and best_dist <= max_distance_km:
                    lat = float(best["lat"])
                    lon = float(best["lon"])
                    osm_name = best.get("display_name", "")[:80]
                    try:
                        print(f"  [GEOCODE] Resolved '{name}' -> ({lat}, {lon}) [{best_dist:.2f}km from origin] | {osm_name}")
                    except UnicodeEncodeError:
                        print(f"  [GEOCODE] Resolved '{name}' -> ({lat}, {lon})")
                    return lat, lon
            else:
                # No fallback — use first result
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                osm_name = data[0].get("display_name", "")[:80]
                try:
                    print(f"  [GEOCODE] Resolved '{name}' -> ({lat}, {lon}) | {osm_name}")
                except UnicodeEncodeError:
                    print(f"  [GEOCODE] Resolved '{name}' -> ({lat}, {lon})")
                return lat, lon

        except Exception as e:
            print(f"  [GEOCODE] Query '{query}' failed: {e}")
            continue

    if fallback_lat is not None:
        print(f"  [GEOCODE] '{name}' -> all queries failed, using fallback.")
    return fallback_lat, fallback_lon


def search_nearby_hospitals_osm(lat: float, lon: float, radius_km: float = 25.0):
    """
    Search for real hospitals near a location using Overpass API.
    Provides much higher precision and better results than Nominatim for amenities.
    """
    # Overpass endpoint
    url = "https://overpass-api.de/api/interpreter"
    
    # Radius in meters for Overpass
    radius_m = radius_km * 1000
    
    # Overpass QL query: find node/way/relation with amenity=hospital|clinic|doctors
    query = f"""
    [out:json][timeout:25];
    (
      node["amenity"~"hospital|clinic|doctors"](around:{radius_m},{lat},{lon});
      way["amenity"~"hospital|clinic|doctors"](around:{radius_m},{lat},{lon});
      relation["amenity"~"hospital|clinic|doctors"](around:{radius_m},{lat},{lon});
    );
    out center;
    """
    
    try:
        data_bytes = query.encode('utf-8')
        req = urllib.request.Request(url, data=data_bytes, headers={"User-Agent": "HealthApp/2.0"})
        res = urllib.request.urlopen(req, timeout=15)
        raw_data = json.loads(res.read())
        
        if not raw_data or 'elements' not in raw_data:
            return []

        hospitals = []
        for el in raw_data['elements']:
            h_lat = el.get('lat') or (el.get('center', {}).get('lat') if 'center' in el else None)
            h_lon = el.get('lon') or (el.get('center', {}).get('lon') if 'center' in el else None)
            
            if h_lat is None or h_lon is None:
                continue
                
            tags = el.get('tags', {})
            name = tags.get('name') or tags.get('operator') or f"Unnamed {tags.get('amenity', 'Medical Facility')}"
            
            dist = round(_haversine_km(lat, lon, h_lat, h_lon), 2)
            
            hospitals.append({
                "name": name,
                "latitude": h_lat,
                "longitude": h_lon,
                "distance": dist,
                "source": "osm_overpass",
                "capacity": 0,
                "type": tags.get('amenity', 'hospital')
            })

        # Sort: Nearest first
        hospitals.sort(key=lambda x: x['distance'])
        
        try:
            print(f"  [OVERPASS] Found {len(hospitals)} facilities within {radius_km}km of ({lat}, {lon})")
        except UnicodeEncodeError:
            pass

        return hospitals

    except Exception as e:
        print(f"  [OVERPASS] API call failed: {e}")
        # Fallback to a very basic Nominatim search if Overpass is down
        return _search_nearby_nominatim_fallback(lat, lon, radius_km)


def _search_nearby_nominatim_fallback(lat, lon, radius_km):
    """Emergency fallback if Overpass API is unavailable."""
    delta = radius_km / 111.0
    try:
        params = {
            "q": "hospital",
            "format": "json",
            "viewbox": f"{lon - delta},{lat + delta},{lon + delta},{lat - delta}",
            "bounded": 1,
        }
        url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "HealthApp/2.0"})
        res = urllib.request.urlopen(req, timeout=5)
        data = json.loads(res.read())
        
        results = []
        for item in data:
            h_lat, h_lon = float(item["lat"]), float(item["lon"])
            name = item.get("display_name", "Hospital").split(",")[0]
            results.append({
                "name": name,
                "latitude": h_lat,
                "longitude": h_lon,
                "distance": round(_haversine_km(lat, lon, h_lat, h_lon), 2),
                "source": "osm_nominatim_fallback"
            })
        return results
    except Exception:
        return []


def resolve_canonical_hospital(name: str, lat: float = None, lon: float = None):
    """
    Resolve a potentially slightly different hospital name (e.g. from OSM)
    to our internal canonical name and data.

    Returns (canonical_name, hospital_dict) or (Original Name, None)
    """
    from backend.models import Hospital
    import difflib

    # 1. Try exact/substring match first (case-insensitive)
    name_clean = name.lower().strip()
    hospitals = Hospital.query.all()

    # Exact or substring match
    for h in hospitals:
        h_name = h.name.lower()
        if name_clean in h_name or h_name in name_clean:
            return h.name, h.to_dict()

    # Fuzzy string match (high threshold)
    all_names = [h.name for h in hospitals]
    matches = difflib.get_close_matches(name, all_names, n=1, cutoff=0.6)
    if matches:
        target_name = matches[0]
        for h in hospitals:
            if h.name == target_name:
                print(f"  [RESOLVER] Fuzzy string match: '{name}' -> '{h.name}'")
                return h.name, h.to_dict()

    # 2. Try location-based resolution (if coords provided)
    if lat is not None and lon is not None:
        best_match = None
        min_dist = float('inf')
        for h in hospitals:
            dist = _haversine_km(lat, lon, h.latitude, h.longitude)
            if dist < min_dist:
                min_dist = dist
                best_match = h

        # If it's within 500 meters, it's almost certainly the same facility
        if best_match and min_dist <= 0.5:
            print(f"  [RESOLVER] Location match: '{name}' -> '{best_match.name}' ({int(min_dist*1000)}m away)")
            return best_match.name, best_match.to_dict()

    return name, None

