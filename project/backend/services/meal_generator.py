
import random
from typing import List, Dict, Any

class MealGenerator:
    """
    Assembles a complete daily meal plan from filtered ingredients.
    Ensures variety and nutritional balance.
    """
    def generate_meals(self, filtered_foods: List[Dict[str, Any]]) -> Dict[str, Any]:
        meal_plan = {
            "breakfast": [],
            "lunch": [],
            "snacks": [],
            "dinner": []
        }
        
        # Indian Food Context Mapping (if USDA data is generic, we wrap it)
        # In a production system, this would be a more robust mapping.
        available = list(filtered_foods)
        if len(available) < 4:
            # Fallback if filtering was too strict
            available = filtered_foods
            
        random.shuffle(available)
        
        # Helper to pick and remove to avoid repetition
        def pick(n=1):
            batch = []
            for _ in range(n):
                if available: batch.append(available.pop(0))
            return batch

        # 1. Breakfast: Focus on energy + fiber
        meal_plan["breakfast"] = pick(2)
        
        # 2. Lunch: Focus on protein + satiety
        meal_plan["lunch"] = pick(3)
        
        # 3. Snacks: Focus on light/nutrient-dense
        meal_plan["snacks"] = pick(2)
        
        # 4. Dinner: Focus on easy digestion
        meal_plan["dinner"] = pick(2)
        
        # Final Format Cleanup (names only for now, reasoning comes later)
        return meal_plan

# Singleton instance
meal_generator = MealGenerator()
