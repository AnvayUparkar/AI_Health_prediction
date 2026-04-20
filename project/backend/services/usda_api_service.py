
import os
import requests
import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class USDAApiService:
    """
    Handles communication with the USDA FoodData Central API.
    Provides search and details with local caching.
    """
    BASE_URL = "https://api.nal.usda.gov/fdc/v1"
    
    # Map USDA Nutrient IDs to our internal keys
    # IDs can be found via: https://fdc.nal.usda.gov/portal-data/external/nutrient_definition
    NUTRIENT_ID_MAP = {
        "iron": 1089,       # Iron, Fe
        "vitamin_c": 1162,  # Vitamin C, total ascorbic acid
        "vitamin_b12": 1178,# Vitamin B-12
        "calcium": 1087,    # Calcium, Ca
        "vitamin_d": 1114,  # Vitamin D (D2 + D3)
        "fiber": 1079,      # Fiber, total dietary
        "protein": 1003,    # Protein
        "potassium": 1092,  # Potassium, K
        "magnesium": 1090,  # Magnesium, Mg
        "selenium": 1103,   # Selenium, Se
        "zinc": 1095,       # Zinc, Zn
        "sodium": 1093,     # Sodium, Na
        "sugar": 2000       # Sugars, total including NLEA
    }

    def __init__(self):
        self.api_key = os.getenv("USDA_API_KEY")
        self.enabled = os.getenv("USDA_API_ENABLED", "False").lower() == "true"
        
        # Cache setup
        self.cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")
        self.cache_file = os.path.join(self.cache_dir, "usda_api_cache.json")
        self._ensure_cache()
        self.cache = self._load_cache()

    def _ensure_cache(self):
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        if not os.path.exists(self.cache_file):
            with open(self.cache_file, "w") as f:
                json.dump({}, f)

    def _load_cache(self) -> Dict[str, Any]:
        try:
            with open(self.cache_file, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_cache(self):
        try:
            with open(self.cache_file, "w") as f:
                json.dump(self.cache, f)
        except Exception as e:
            logger.error(f"Failed to save USDA cache: {e}")

    def fetch_food_data(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Search for a food and return it in our standard format.
        Uses cache if available.
        """
        if not self.enabled or not self.api_key:
            return None
            
        query_clean = query.strip().lower()
        if query_clean in self.cache:
            return self.cache[query_clean]

        logger.info(f"USDA_API | Searching for: {query_clean}")
        try:
            # 1. Search for the food
            search_url = f"{self.BASE_URL}/foods/search?api_key={self.api_key}"
            payload = {
                "query": query_clean,
                "pageSize": 5,
                "dataType": ["Foundation", "SR Legacy", "Survey (FNDDS)"]
            }
            
            response = requests.post(search_url, json=payload, timeout=10)
            response.raise_for_status()
            results = response.json()
            
            foods = results.get("foods", [])
            if not foods:
                return None
                
            # Pick the best match (shortest name usually means raw/basic item)
            best_match = sorted(foods, key=lambda x: len(x.get("description", "")))[0]
            
            # 2. Extract nutrients
            mapped_nutrients = {}
            units = {}
            calories = 0.0
            
            food_nutrients = best_match.get("foodNutrients", [])
            for nut in food_nutrients:
                # API format for search results has nutrientId
                n_id = nut.get("nutrientId")
                amount = nut.get("value", 0.0)
                unit = nut.get("unitName", "")
                
                # Check for calories
                if n_id == 1008 or nut.get("nutrientName", "").lower() == "energy":
                    calories = amount

                # Map to our keys
                for key, target_id in self.NUTRIENT_ID_MAP.items():
                    if n_id == target_id:
                        mapped_nutrients[key] = amount
                        units[key] = unit

            normalized_data = {
                "name": best_match.get("description"),
                "nutrients": mapped_nutrients,
                "units": units,
                "calories": calories,
                "fdc_id": best_match.get("fdcId"),
                "source": "USDA_LIVE_API"
            }
            
            # Save to cache
            self.cache[query_clean] = normalized_data
            self._save_cache()
            
            return normalized_data

        except Exception as e:
            logger.error(f"USDA_API | Request failed for '{query}': {e}")
            return None

# Singleton instance
usda_api_service = USDAApiService()
