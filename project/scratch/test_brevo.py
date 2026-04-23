import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get('BREVO_API_KEY')
patient_email = "anvay18077@gmail.com" # Just a guess or placeholder, I'll use the user's email if I know it.
# Wait, I don't know the user's email. I'll just use a dummy one or let the script fail with the error.

def test_email():
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "api-key": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "sender": {
            "name": "Health App",
            "email": "no-reply@yourapp.com"
        },
        "to": [{"email": "test@example.com"}],
        "subject": "Test Email",
        "htmlContent": "<h3>Test</h3>"
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if not api_key:
        print("No API Key")
    else:
        test_email()
