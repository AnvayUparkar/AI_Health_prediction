import os
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from dotenv import load_dotenv

load_dotenv()

def test_sdk_email():
    api_key = os.environ.get('BREVO_API_KEY')
    if not api_key:
        print("No API Key")
        return

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = api_key

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    
    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": "anvay.18077@sakec.ac.in"}],
        html_content="<h3>Test from SDK</h3>",
        subject="SDK Test",
        sender={"name": "NeuroCare AI", "email": "no-reply@neurocare-ai.com"}
    )

    try:
        api_response = api_instance.send_transac_email(send_smtp_email)
        print(f"Success! Message ID: {api_response.message_id}")
    except ApiException as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_sdk_email()
