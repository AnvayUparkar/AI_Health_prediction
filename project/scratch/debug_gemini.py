"""
Reproduce the exact call made inside the Flask app to debug why
"Gemini API unavailable" is shown even though the key works.
"""
import os
import sys
# Add project root to path so 'backend' module resolves
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

print(f"Key loaded: {bool(os.environ.get('GEMINI_API_KEY'))}")

# Simulate the _call_gemini call directly
try:
    import google.generativeai as genai
    api_key = os.environ.get("GEMINI_API_KEY")
    genai.configure(api_key=api_key)

    config_with_mime = {
        "temperature": 0.3,
        "top_p": 0.85,
        "top_k": 40,
        "max_output_tokens": 512,
        "response_mime_type": "application/json",
    }
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        generation_config=config_with_mime,
    )
    response = model.generate_content("Return: {\"test\": true}")
    print(f"SUCCESS: {response.text[:200]}")

except RuntimeError as e:
    print(f"RuntimeError caught: {type(e).__name__}: {e}")
except Exception as e:
    print(f"NON-RuntimeError caught: {type(e).__name__}: {e}")
    print("^ This is the problem - the except RuntimeError block in gemini_diet_planner.py MISSES this!")
