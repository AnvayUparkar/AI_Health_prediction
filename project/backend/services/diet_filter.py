
from typing import List, Dict, Any

class DietFilter:
    """
    Filters classified foods based on the patient's specific lab markers and conditions.
    """
    def filter_foods(self, patient_data: Dict[str, Any], classified_foods: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # 1. Identify Target Categories based on Patient Data
        target_categories = []
        
        # Glucose Rule
        glucose = patient_data.get("glucose_value") or patient_data.get("glucose")
        if glucose and float(glucose) > 125:
            target_categories.extend(["HIGH_FIBER", "LOW_GI"])
            
        # Blood Pressure Rule
        bp = str(patient_data.get("bp") or "")
        systolic = 0
        if "/" in bp:
            try: systolic = int(bp.split("/")[0])
            except: pass
        if systolic > 135:
            target_categories.append("LOW_SODIUM")
            
        # Activity Rule
        activity = str(patient_data.get("activityLevel") or "").lower()
        if activity in ["sedentary", "none", "inactive"]:
            target_categories.extend(["LIGHT", "LOW_CALORIE"])
            
        # 2. Filter Process
        if not target_categories:
            # For healthy users, return everything (general wellness)
            return classified_foods
            
        filtered = []
        for food in classified_foods:
            # Check if food matches ANY of the target clinical requirements
            matches = [cat in food["categories"] for cat in target_categories]
            if any(matches):
                # Count matches for later ranking
                food["match_score"] = sum(matches)
                filtered.append(food)
                
        # Sort by relevance to conditions
        filtered.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        
        return filtered

# Singleton instance
diet_filter = DietFilter()
