import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.fallback_diet_engine import fallback_diet_engine

def test_fallback():
    print("Testing Fallback Diet Engine...")
    
    # Mock input data (e.g., Anemia and Diabetes)
    mock_params = {
        "Hemoglobin": {"value": 8.5, "status": "Low", "unit": "g/dL"},
        "HbA1c": {"value": 7.2, "status": "High", "unit": "%"}
    }
    
    # Mock raw text mentioning hypertension
    mock_text = "Patient shows symptoms of hypertension and protein deficiency."
    
    print("\n[INPUT] Parameters:", list(mock_params.keys()))
    print("[INPUT] Text:", mock_text)
    
    result = fallback_diet_engine(mock_params, raw_text=mock_text)
    
    print("\n" + "="*50)
    print("FALLBACK ENGINE RESULTS")
    print("="*50)
    print(f"Issues Detected: {result['issues_detected']}")
    print(f"Recommended Foods (Scored): {result['recommended_foods'][:5]}")
    print(f"Foods to Avoid: {result['foods_to_avoid'][:5]}")
    print("\nMeal Plan (Breakfast):", result['meal_plan']['breakfast'])
    print("\nParameter Reasoning:")
    for param, reason in result['parameter_reasoning'].items():
        print(f"  - {param}: {reason}")
    print("\nSummary:", result['summary'])
    print("="*50)

if __name__ == "__main__":
    test_fallback()
