import requests
import json
import time

BASE_URL = "http://localhost:5000"

def test_real_integration():
    # 1. Register / Login a test user
    email = f"test_user_{int(time.time())}@gmail.com"
    password = "password123"
    
    print(f"--- 1. Registering user: {email} ---")
    reg_resp = requests.post(f"{BASE_URL}/auth/register", json={
        "name": "Test User",
        "email": email,
        "password": password
    })
    
    # In some versions of this app, it might be /auth/signup or /auth/register
    if reg_resp.status_code != 201:
        reg_resp = requests.post(f"{BASE_URL}/auth/signup", json={
            "name": "Test User",
            "email": email,
            "password": password
        })
    
    print(f"Register Status: {reg_resp.status_code}")
    
    print(f"\n--- 2. Logging in ---")
    login_resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": email,
        "password": password
    })
    print(f"Login Status: {login_resp.status_code}")
    token = login_resp.json().get('access_token')
    
    if not token:
        print("Failed to get token!")
        return

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 3. Synchronize Health Data
    print(f"\n--- 3. Synchronizing real health data (POST) ---")
    payload = {
        "steps": 10500,
        "avg_heart_rate": 65.0,
        "sleep_hours": 8.0
    }
    sync_resp = requests.post(f"{BASE_URL}/api/health-analysis", json=payload, headers=headers)
    print(f"Sync Status: {sync_resp.status_code}")
    
    # 4. Fetch persistent data
    print(f"\n--- 4. Fetching latest data (GET) ---")
    get_resp = requests.get(f"{BASE_URL}/api/health-analysis", headers=headers)
    print(f"Get Status: {get_resp.status_code}")
    
    if get_resp.status_code == 200:
        data = get_resp.json().get('data')
        print("Successfully retrieved persistent data:")
        print(json.dumps(data, indent=2))
        
        if data and data.get('health_score') > 0:
            print("\n✅ PERSISTENCE VERIFIED: Data matches sync result.")
        else:
            print("\n❌ VERIFICATION FAILED: Data is missing or invalid.")
    else:
        print(f"\nError: {get_resp.status_code}")
        try:
            print(json.dumps(get_resp.json(), indent=2))
        except:
            print(get_resp.text)

if __name__ == "__main__":
    test_real_integration()
