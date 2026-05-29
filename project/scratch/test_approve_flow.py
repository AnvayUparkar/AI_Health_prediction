import requests
import json
import time

def test_approve_flow():
    base_url = "http://localhost:5000/api"
    
    # 1. Book an online appointment
    print("--- 1. BOOKING ONLINE APPOINTMENT ---")
    booking_payload = {
        "name": "Jane Doe Test Approval Flow",
        "email": "anvay.18077@sakec.ac.in",
        "phone": "9876543210",
        "mode": "online",
        "date": "2026-06-03",
        "time": "14:00",
        "reason": "Neurology checkup",
        "doctor_id": 1,
        "patient_id": 1
    }
    
    response = requests.post(f"{base_url}/appointments", json=booking_payload, timeout=15)
    print(f"Booking Status Code: {response.status_code}")
    booking_res = response.json()
    print(f"Booking Response: {booking_res}")
    
    if response.status_code != 201:
        print("Booking failed!")
        return
        
    apt_id = booking_res.get("appointment_id")
    
    # 2. Verify appointment details in pending status
    print("\n--- 2. VERIFYING DETAILS ---")
    response = requests.get(f"{base_url}/appointments/{apt_id}", timeout=10)
    apt_details = response.json()
    print(f"Current Status: {apt_details.get('status')}")
    
    # 3. Simulate doctor approval using the doctor's portal approve endpoint (POST /doctor_appointments/<id>/approve)
    print("\n--- 3. SIMULATING DOCTOR PORTAL APPROVAL ---")
    response = requests.post(f"{base_url}/doctor_appointments/{apt_id}/approve", timeout=15)
    print(f"Approval Status Code: {response.status_code}")
    print(f"Approval Response: {response.json()}")

if __name__ == "__main__":
    test_approve_flow()
