import requests
import json

def test_booking():
    url = "http://localhost:5000/api/appointments"
    payload = {
        "name": "John Doe Test",
        "email": "anvay.18077@sakec.ac.in",
        "phone": "9876543210",
        "mode": "online",
        "date": "2026-06-01",
        "time": "10:30",
        "reason": "Routine neuro checkup",
        "doctor_id": 1,
        "patient_id": 1
    }
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error during request: {e}")

if __name__ == "__main__":
    test_booking()
