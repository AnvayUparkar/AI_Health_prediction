
from typing import Dict, List, Any

class MealExplainer:
    """
    Generates biochemical and clinical reasoning for recommended meals.
    Links nutrient data to patient conditions (e.g. Glucose -> Fiber).
    """
    REASONING_TEMPLATES = {
        "HIGH_FIBER": "High fiber content helps regulate blood sugar and prevents glucose spikes by slowing carbohydrate absorption.",
        "LOW_GI": "Low Glycemic Index profile ensures stable insulin levels and long-lasting energy without metabolic stress.",
        "HIGH_PROTEIN": "Optimal lean protein density supports muscular repair and structural metabolic integrity.",
        "LOW_SODIUM": "Reduced sodium concentration assists in maintaining vascular stability and renal filtration efficiency.",
        "LOW_CALORIE": "Reduced caloric density promotes metabolic efficiency and weight management for sedentary profiles.",
        "LIGHT": "Light digestive profile minimizes gastric load and promotes post-meal alertness."
    }

    def add_explanations(self, meal_plan: Dict[str, List[Dict[str, Any]]], patient_data: Dict[str, Any]) -> Dict[str, Any]:
        explained_plan = {}
        
        for meal_slot, items in meal_plan.items():
            slot_data = []
            for item in items:
                # Select the most relevant explanation based on categories
                categories = item.get("categories", [])
                
                # Priority mapping based on patient data
                # If glucose is high, prioritize FIBER/GI explanations
                is_diabetic = float(patient_data.get("glucose") or 0) > 125
                
                reason = "Natural whole-food source providing essential micronutrients for general metabolic support."
                
                if is_diabetic and "HIGH_FIBER" in categories:
                    reason = self.REASONING_TEMPLATES["HIGH_FIBER"]
                elif is_diabetic and "LOW_GI" in categories:
                    reason = self.REASONING_TEMPLATES["LOW_GI"]
                elif "LOW_SODIUM" in categories and int((str(patient_data.get("bp") or "0/0").split("/")[0]) or 0) > 135:
                    reason = self.REASONING_TEMPLATES["LOW_SODIUM"]
                elif categories:
                    # Fallback to the first applicable category
                    reason = self.REASONING_TEMPLATES.get(categories[0], reason)

                slot_data.append({
                    "item": item["name"].title(),
                    "explanation": reason,
                    "nutrients": {
                        "p": item.get("protein"),
                        "f": item.get("fiber"),
                        "c": item.get("calories")
                    }
                })
            
            explained_plan[meal_slot] = slot_data
            
        return explained_plan

# Singleton instance
meal_explainer = MealExplainer()
