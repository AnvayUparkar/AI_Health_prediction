import json
import os

KB_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", "data", "dietary_knowledge.json")

def update_kb():
    with open(KB_FILE, 'r') as f:
        data = json.load(f)
        
    # Add new conditions for vital signs tracking
    data["condition_nutrients"]["hypoxia"] = ["iron", "vitamin_c", "antioxidants"]
    data["condition_nutrients"]["hyperglycemia"] = ["fiber", "low_glycemic", "protein"]
    data["condition_nutrients"]["hypoglycemia"] = ["complex_carbs", "protein"]
    data["condition_nutrients"]["hypertension"] = ["potassium", "magnesium", "low_sodium"]
    data["condition_nutrients"]["hypotension"] = ["sodium", "hydration", "vitamin_b12"]

    # Add avoidance rules for new conditions
    if "condition_avoid" not in data:
        data["condition_avoid"] = {}
        
    data["condition_avoid"]["hyperglycemia"] = {
        "reason": "Directly spikes blood glucose levels and exacerbates metabolic stress.",
        "foods": ["Sugar", "Honey", "White Rice", "Refined Flour", "Soda", "Juice"]
    }
    data["condition_avoid"]["hypertension"] = {
        "reason": "High sodium and saturated fats elevate blood pressure.",
        "foods": ["Pickles", "Papad", "Processed Meat", "Canned Soup", "Salted Nuts"]
    }
    
    with open(KB_FILE, 'w') as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
    update_kb()
    print("KB successfully updated with vital monitoring conditions.")
