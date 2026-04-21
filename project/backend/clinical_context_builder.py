import re
from typing import Dict, List, Any, Set

def build_context(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transforms standardized analysis summary into a Scoring Context Object.
    
    analysis = {
        "conditions": [...],
        "nutritional_goals": {"iron": "high", "sugar": "low"},
        "recommended_foods": ["Spinach and kale", "Red meat"],
        "avoid_foods": ["Coffee", "Sugar"]
    }
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
    
    return {
        "conditions": analysis.get("conditions", []),
        "boost": boost_set,
        "avoid": avoid_set,
        "goals": goals,
        "raw_analysis": analysis # Keep for debugging
    }
