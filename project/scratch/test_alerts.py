import requests
import json
import time

BASE_URL = "http://localhost:5000/api"

def test_alert_data():
    print("\n1. Testing Alert Data (Critical Fall)...")
    payload = {
        "patient_id": "P001",
        "room_number": "101",
        "fall_detected": True,
        "movement": "none",
        "posture": "lying",
        "eye_state": "closed",
        "activity_duration": 10,
        "distress": False
    }
    response = requests.post(f"{BASE_URL}/alert/data", json=payload)
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    return response.json().get('id')

def test_warning_data():
    print("\n2. Testing Alert Data (Warning Inactivity)...")
    payload = {
        "patient_id": "P002",
        "room_number": "102",
        "fall_detected": False,
        "movement": "none",
        "posture": "sitting",
        "eye_state": "open",
        "activity_duration": 120,
        "distress": False
    }
    response = requests.post(f"{BASE_URL}/alert/data", json=payload)
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))

def test_get_alerts():
    print("\n3. Testing Get Alerts...")
    response = requests.get(f"{BASE_URL}/alerts")
    print(f"Status: {response.status_code}")
    print(f"Found {len(response.json())} alerts.")

def test_patch_alert(alert_id):
    if not alert_id:
        print("Skipping patch test, no ID.")
        return
    print(f"\n4. Testing Patch Alert {alert_id}...")
    payload = {"acknowledged": True}
    response = requests.patch(f"{BASE_URL}/alerts/{alert_id}", json=payload)
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    try:
        # Check if server is up
        requests.get("http://localhost:5000/health")
        alert_id = test_alert_data()
        test_warning_data()
        test_get_alerts()
        test_patch_alert(alert_id)
    except Exception as e:
        print(f"Error: {e}")
        print("Is the Flask server running?")
