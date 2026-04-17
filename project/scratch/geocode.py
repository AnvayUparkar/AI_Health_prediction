import urllib.request, json

url = "https://nominatim.openstreetmap.org/search?q=Avadhoot+Hospital+Airoli&format=json&limit=3"
req = urllib.request.Request(url, headers={"User-Agent": "HealthApp/1.0"})
res = urllib.request.urlopen(req)
data = json.loads(res.read())

if data:
    for r in data:
        name = r.get("display_name", "?")[:100]
        print(f"name: {name}")
        print(f"lat: {r['lat']}, lon: {r['lon']}")
        print()
else:
    print("No results found")
