import requests
import json
import time

BASE_URL = "http://localhost:5000"

def test_full_report():
    # 1. Register / Login a test user
    email = f"report_user_{int(time.time())}@gmail.com"
    password = "password123"
    
    print(f"--- 1. Registering user: {email} ---")
    reg_resp = requests.post(f"{BASE_URL}/auth/signup", json={
        "name": "Report Tester",
        "email": email,
        "password": password
    })
    print(f"Register Status: {reg_resp.status_code}")
    
    print(f"\n--- 2. Logging in ---")
    login_resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": email,
        "password": password
    })
    token = login_resp.json().get('access_token')
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 3. Perform 3 syncs with different data
    metrics = [
        {"steps": 7000, "avg_heart_rate": 72.0, "sleep_hours": 6.5},
        {"steps": 12000, "avg_heart_rate": 68.0, "sleep_hours": 7.5},
        {"steps": 9500, "avg_heart_rate": 70.0, "sleep_hours": 8.0}
    ]

    for i, m in enumerate(metrics):
        print(f"\n--- 3.{i+1} Syncing health data: {m} ---")
        sync_resp = requests.post(f"{BASE_URL}/api/health-analysis", json=m, headers=headers)
        print(f"Sync Status: {sync_resp.status_code}")
        time.sleep(1) # Ensure separate timestamps

    # 4. Fetch historical report
    print(f"\n--- 4. Fetching weekly report (GET /api/health-report) ---")
    report_resp = requests.get(f"{BASE_URL}/api/health-report", headers=headers)
    print(f"Report Status: {report_resp.status_code}")
    
    if report_resp.status_code == 200:
        result = report_resp.json()
        data = result.get('data')
        print(f"Retrieved {result.get('count')} records.")
        
        for entry in data:
            print(f"- Date: {entry['created_at']}, Steps: {entry['metrics']['steps']}, Score: {entry['health_score']}")
            
        if result.get('count') == 3:
            print("\n✅ WEEKLY REPORT VERIFIED: Multiple entries with metrics retrieved successfully.")
        else:
            print(f"\n❌ VERIFICATION FAILED: Expected 3 records, got {result.get('count')}")
    else:
        print(f"\n❌ Error: {report_resp.text}")

if __name__ == "__main__":
    test_full_report()
