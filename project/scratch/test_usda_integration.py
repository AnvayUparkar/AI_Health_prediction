import sys
import os
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.fallback_diet_engine import fallback_diet_engine

def test_usda_integration():
    print("=== TESTING USDA INTEGRATION ===")
    
    # Mock data for Iron Deficiency Anemia
    anemia_data = {
        "Hemoglobin": {"value": 10.5, "status": "Low", "ref_range": "13.5-17.5", "unit": "g/dL"},
        "MCV": {"value": 75.0, "status": "Low", "ref_range": "80-100", "unit": "fL"}
    }
    
    report = fallback_diet_engine(anemia_data)
    
    print("\n[Conditions Detected]")
    for issue in report["issues_detected"]:
        print(f" - {issue}")
        
    print("\n[Recommended Foods (Should contain USDA and Expert KB foods)]")
    for rec in report["recommended_foods"]:
        print(f" - {rec}")

    # Check for specific USDA foods that should be high in iron
    usda_found = any("USDA Foundation data" in rec for rec in report["recommended_foods"])
    print(f"\nUSDA Data Presence: {'PASSED' if usda_found else 'FAILED'}")

    # Test Safety Filter (Prediabetes + High Sugar)
    print("\n--- Testing Safety Filter (Prediabetes) ---")
    prediabetes_data = {
        "HbA1c": {"value": 6.2, "status": "High", "ref_range": "4.0-5.6", "unit": "%"}
    }
    report_pd = fallback_diet_engine(prediabetes_data)
    
    # Check if high sugar foods like "Honey" or "Medjool Dates" (if indexed) are rejected
    # In my USDA foundation index, "Dates" would be high sugar. 
    # Let's see what's in there.
    for rec in report_pd["recommended_foods"]:
        if "Dates" in rec or "Honey" in rec:
             print(f" - WARNING: High sugar food found in prediabetes recommendation: {rec}")
    
    print("Safety Filter Test: Check logs for 'USDA_SAFETY | Rejecting...' messages.")

if __name__ == "__main__":
    test_usda_integration()
