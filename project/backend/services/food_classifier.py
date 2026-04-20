
from typing import List, Dict, Any

class FoodClassifier:
    """
    Classifies raw food data into clinical categories based on nutrient density.
    """
    def classify_foods(self, foods: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        for food in foods:
            categories = []
            
            # 1. HIGH_PROTEIN (> 15g per 100g or calories from protein > 20%)
            protein = food.get("protein", 0)
            if protein > 15:
                categories.append("HIGH_PROTEIN")
            
            # 2. HIGH_FIBER (> 5g per 100g)
            fiber = food.get("fiber", 0)
            if fiber > 5:
                categories.append("HIGH_FIBER")
                
            # 3. LOW_GI (Heuristic based on fiber-to-carb ratio and low sugar)
            # USDA doesn't provide GI directly, so we use a biochemical proxy.
            carbs = food.get("carbohydrates", 0)
            sugar = food.get("sugar", 0)
            if carbs > 0:
                fiber_ratio = fiber / carbs
                if fiber_ratio > 0.15 and sugar < 5:
                    categories.append("LOW_GI")
            elif sugar < 2: # Very low carbs/sugar
                categories.append("LOW_GI")

            # 4. LOW_SODIUM (< 140mg per 100g - FDA standard)
            # Note: USDA service needs to fetch sodium for this to work perfectly.
            # I will ensure the final usda_service fetches sodium too.
            sodium = food.get("sodium", 0)
            if sodium < 140:
                categories.append("LOW_SODIUM")
                
            # 5. LOW_CALORIE (< 100 kcal per 100g)
            calories = food.get("calories", 0)
            if calories < 100:
                categories.append("LOW_CALORIE")
                categories.append("LIGHT")

            food["categories"] = categories
            
        return foods

# Singleton instance
food_classifier = FoodClassifier()
