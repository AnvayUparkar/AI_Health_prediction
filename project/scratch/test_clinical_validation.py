import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.fallback_diet_engine import fallback_diet_engine

def run_test_case(name, input_data, raw_text=None):
    print(f"\n{'='*60}")
    print(f"TEST CASE: {name}")
    print(f"{'='*60}")
    
    result = fallback_diet_engine(input_data, raw_text)
    
    print("\nISSUES DETECTED:")
    for issue in result['issues_detected']:
        print(f"  - {issue}")
        
    print("\nRECOMMENDED FOODS:")
    for food in result['recommended_foods']:
        print(f"  + {food}")
        
    print("\nFOODS TO AVOID:")
    for food in result['foods_to_avoid']:
        print(f"  ! {food}")
    
    return result

# 1. Test Strict Anemia (Hb Low, MCV Normal -> Should NOT detect)
test_hblo_mcvnorm = {
    "Hemoglobin": {"value": "10.5", "unit": "g/dL", "status": "Low", "ref_range": "12.0-16.0"},
    "MCV": {"value": "88", "unit": "fL", "status": "Normal", "ref_range": "80-100"}
}
run_test_case("Strict Anemia Check (Hb Low, MCV Normal)", test_hblo_mcvnorm)

# 2. Test Conflict Resolution (Anemia vs Kidney Strain)
# Anemia wants Spinach (Iron). Kidney Strain avoids Spinach (High Potassium/Oxalate).
# RESULT: Spinach should NOT be in Recommended.
test_conflict = {
    "Hemoglobin": {"value": "10.1", "unit": "g/dL", "status": "Low", "ref_range": "12.0-16.0"},
    "MCV": {"value": "75", "unit": "fL", "status": "Low", "ref_range": "80-100"},
    "Creatinine": {"value": "2.1", "unit": "mg/dL", "status": "High", "ref_range": "0.6-1.2"},
    "Sodium": {"value": "135", "unit": "mEq/L", "status": "Normal", "ref_range": "136-145"}
}
res_conflict = run_test_case("Conflict Resolution (Anemia + Kidney Strain)", test_conflict)
recommended_lower = [f.lower() for f in res_conflict['recommended_foods']]
if any("spinach" in f for f in recommended_lower):
    print("\n[FAIL] Spinach found in Recommended despite Kidney Strain!")
else:
    print("\n[PASS] Spinach correctly excluded due to Kidney conflict.")

# 3. Test Deduplication (Hyperlipidemia + Hypertriglyceridemia)
test_dedup = {
    "Total Cholesterol": {"value": "240", "unit": "mg/dL", "status": "High", "ref_range": "0-200"},
    "Triglycerides": {"value": "190", "unit": "mg/dL", "status": "High", "ref_range": "0-150"}
}
res_dedup = run_test_case("Deduplication (Lipid vs Triglyceride)", test_dedup)
if any("Hyperlipidemia" in s for s in res_dedup['issues_detected']) and any("Hypertriglyceridemia" in s for s in res_dedup['issues_detected']):
    print("\n[FAIL] Both conditions present. Deduplication failed.")
elif any("Hypertriglyceridemia" in s for s in res_dedup['issues_detected']):
    print("\n[PASS] Only specific condition (Hypertriglyceridemia) kept.")

# 4. Test Prediabetes (Borderline HbA1c)
test_prediabetes = {
    "HbA1c": {"value": "5.9", "unit": "%", "status": "High", "ref_range": "4.0-5.7"}
}
run_test_case("Prediabetes Validation (HbA1c 5.9)", test_prediabetes)
