import json
import logging
import os
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class USDAManager:
    """
    Singleton Manager for USDA FoodData Central (Foundation dataset).
    Handles indexing of nutrients for biochemical-based ranking.
    """
    NUTRIENT_MAP = {
        "iron": "Iron, Fe",
        "vitamin_c": "Vitamin C, total ascorbic acid",
        "vitamin_b12": "Vitamin B-12",
        "calcium": "Calcium, Ca",
        "vitamin_d": "Vitamin D (D2 + D3)",
        "fiber": "Fiber, total dietary",
        "protein": "Protein",
        "potassium": "Potassium, K",
        "magnesium": "Magnesium, Mg",
        "selenium": "Selenium, Se",
        "zinc": "Zinc, Zn",
        "sodium": "Sodium, Na",
        "sugar": "Sugars, Total"
    }

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(USDAManager, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self, json_path: str):
        if self.initialized:
            return
            
        self.path = json_path
        self.food_index = {} # fdcId -> {name, nutrients}
        self.nutrient_rankings = {} # nutrient_key -> list of (fdcId, amount) sorted by amount
        
        self._load_and_index()
        self.initialized = True

    def _load_and_index(self):
        """Loads and indexes the Foundation dataset."""
        try:
            if not os.path.exists(self.path):
                logger.error("USDA dataset not found at %s", self.path)
                return

            with open(self.path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            foods = data.get("FoundationFoods", [])
            logger.info("USDA_LOADER | Starting index for %d foundation foods.", len(foods))

            # Temp storage for rankings
            temp_ranks = {k: [] for k in self.NUTRIENT_MAP.keys()}

            for food in foods:
                fdc_id = food.get("fdcId")
                description = food.get("description", "Unknown Food")
                nutrients = food.get("foodNutrients", [])
                
                food_data = {
                    "name": description,
                    "nutrients": {},
                    "calories": 0.0,
                    "units": {}
                }

                # Extract mapped nutrients
                for nut_entry in nutrients:
                    nut_obj = nut_entry.get("nutrient", {})
                    nut_name = nut_obj.get("name")
                    amount = nut_entry.get("amount", 0.0)
                    unit = nut_obj.get("unitName", "")
                    
                    if nut_name == "Energy" and unit == "kcal":
                        food_data["calories"] = amount

                    for engine_key, usda_name in self.NUTRIENT_MAP.items():
                        if usda_name == nut_name:
                            food_data["nutrients"][engine_key] = amount
                            food_data["units"][engine_key] = unit
                            temp_ranks[engine_key].append((fdc_id, amount))

                self.food_index[fdc_id] = food_data

            # Sort rankings by amount (desc)
            for key in temp_ranks:
                temp_ranks[key].sort(key=lambda x: x[1], reverse=True)
                self.nutrient_rankings[key] = temp_ranks[key]

            logger.info("USDA_LOADER | Successfully indexed %d foods.", len(self.food_index))

        except Exception as e:
            logger.error("USDA_LOADER | Critical failure: %s", e)

    def get_top_foods(self, nutrient_key: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Returns top sources for a given nutrient, prioritizing natural foundation items."""
        if nutrient_key not in self.nutrient_rankings:
            return []
            
        rankings = self.nutrient_rankings[nutrient_key]
        results = []
        for fdc_id, amount in rankings:
            if len(results) >= limit: break
            
            food = self.food_index[fdc_id]
            desc = food["name"].lower()
            
            # Simple heuristic: Prioritize foods without 'canned', 'processed', 'salted' in the first 10 results
            if any(x in desc for x in ["canned", "salted", "frankfurter"]):
                if len(results) < (limit // 2): continue # Skip processed if we have plenty of room
                
            if amount > 0:
                results.append({
                    "name": food["name"],
                    "amount": amount,
                    "unit": food["units"].get(nutrient_key, ""),
                    "calories": food["calories"],
                    "fdc_id": fdc_id
                })
        return results

    def get_food_biochemicals(self, food_name: str) -> Optional[Dict[str, Any]]:
        """Attempt to find biochemical data for a food by name (fuzzy match)."""
        name_lower = food_name.lower()
        
        # 1. Direct match check
        for fid, data in self.food_index.items():
            if data["name"].lower() == name_lower:
                return data
        
        # 2. Key word match check
        best_match = None
        for fid, data in self.food_index.items():
            if name_lower in data["name"].lower():
                # Prefer shorter descriptions as they are usually raw items
                if not best_match or len(data["name"]) < len(best_match["name"]):
                    best_match = data
                    
        return best_match

# Singleton creation
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USDA_PATH = os.path.join(os.path.dirname(BASE_DIR), "FoodData_Central_foundation_food_json_2025-12-18.json")
usda_manager = USDAManager(USDA_PATH)
