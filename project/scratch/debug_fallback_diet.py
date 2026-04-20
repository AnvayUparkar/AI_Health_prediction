
import os
import sys
import json
import logging

# Set up paths
project_root = r"c:\Users\Anvay Uparkar\Hackathon projects\AI_Health_prediction\project"
sys.path.append(project_root)

# Mock trends
trends = {
    'glucose': {'average': 160, 'trend': 'INCREASING'},
    'bp_systolic': {'average': 140, 'trend': 'STABLE'},
    'spo2': {'average': 94}
}

try:
    from backend.fallback_diet_engine import fallback_diet_engine
    from backend.fallback_monitoring_engine import _map_trends_to_diet_input
    
    # Map trends to a simulated lab report for the diet engine
    input_data, raw_text_pad = _map_trends_to_diet_input(trends, "LOW")
    print(f"DEBUG: input_data={input_data}")
    print(f"DEBUG: raw_text_pad={raw_text_pad}")
    
    # Generate diet
    diet_engine_result = fallback_diet_engine(input_data=input_data, raw_text=raw_text_pad)
    meal_plan = diet_engine_result.get("meal_plan", {})
    recommended_foods = diet_engine_result.get("recommended_foods", [])
    
    print(f"DEBUG: meal_plan keys: {list(meal_plan.keys())}")
    print(f"DEBUG: recommended_foods count: {len(recommended_foods)}")
    
    food_reasoning_map = {}
    for rec in recommended_foods:
        parts = rec.split(" — ")
        if len(parts) >= 2:
            food_reasoning_map[parts[0].strip().lower()] = parts[1].strip()

    print(f"DEBUG: food_reasoning_map count: {len(food_reasoning_map)}")

    def build_meal_with_reasoning(meal_key, default_items):
        items = meal_plan.get(meal_key, [])
        if not items:
            return {"items": default_items, "reasoning": "Standard clinical sustenance for recovery."}
        
        reasons = []
        for item in items:
            clean_name = item.replace(" (Synergy Booster)", "").strip().lower()
            if clean_name in food_reasoning_map:
                reasons.append(f"{clean_name.title()}: {food_reasoning_map[clean_name]}")
        
        reasoning_str = " ".join(reasons) if reasons else "Selected for optimal metabolic glycemic response."
        return {"items": items, "reasoning": reasoning_str}

    result = {
        "breakfast": build_meal_with_reasoning("breakfast", ["Oatmeal (Low GI)", "Lemon Water"]),
        "lunch": build_meal_with_reasoning("lunch", ["Brown Rice", "Lentil Soup"]),
        "snacks": build_meal_with_reasoning("snack", ["Roasted Makhana", "Buttermilk"]),
        "dinner": build_meal_with_reasoning("dinner", ["Multigrain Roti", "Vegetable Stew"]),
    }
    print("SUCCESS: Result generated")
    print(json.dumps(result, indent=2))

except Exception as e:
    import traceback
    traceback.print_exc()
