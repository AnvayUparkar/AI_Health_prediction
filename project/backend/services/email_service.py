import os
import requests
import time

class EmailService:
    """Service to interact with Brevo (Sendinblue) API for emails"""

    @staticmethod
    def send_appointment_email(patient_email, meeting_link, retries=2):
        """
        Sends an appointment confirmation email containing the Zoom link.
        Uses exponential backoff for retries internally.
        """
        api_key = os.environ.get('BREVO_API_KEY')
        if not api_key:
            print("[EmailService] Warning: BREVO_API_KEY missing in .env")
            return False

        url = "https://api.brevo.com/v3/smtp/email"
        headers = {
            "api-key": api_key,
            "Content-Type": "application/json"
        }

        html_content = f"""
        <h3>Appointment Confirmed</h3>
        <p>Your online consultation has been scheduled.</p>
        <p><b>Join Meeting:</b> <a href='{meeting_link}'>Click here</a></p>
        <p>Please join 5 minutes before the scheduled time.</p>
        """

        payload = {
            "sender": {
                "name": "Health App",
                "email": "no-reply@yourapp.com"
            },
            "to": [
                {
                    "email": patient_email
                }
            ],
            "subject": "Your Online Doctor Appointment Confirmation",
            "htmlContent": html_content
        }

        for attempt in range(retries + 1):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=10)
                response.raise_for_status()
                print(f"[EmailService] Email sent successfully to {patient_email}")
                return True
            except requests.exceptions.RequestException as e:
                print(f"[EmailService] Failed to send email (Attempt {attempt+1}/{retries+1}): {e}")
                if attempt < retries:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    return False
