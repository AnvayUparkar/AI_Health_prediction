import os
import requests
import base64
import time

class ZoomService:
    """Service to interact with Zoom API for online consultations"""

    @staticmethod
    def get_access_token():
        """Fetch the OAuth access token for Server-to-Server OAuth"""
        account_id = os.environ.get('ZOOM_ACCOUNT_ID')
        client_id = os.environ.get('ZOOM_CLIENT_ID')
        client_secret = os.environ.get('ZOOM_CLIENT_SECRET')

        if not all([account_id, client_id, client_secret]):
            print("[ZoomService] Warning: Missing Zoom API credentials in .env")
            return None

        url = f"https://zoom.us/oauth/token?grant_type=account_credentials&account_id={account_id}"
        auth_str = f"{client_id}:{client_secret}"
        b64_auth_str = base64.b64encode(auth_str.encode('ascii')).decode('ascii')
        
        headers = {
            "Authorization": f"Basic {b64_auth_str}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        try:
            response = requests.post(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json().get('access_token')
        except requests.exceptions.RequestException as e:
            print(f"[ZoomService] Failed to obtain access token: {e}")
            return None

    @staticmethod
    def create_zoom_meeting(patient_name, appointment_time, retries=2):
        """
        Create a Zoom meeting. Retries up to `retries` times if network/API failure occurs.
        """
        # Note: 'me' is a special userId in Zoom API denoting the authenticated user 
        # (or the main account admin in Server-to-Server).
        api_url = "https://api.zoom.us/v2/users/me/meetings"
        
        payload = {
            "topic": f"Doctor Consultation with {patient_name}",
            "type": 2, # Scheduled Meeting
            "start_time": f"{appointment_time}:00Z" if 'T' in appointment_time else appointment_time, # Basic formatting fallback
            "duration": 30,
            "timezone": "Asia/Kolkata",
            "agenda": "Online Medical Consultation",
            "settings": {
                "join_before_host": True,
                "waiting_room": False
            }
        }

        for attempt in range(retries + 1):
            token = ZoomService.get_access_token()
            if not token:
                print("[ZoomService] Unable to proceed without access token.")
                return None

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            try:
                response = requests.post(api_url, headers=headers, json=payload, timeout=15)
                response.raise_for_status()
                data = response.json()
                
                print(f"[ZoomService] Successfully created meeting {data.get('id')}")
                return {
                    "meeting_link": data.get("join_url"),
                    "meeting_id": str(data.get("id")),
                    "meeting_password": data.get("password")
                }

            except requests.exceptions.RequestException as e:
                print(f"[ZoomService] Creation failed (Attempt {attempt+1}/{retries+1}): {e}")
                if attempt < retries:
                    time.sleep(2 ** attempt) # Exponential backoff for retries
                else:
                    return None
