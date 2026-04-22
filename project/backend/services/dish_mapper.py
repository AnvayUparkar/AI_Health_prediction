import os
import json
import logging
import time
from typing import Dict, List, Any, Set, Tuple

# --- CONFIGURATION (Senior Architect Standards) ---
MAX_CACHE_SIZE = 500
CACHE_TTL = 30 * 24 * 60 * 60  # 30 days in seconds
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "spoonacular_cache.json")

# Confidence Scoring Matrix
CONFIDENCE = {
    "static": 1.0,
    "cache": 0.95,
    "spoonacular": 0.9,
    "inferred": 0.7,
    "raw": 0.5
}

VALID_FOODS = set([
    "rice", "lentils", "milk", "egg", "chicken", "paneer", "oats", "wheat", 
    "beans", "fruits", "nuts", "oil", "ghee", "butter", "cream", "tomato", 
    "onion", "garlic", "ginger", "spinach", "potato", "carrot", "peas", 
    "curd", "yogurt", "dal", "chana", "rajma", "mutton", "fish", "spices",
    "turmeric", "cumin", "coriander", "avocado", "lemon", "cucumber"
])

LOCKED_REQUESTS: Set[str] = set()

# --- PERSISTENCE LAYER ---

def _load_persistence() -> dict:
    """Loads cache with backward compatibility and migration logic."""
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, "r") as f:
            data = json.load(f)
            
            # Migration logic: Convert old List format to new Dict format with timestamp
            migrated_count = 0
            for key in list(data.keys()):
                if isinstance(data[key], list):
                    # Wrap legacy list in new structure
                    data[key] = {
                        "ingredients": data[key],
                        "timestamp": time.time(),
                        "confidence": CONFIDENCE["cache"]
                    }
                    migrated_count += 1
            
            if migrated_count > 0:
                print(f"📦 [DISH_MAPPER] Migrated {migrated_count} legacy cache entries.")
            
            return data
    except Exception:
        return {}

def _enforce_cache_limit(cache: dict):
    while len(cache) > MAX_CACHE_SIZE:
        oldest_key = next(iter(cache))
        cache.pop(oldest_key)

def _save_persistence(cache_data: dict):
    try:
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR)
        _enforce_cache_limit(cache_data)
        with open(CACHE_FILE, "w") as f:
            json.dump(cache_data, f, indent=4)
    except Exception as e:
        logging.error(f"DISH_MAPPER | Save failed: {e}")

# Global In-Memory Cache
SPOON_CACHE = _load_persistence()

# --- LOGIC & UTILITIES ---

class MapperResult(dict):
    def __iter__(self):
        yield self["ingredients"]
        yield self["meta"]["source"]

def validate_ingredients(ingredients: List[str]) -> List[str]:
    return [
        i for i in ingredients
        if any(word in i.lower() for word in VALID_FOODS)
    ]

def apply_confidence_decay(base_confidence: float, timestamp: float) -> float:
    """
    Applies a temporal decay factor to confidence scores based on cache age.
    Reliability decreases linearly from 100% to 80% as data approaches TTL.
    """
    age = time.time() - timestamp
    
    # Normalize decay factor between 0.8 and 1.0
    decay_factor = max(0.8, 1.0 - (age / CACHE_TTL))
    
    return round(base_confidence * decay_factor, 3)

def infer_ingredients(food_name: str) -> list:
    food_name = food_name.lower().strip()
    ingredients = []
    
    mapping_rules = {
        "paneer": ["paneer", "spices", "oil"],
        "chicken": ["chicken", "onion", "tomato", "oil"],
        "dal": ["lentils", "onion", "garlic", "spices"],
        "roti": ["wheat"],
        "rice": ["rice"],
        "salad": ["cucumber", "tomato", "lemon"],
        "khichdi": ["rice", "lentils", "ghee"],
        "upma": ["oats", "onion", "carrot"],
        "chilla": ["moong dal", "onion", "oil"],
        "egg": ["egg", "oil", "onion"]
    }
    
    for key, items in mapping_rules.items():
        if key in food_name:
            ingredients.extend(items)
    
    return list(set(ingredients))

