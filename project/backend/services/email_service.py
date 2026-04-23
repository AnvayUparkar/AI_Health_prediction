import os
import time
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

class EmailService:
    """Service to interact with Brevo (Sendinblue) API for emails using official SDK"""

    @staticmethod
    def send_appointment_email(patient_email, meeting_link, retries=2):
        """
        Sends an appointment confirmation email containing the Zoom link.
        Uses the official Brevo SDK with exponential backoff for retries.
        """
        print(f"[EmailService] Attempting to send email to {patient_email}")
        
        api_key = os.environ.get('BREVO_API_KEY')
        if not api_key:
            print("[EmailService] Warning: BREVO_API_KEY missing in .env")
            return False

        # Configure API key authorization
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = api_key

        # Create an instance of the API class
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 10px;">
            <h2 style="color: #2c3e50;">Appointment Confirmed</h2>
            <p>Hello,</p>
            <p>Your online consultation with <strong>NeuroCare AI</strong> has been successfully scheduled.</p>
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p style="margin: 0;"><strong>Join Zoom Meeting:</strong></p>
                <p style="margin: 10px 0;"><a href='{meeting_link}' style="display: inline-block; padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px;">Join Meeting Now</a></p>
            </div>
            <p>Please ensure you have a stable internet connection and join 5 minutes before the scheduled time.</p>
            <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
            <p style="font-size: 12px; color: #7f8c8d;">This is an automated message from NeuroCare AI. Please do not reply to this email.</p>
        </div>
        """

        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": patient_email}],
            html_content=html_content,
            subject="Your Online Doctor Appointment Confirmation - NeuroCare AI",
            sender={"name": "NeuroCare AI", "email": "no-reply@neurocare-ai.com"}
        )

        for attempt in range(retries + 1):
            try:
                api_response = api_instance.send_transac_email(send_smtp_email)
                print(f"[EmailService] Email sent successfully to {patient_email}. Message ID: {api_response.message_id}")
                return True
            except ApiException as e:
                print(f"[EmailService] Failed to send email (Attempt {attempt+1}/{retries+1}): {e}")
                if attempt < retries:
                    time.sleep(2 ** attempt)
                else:
                    return False
            except Exception as e:
                print(f"[EmailService] Unexpected error sending email: {e}")
                return False
