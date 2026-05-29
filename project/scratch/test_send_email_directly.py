import sys
import os

# Ensure repo root is on sys.path
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from backend.services.email_service import EmailService

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

def test():
    patient_email = "anvay.18077@sakec.ac.in"
    meeting_link = "https://us04web.zoom.us/j/78882622709?pwd=ch1IWpJmi3fD4GeIKFHbLhhrnrbRAu.1"
    print("Calling EmailService.send_appointment_email directly...")
    success = EmailService.send_appointment_email(patient_email, meeting_link)
    print(f"Result: {success}")

if __name__ == "__main__":
    test()
