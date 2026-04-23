import re
from typing import Dict, List, Any, Set

def build_context(analysis: Dict[str, Any], health_data: dict = None) -> Dict[str, Any]:
    """
    Transforms standardized analysis summary into a Scoring Context Object.
    Now supports health_data injection for activity-aware clinical logic.
    """
    
    # 1. Normalize Food Identifiers (Extract keywords for scoring matches)
    def normalize_foods(food_list: List[str]) -> Set[str]:
        keywords = set()
        for item in food_list:
            # Remove parentheses and split by common separators
            clean = re.sub(r'\(.*?\)', '', item).lower()
            parts = re.split(r'[,;and/]+', clean)
            for p in parts:
                p = p.strip()
                if len(p) > 2:
                    keywords.add(p)
        return keywords

    boost_set = normalize_foods(analysis.get("recommended_foods", []))
    avoid_set = normalize_foods(analysis.get("avoid_foods", []))
    
    # 2. Map Nutritional Goals (Standardized keys for USDA comparison)
    goals = analysis.get("nutritional_goals", {})
    
    context = {
        "conditions": analysis.get("conditions", []),
        "boost": boost_set,
        "avoid": avoid_set,
        "goals": goals,
        "raw_analysis": analysis
    }

    # 3. Inject Health Data for clinical grounding
    if health_data:
        context["activityLevel"] = health_data.get("activityLevel", "moderate")
        context["age"] = health_data.get("age")
        context["weight"] = health_data.get("weight")
        context["height"] = health_data.get("height")
        context["healthConditions"] = health_data.get("healthConditions", "")
        
        # 🍽️ Dietary Preferences — drives food filtering in IndianMealBuilder
        context["diet_preference"] = health_data.get("dietaryPreference",
                                         health_data.get("diet_preference", "balanced"))
        context["non_veg_preferences"] = health_data.get("nonVegPreferences",
                                             health_data.get("non_veg_preferences", []))
        context["allergies"] = health_data.get("allergies", [])

    return context
