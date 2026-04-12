import requests
import json

def test_health_analysis():
    url = "http://localhost:5000/api/health-analysis"
    payload = {
        "steps": 12000,
        "avg_heart_rate": 68.5,
        "sleep_hours": 7.5
    }
    headers = {
        "Content-Type": "application/json"
    }

    print(f"Testing {url} with payload: {payload}")
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Success!")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    test_health_analysis()
