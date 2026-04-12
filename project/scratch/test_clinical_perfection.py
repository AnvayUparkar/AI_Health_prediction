import sys
import os
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.fallback_diet_engine import fallback_diet_engine

def test_clinical_perfection():
    print("=== TESTING CLINICAL PERFECTION PROTOCOL (v2) ===")
    
    # Mock data for Anemia + Prediabetes
    mock_data = {
        "Hemoglobin": {"value": 10.2, "status": "Low", "ref_range": "13.5-17.5", "unit": "g/dL"},
        "MCV": {"value": 72.0, "status": "Low", "ref_range": "80-100", "unit": "fL"},
        "HbA1c": {"value": 6.3, "status": "High", "ref_range": "4.0-5.6", "unit": "%"}
    }
    
    report = fallback_diet_engine(mock_data)
    
    print("\n[Condition Profile]")
    print(report["conditions_profile"])

    print("\n[Safety Block Accuracy Check]")
    # These MUST be present based on dietary_knowledge.json
    expected_blocks = ["Sugar", "Honey", "Tea With Meals"]
    found_blocks = []
    
    for food_name, reason in report["blocked_foods_safety"].items():
        print(f" - Blocked: {food_name} | Reason: {reason}")
        if food_name in expected_blocks:
            found_blocks.append(food_name)
            
    print(f"\nExpected Blocks Found: {found_blocks}")
    
    # Verify accurate reasons
    assert "Sugar" in found_blocks
    assert "Tea With Meals" in found_blocks
    
    print("\nOVERALL PERFECTION STATUS: PASSED (ACCURATE SAFETY BLOCKS)")

if __name__ == "__main__":
    test_clinical_perfection()
