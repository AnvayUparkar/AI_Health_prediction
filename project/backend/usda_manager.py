
import os
import json
import logging
from typing import List, Dict, Any, Tuple
from backend.usda_loader import usda_loader

logger = logging.getLogger(__name__)

class USDAManager:
    """
    Expert Manager for USDA nutrition data.
    Implements a Hybrid Strategy: Local for Bulk Scoring, Live for Final Grounding.
    """
    
    def __init__(self):
        # Cache setup for API hits
        self.cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
        self.cache_file = os.path.join(self.cache_dir, "usda_manager_cache.json")
        self._ensure_cache()
        self.api_cache = self._load_cache()

    def _ensure_cache(self):
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        if not os.path.exists(self.cache_file):
            with open(self.cache_file, "w") as f:
                json.dump({}, f)

    def _load_cache(self) -> dict:
        try:
            with open(self.cache_file, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_to_local_cache(self, food_name: str, data: dict):
        """Saves successful API results to disk for offline persistence."""
        try:
            self.api_cache[food_name.lower()] = data
            with open(self.cache_file, "w") as f:
                json.dump(self.api_cache, f)
        except Exception as e:
            logger.error(f"USDA_MANAGER | Cache save failed: {e}")

    def get_food_nutrients(self, food_name: str) -> dict:
        """
        Primary interface for FINAL recommendations.
        Tries Cache -> API -> Local Fallback.
        """
        food_name_clean = food_name.lower()
        
        # 0. Check API Cache (Crucial to avoid 120s timeout)
        if food_name_clean in self.api_cache:
            print(f"[SMART CACHE] Loaded data for '{food_name}' instantly.")
            return self.api_cache[food_name_clean]

        # 1. Live API Path (Shows logs in terminal)
        try:
            print(f"[LIVE USDA API] Fetching real-time data for: '{food_name}'...")
            data = usda_loader.fetch_from_usda_api(food_name)
            if data:
                print(f"[LIVE USDA API] Successfully fetched & cached '{food_name}'.")
                self.save_to_local_cache(food_name, data)
                return data
        except Exception as e:
            logger.error(f"USDA_MANAGER | Live API failed: {e}")

        # 2. Fallback to Local
        print(f"[LOCAL FALLBACK] USDA API failed or offline. Using local database for '{food_name}'.")
        return self.get_food_nutrients_local(food_name)

    def get_food_nutrients_local(self, food_name: str) -> dict:
        """
        High-speed local lookup. Used for heavy scoring loops.
        """
        try:
            data = usda_loader.fetch_from_local_json(food_name)
            if data:
                return data
        except Exception:
            pass
        return self._get_default_nutrient_profile(food_name)

    def get_top_foods(self, nutrient_key: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Delegates bulk ranking to the low-level loader."""
        return usda_loader.get_top_foods(nutrient_key, limit)

    def _get_default_nutrient_profile(self, food_name: str) -> dict:
        """Emergency default structure to prevent engine crashes."""
        return {
            "name": food_name.title(),
            "protein": 1.0,
            "fiber": 1.0,
            "carbohydrates": 10.0,
            "sugar": 0.0,
            "calories": 50.0,
            "nutrients": {
                "protein": 1.0, "fiber": 1.0, "carbohydrates": 10.0, "sugar": 0.0, "calories": 50.0
            },
            "source": "DEFAULT_SAFE"
        }

    def get_food_nutrients_with_meta(self, food_name: str) -> Tuple[dict, dict]:
        """
        Extended interface that returns both data and confidence metadata.
        Confidence levels: API Cache (0.95), Live API (0.9), Local Fallback (0.7), Default (0.5).
        """
        food_name_clean = food_name.lower()
        
        # 0. Check API Cache
        if food_name_clean in self.api_cache:
            return self.api_cache[food_name_clean], {"source": "usda_cache", "confidence": 0.95}

        # 1. Live API Path
        try:
            data = usda_loader.fetch_from_usda_api(food_name)
            if data:
                self.save_to_local_cache(food_name, data)
                return data, {"source": "usda_api", "confidence": 0.9}
        except Exception:
            pass

        # 2. Fallback to Local
        try:
            data = usda_loader.fetch_from_local_json(food_name)
            if data:
                return data, {"source": "usda_local", "confidence": 0.7}
        except Exception:
            pass

        # 3. Default
        return self._get_default_nutrient_profile(food_name), {"source": "default", "confidence": 0.5}

# Singleton instance
usda_manager = USDAManager()
