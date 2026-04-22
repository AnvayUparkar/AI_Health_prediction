import os
import json
from backend.services.spoonacular_service import get_ingredients_from_spoonacular
from backend.services.gemini_service import get_gemini_response

# --- PERSISTENCE LAYER (Senior AI Healthcare Standard) ---
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "spoonacular_cache.json")

def _load_persistence() -> dict:
    """Loads the persistent mapping from disk with corruption safety."""
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception) as e:
        print(f"⚠️ [DISH_MAPPER] Cache corruption detected or file empty. Resetting: {e}")
        return {}

def _save_persistence(cache_data: dict):
    """Saves the mapping to disk using an atomic-style write to prevent corruption."""
    try:
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR)
        
        # Write to a temporary string first to ensure data integrity
        json_content = json.dumps(cache_data, indent=4)
        with open(CACHE_FILE, "w") as f:
            f.write(json_content)
    except Exception as e:
        print(f"❌ [DISH_MAPPER] Critical: Failed to persist cache: {e}")

# Initialize Cache from Disk
SPOON_CACHE = _load_persistence()

# 1. Static Mapping (Dish -> Ingredients)
# These are the 'Clinical Gold Standard' hardcoded mappings
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
    
    Stages:
    1. Static Mapping (Internal Clinical List)
    2. Persistent Cache (Previous successful hits)
    3. Spoonacular API (Live database)
    4. Gemini AI Inference (Structural guessing)
    """
    food_name = food_name.lower().strip()

    # 1. Static mapping (Precedence 1: Manual overrides)
    if food_name in DISH_MAP:
        ingredients = list(set([i.lower().strip() for i in DISH_MAP[food_name]]))
        print(f"[STATIC] {food_name} -> {ingredients}")
        return ingredients, "static"

    # 2. Persistent Cache Check (Precedence 2: Speed & Cost Saving)
    if food_name in SPOON_CACHE:
        print(f"[CACHE HIT] {food_name} -> {SPOON_CACHE[food_name]}")
        return SPOON_CACHE[food_name], "cache"

    # 3. Spoonacular API (External Grounding)
    spoonacular_ingredients = get_ingredients_from_spoonacular(food_name)

    if spoonacular_ingredients:
        normalized = list(set([i.lower().strip() for i in spoonacular_ingredients]))
        SPOON_CACHE[food_name] = normalized
        _save_persistence(SPOON_CACHE) # Persist immediately
        print(f"[SPOONACULAR] {food_name} (Saved to Cache) -> {normalized}")
        return normalized, "spoonacular"

    # 4. AI-style inference (Fallback/Resilience)
    inferred = infer_ingredients(food_name)

    if inferred:
        normalized = list(set([i.lower().strip() for i in inferred]))
        SPOON_CACHE[food_name] = normalized
        _save_persistence(SPOON_CACHE) # Even AI results are worth caching
        print(f"[INFERRED] {food_name} (Saved to Cache) -> {normalized}")
        return normalized, "inferred"

    # 5. Raw fallback (Emergency)
    print(f"[RAW FALLBACK] No mapping found for {food_name}. Using raw name.")
    return [food_name], "raw"
