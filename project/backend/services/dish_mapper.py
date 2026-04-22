import json
from backend.services.spoonacular_service import get_ingredients_from_spoonacular
from backend.services.gemini_service import get_gemini_response

# 3. Add Caching (VERY IMPORTANT)
SPOON_CACHE = {}

# 1. Static Mapping (Dish -> Ingredients)
DISH_MAP = {
    "oats upma": ["oats", "onion", "carrot", "peas", "oil"],
    "vegetable daliya": ["broken wheat", "carrot", "beans", "peas", "oil"],
    "moong dal chilla": ["moong dal", "onion", "coriander", "oil"],
    "brown rice + dal": ["brown rice", "lentils", "onion", "tomato", "spices"],
    "multigrain roti + sabzi": ["whole wheat", "mixed vegetables", "oil", "spices"],
    "lauki sabzi + roti": ["bottle gourd", "whole wheat", "tomato", "spices"],
    "vegetable khichdi": ["rice", "moong dal", "carrot", "peas", "ghee"]
}

def infer_ingredients(food_name: str) -> list:
    """Fallback: Uses Gemini to infer ingredients if Spoonacular fails."""
    prompt = f"List the 3 to 5 core base ingredients for the dish '{food_name}'. Return ONLY a comma-separated list of lowercase ingredient names (e.g., tomato, onion, chicken). Do not include quantities or formatting."
    try:
        response = get_gemini_response(prompt)
        if response:
            return [i.strip().lower() for i in response.split(",")]
    except Exception as e:
        print(f"❌ AI Inference failed for {food_name}: {e}")
    return []

def get_ingredients(food_name: str) -> tuple:
    """
    Extracts base ingredients from a dish name using a 4-stage Hybrid System.
    Returns (ingredients_list, source)
    """
    food_name = food_name.lower().strip()

    # 3. Cache Check
    if food_name in SPOON_CACHE:
        print(f"[CACHE] {food_name} -> {SPOON_CACHE[food_name]}")
        return SPOON_CACHE[food_name], "cache"

    # 1. Static mapping
    if food_name in DISH_MAP:
        ingredients = list(set([i.lower().strip() for i in DISH_MAP[food_name]]))
        print(f"[STATIC] {food_name} -> {ingredients}")
        return ingredients, "static"

    # 2. Spoonacular API (NEW)
    spoonacular_ingredients = get_ingredients_from_spoonacular(food_name)

    if spoonacular_ingredients:
        # 4. Normalize
        normalized = list(set([i.lower().strip() for i in spoonacular_ingredients]))
        SPOON_CACHE[food_name] = normalized
        print(f"[SPOONACULAR] {food_name} -> {normalized}")
        return normalized, "spoonacular"

    # 3. AI-style inference (Fallback)
    inferred = infer_ingredients(food_name)

    if inferred:
        normalized = list(set([i.lower().strip() for i in inferred]))
        SPOON_CACHE[food_name] = normalized
        print(f"[INFERRED] {food_name} -> {normalized}")
        return normalized, "inferred"

    # 4. Raw fallback
    print(f"[RAW FALLBACK] {food_name} -> {[food_name]}")
    return [food_name], "raw"
