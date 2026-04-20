import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.fallback_diet_engine import fallback_diet_engine
import json

def test_deep_analysis():
    print("--- TESTING DEEP CLINICAL ANALYSIS (Rule-Based Fallback) ---")
    
    # Simulate a complex report with Liver, Kidney and Thyroid markers
    mock_report = {
        "GGT": {"value": "120", "status": "High", "unit": "U/L", "ref_range": "9-64"},
        "Creatinine": {"value": "2.1", "status": "High", "unit": "mg/dL", "ref_range": "0.6-1.2"},
        "TSH": {"value": "8.5", "status": "High", "unit": "uIU/mL", "ref_range": "0.4-4.0"},
        "Hemoglobin": {"value": "13.5", "status": "Normal", "unit": "g/dL"}
    }
    
    # Run engine
    result = fallback_diet_engine(mock_report)
    
    print(f"\nConditions Profile: {result['conditions_profile']}")
    print("\nIssues Detected:")
    for issue in result['issues_detected']:
        print(f"  - {issue}")
        
    print("\nMeal Plan Highlights:")
    for slot, data in result['meal_plan'].items():
        print(f"  [{slot.upper()}]: {', '.join(data['items'])}")
        print(f"     Reasoning: {data['reasoning']}")
        
    # Assertions (Checking for Technical Names)
    plan_str = str(result['meal_plan'])
    profile_str = str(result['conditions_profile']).lower()
    
    assert "liver" in profile_str
    assert "kidney" in profile_str
    assert "thyroid" in profile_str
    
    # Check for specific clinical food injections
    plan_str = str(result['meal_plan'])
    assert "Lemon Water" in plan_str # Liver detox
    assert "Bottle Gourd" in plan_str # Kidney support
    assert "Seaweed" in plan_str or "Brazil Nuts" in plan_str or "iodine" in plan_str # Thyroid support
    
    print("\nPASSED Verification: Deep clinical analysis is active.")

if __name__ == "__main__":
    test_deep_analysis()
