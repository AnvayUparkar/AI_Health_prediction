
import os
import requests
import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class USDAService:
    """
    Handles communication with the USDA FoodData Central API.
    Provides searching and detail extraction with local fallback.
    """
    BASE_URL = "https://api.nal.usda.gov/fdc/v1"
    
    # Map USDA Nutrient IDs to our internal keys
    NUTRIENT_ID_MAP = {
        "protein": 1003,
        "fiber": 1079,
        "sugar": 2000,
        "carbohydrates": 1005,
        "calories": 1008,
        "sodium": 1093
    }

    def __init__(self):
        self.api_key = os.getenv("USDA_API_KEY")
        self.enabled = os.getenv("USDA_API_ENABLED", "False").lower() == "true"
        
        # Cache setup
        self.cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")
        self.cache_file = os.path.join(self.cache_dir, "usda_api_cache_v2.json")
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

    def search_foods(self, query_string: str) -> List[Dict[str, Any]]:
        """
        Search for foods by keyword and return structured nutrient data.
        Requirement: protein, fiber, sugar, carbohydrates, calories, sodium.
        """
        queries = [q.strip() for q in query_string.split(",")]
        all_results = []

        for query in queries:
            query_clean = query.lower()
            
            # 1. Check Cache
            if query_clean in self.cache:
                all_results.append(self.cache[query_clean])
                continue

            # 2. API Call
            if self.enabled and self.api_key:
                try:
                    search_url = f"{self.BASE_URL}/foods/search?api_key={self.api_key}"
                    payload = {
                        "query": query_clean,
                        "pageSize": 5,
                        "dataType": ["Foundation", "SR Legacy", "Survey (FNDDS)"]
                    }
                    response = requests.post(search_url, json=payload, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    
                    foods = data.get("foods", [])
                    if foods:
                        # Best match
                        best = sorted(foods, key=lambda x: len(x.get("description", "")))[0]
                        
                        mapped = {
                            "name": best.get("description"),
                            "fdc_id": best.get("fdcId"),
                            "protein": 0.0,
                            "fiber": 0.0,
                            "sugar": 0.0,
                            "carbohydrates": 0.0,
                            "calories": 0.0,
                            "sodium": 0.0
                        }

                        for nut in best.get("foodNutrients", []):
                            n_id = nut.get("nutrientId")
                            val = nut.get("value", 0.0)
                            
                            for key, target_id in self.NUTRIENT_ID_MAP.items():
                                if n_id == target_id:
                                    mapped[key] = val
                            
                            # Fallback check by name for calories
                            if not mapped["calories"] and nut.get("nutrientName", "").lower() == "energy":
                                mapped["calories"] = val

                        self.cache[query_clean] = mapped
                        self._save_cache()
                        all_results.append(mapped)
                except Exception as e:
                    logger.error(f"USDA API Search failed for {query_clean}: {e}")
            
        return all_results

# Singleton instance
usda_service = USDAService()
