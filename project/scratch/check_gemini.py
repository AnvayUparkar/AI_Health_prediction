
import os
from dotenv import load_dotenv

# Load .env
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
load_dotenv(dotenv_path=env_path)

print(f"DEBUG | GEMINI_API_KEY from env: {os.environ.get('GEMINI_API_KEY')[:10]}...")

try:
    import google.generativeai as genai
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("FAIL | GEMINI_API_KEY not found in environment!")
    else:
        genai.configure(api_key=api_key)
        # Try a model list call to verify connectivity/key
        models = genai.list_models()
        print("OK | Successfully connected to Gemini API. Listing some models:")
        for i, m in enumerate(models):
            print(f"  - {m.name}")
            if i > 5: break
except Exception as e:
    print(f"FAIL | Gemini check failed: {e}")
