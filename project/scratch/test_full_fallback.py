import sys
import os
import logging

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Disable Gemini API by removing key or setting it to invalid
os.environ["GEMINI_API_KEY"] = "INVALID_KEY_TO_TRIGGER_FALLBACK"

from backend.gemini_diet_planner import generate_diet_plan_with_gemini

# Configure logging to see the fallback logs
logging.basicConfig(level=logging.INFO)

def test_full_pipeline_fallback():
    print("Testing Full Pipeline Fallback...")
    
    mock_params = {
        "Hemoglobin": {"value": 8.5, "status": "Low", "unit": "g/dL"},
        "HbA1c": {"value": 7.2, "status": "High", "unit": "%"}
    }
    mock_text = "Detection of high cholesterol in history."
    
    result = generate_diet_plan_with_gemini(
        mock_params,
        raw_text=mock_text,
        fallback_to_rules=True
    )
    
    print("\n" + "="*50)
    print("FULL PIPELINE RESULT")
    print("="*50)
    print(f"Source: {result['source']}")
    print(f"Plan Summary: {result['diet_plan']['summary']}")
    print(f"Issues Detected: {result['diet_plan']['issues_detected']}")
    print(f"Reasoning for high cholesterol: {result['diet_plan']['parameter_reasoning'].get('High_Cholesterol', 'Not Found')}")
    print("="*50)

if __name__ == "__main__":
    test_full_pipeline_fallback()
