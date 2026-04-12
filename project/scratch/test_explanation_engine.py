import sys
import os
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.fallback_diet_engine import fallback_diet_engine

def test_explanation_engine():
    # Mock data with multiple conditions to test hierarchical matching
    mock_input = {
        "Hemoglobin": {"value": "9.5", "status": "Low", "unit": "g/dL", "ref_range": "12.0 - 16.0"},
        "HbA1c": {"value": "7.8", "status": "High", "unit": "%", "ref_range": "4.0 - 5.6"},
        "SGPT": {"value": "95", "status": "High", "unit": "U/L", "ref_range": "0 - 40"}
    }
    
    # Raw text
    raw_text = "Patient reports high blood pressure and recent joint pain."
    
    print("Testing Fallback Engine with Explanation Logic...")
    print("=" * 60)
    
    result = fallback_diet_engine(mock_input, raw_text=raw_text)
    
    print(f"Summary: {result['summary']}")
    print("\nIssues Detected:")
    for issue in result['issues_detected']:
        print(f" - {issue}")
        
    print("\nDetailed Analysis:")
    for analysis in result['detailed_analysis']:
        print(f" - {analysis}")
        
    print("\nRecommended Foods (with reasoning):")
    for food in result['recommended_foods']:
        print(f" - {food}")
        
    print("\nFoods to Avoid (with reasoning):")
    for food in result['foods_to_avoid']:
        print(f" - {food}")

    print("\n" + "=" * 60)
    print("Verification successful!")

if __name__ == "__main__":
    test_explanation_engine()