# --- PRIMARY INTERFACE ---

def get_ingredients(food_name: str) -> MapperResult:
    from backend.services.spoonacular_service import get_ingredients_from_spoonacular
    
    food_name = food_name.lower().strip()
    if not food_name:
        return MapperResult({"ingredients": [], "meta": {"source": "raw", "confidence": 0}})

    # 1. Static Mapping (Precedence 1)
    DISH_MAP = {
        "oats upma": ["oats", "onion", "carrot", "peas", "oil"],
        "vegetable daliya": ["broken wheat", "carrot", "beans", "peas", "oil"],
        "moong dal chilla": ["moong dal", "onion", "coriander", "oil"],
        "brown rice + dal": ["brown rice", "lentils", "onion", "tomato", "spices"],
        "multigrain roti + sabzi": ["whole wheat", "mixed vegetables", "oil", "spices"],
        "lauki sabzi + roti": ["bottle gourd", "whole wheat", "tomato", "spices"],
        "vegetable khichdi": ["rice", "moong dal", "carrot", "peas", "ghee"]
    }

    if food_name in DISH_MAP:
        source = "static"
        return _finalize(DISH_MAP[food_name], source)

    # 2. Persistent Cache Check with TTL
    if food_name in SPOON_CACHE:
        cached = SPOON_CACHE[food_name]
        current_time = time.time()
        
        # Check if entry is still valid (TTL check)
        if current_time - cached.get("timestamp", 0) < CACHE_TTL:
            source = "cache"
            # Apply temporal decay to the stored confidence
            decayed_confidence = apply_confidence_decay(
                cached.get("confidence", 0.95),
                cached.get("timestamp", current_time)
            )
            return _finalize(cached["ingredients"], source, decayed_confidence)
        else:
            print(f"⏳ [DISH_MAPPER] Cache expired for {food_name}, refreshing...")
            del SPOON_CACHE[food_name] # Trigger refresh

    # 3. Duplicate Call Prevention
    if food_name in LOCKED_REQUESTS:
        return MapperResult({"ingredients": [], "meta": {"source": "locked", "confidence": 0}})

    LOCKED_REQUESTS.add(food_name)
    
    try:
        # 4. Spoonacular API (Precedence 3)
        spoon_ingredients = get_ingredients_from_spoonacular(food_name)
        if spoon_ingredients:
            source = "spoonacular"
            ingredients = validate_ingredients(spoon_ingredients)
            if ingredients:
                _cache_and_save(food_name, ingredients, source)
                return _finalize(ingredients, source)

        # 5. Rule-Based Inference (Precedence 4)
        inferred = infer_ingredients(food_name)
        if inferred:
            source = "inferred"
            _cache_and_save(food_name, inferred, source)
            return _finalize(inferred, source)

    finally:
        if food_name in LOCKED_REQUESTS:
            LOCKED_REQUESTS.remove(food_name)

    # 6. Raw Fallback
    return _finalize([food_name], "raw")

def _cache_and_save(name: str, ingredients: list, source: str):
    """Internal helper with timestamp and confidence tracking."""
    SPOON_CACHE[name] = {
        "ingredients": ingredients,
        "timestamp": time.time(),
        "confidence": CONFIDENCE.get(source, 0.5)
    }
    _save_persistence(SPOON_CACHE)

def _finalize(ingredients: list, source: str, confidence_override: float = None) -> MapperResult:
    final_ingredients = list(set(ingredients))
    confidence = confidence_override if confidence_override is not None else CONFIDENCE.get(source, 0.5)
    
    print(f"[MAPPER] Source: {source.upper()} | Confidence: {confidence}")
    print(f"[MAPPER] {final_ingredients}")
    
    return MapperResult({
        "ingredients": final_ingredients,
        "meta": {
            "source": source,
            "confidence": confidence
        }
    })
