
import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class USDALoader:
    """
    Low-level data fetcher for USDA nutritional data.
    Provides methods for both Live API and Local JSON access.
    """
    
    # --- [LOCAL OVERRIDE] Indian Staples Biochemical Mapping ---
    # Ensures these foods have accurate scores even if API/Foundation JSON lacks them.
    INDIAN_OVERRIDES = {
        "roti": {"protein": 3.0, "fiber": 4.0, "carbohydrates": 15.0, "sugar": 0.0, "calories": 100.0, "nutrients": {"protein": 3.0, "fiber": 4.0, "iron": 1.5}},
        "multigrain roti": {"protein": 5.0, "fiber": 6.0, "carbohydrates": 18.0, "sugar": 0.0, "calories": 110.0, "nutrients": {"protein": 5.0, "fiber": 6.0, "iron": 2.5}},
        "jowar roti": {"protein": 4.0, "fiber": 7.0, "carbohydrates": 20.0, "sugar": 0.0, "calories": 120.0, "nutrients": {"protein": 4.0, "fiber": 7.0, "magnesium": 40.0}},
        "bajra roti": {"protein": 4.5, "fiber": 8.0, "carbohydrates": 22.0, "sugar": 0.0, "calories": 130.0, "nutrients": {"protein": 4.5, "fiber": 8.0, "iron": 3.0}},
        "poha": {"protein": 2.5, "fiber": 2.0, "carbohydrates": 25.0, "sugar": 0.0, "calories": 150.0, "nutrients": {"protein": 2.5, "fiber": 2.0, "iron": 5.0}},
        "moong dal": {"protein": 24.0, "fiber": 16.0, "carbohydrates": 60.0, "sugar": 0.0, "calories": 340.0, "nutrients": {"protein": 24.0, "fiber": 16.0, "iron": 6.0}},
        "lentil dal": {"protein": 9.0, "fiber": 8.0, "carbohydrates": 20.0, "sugar": 0.0, "calories": 116.0, "nutrients": {"protein": 9.0, "fiber": 8.0, "iron": 3.3, "potassium": 369.0}},
        "vegetable sabzi": {"protein": 2.0, "fiber": 5.0, "carbohydrates": 10.0, "sugar": 0.0, "calories": 80.0, "nutrients": {"protein": 2.0, "fiber": 5.0, "vitamin_c": 15.0}},
        "bitter gourd sabzi": {"protein": 1.0, "fiber": 3.0, "carbohydrates": 5.0, "sugar": 0.0, "calories": 40.0, "nutrients": {"protein": 1.0, "fiber": 3.0, "potassium": 300.0}},
        "roasted makhana": {"protein": 9.0, "fiber": 14.0, "carbohydrates": 60.0, "sugar": 0.0, "calories": 350.0, "nutrients": {"protein": 9.0, "fiber": 14.0, "magnesium": 65.0}}
    }
    
    # Map for standardized schema extraction
    NUTRIENT_IDS = {
        "protein": 1003,
        "fiber": 1079,
        "sugar": 2000,
        "carbohydrates": 1005,
        "calories": 1008,
        "calcium": 1087,
        "iron": 1089,
        "magnesium": 1090,
        "phosphorus": 1091,
        "potassium": 1092,
        "sodium": 1093,
        "zinc": 1095,
        "vitamin_c": 1162,
        "vitamin_b12": 1178,
        "vitamin_d": 1114
    }

    def __init__(self):
        self.api_key = os.getenv("USDA_API_KEY")
        self.enabled = os.getenv("USDA_API_ENABLED", "False").lower() == "true"
        
        # Local JSON path
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.json_path = os.path.join(os.path.dirname(base_dir), "FoodData_Central_foundation_food_json_2025-12-18.json")
        self.local_index = None # fdcId -> data
        self.nutrient_rankings = {} # nutrient_key -> list of (fdcId, amount)

    def fetch_from_usda_api(self, food_name: str) -> Optional[dict]:
        """
        Primary source: Fetch live data from USDA API.
        Target Schema: {name, protein, fiber, carbs, sugar, calories, nutrients: {full set}}
        """
        if not self.enabled or not self.api_key:
            return None

        try:
            url = f"https://api.nal.usda.gov/fdc/v1/foods/search?api_key={self.api_key}"
            payload = {
                "query": food_name.lower(),
                "pageSize": 1,
                "dataType": ["Foundation", "SR Legacy"]
            }
            # Requirement: 5s timeout
            response = requests.post(url, json=payload, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            # --- VERBOSE TERMINAL DEBUGGING ---
            print(f"\n[LIVE_API] Raw Response for: {food_name.upper()}")
            print(f"[LIVE_API] Found {len(data.get('foods', []))} match(es)")
            if data.get('foods'):
                print(f"[LIVE_API] Best Match: {data['foods'][0].get('description')}")
            print("-" * 50)
            # ----------------------------------
            
            foods = data.get("foods", [])
            if not foods:
                return None
                
            best = foods[0]
            result = {
                "name": best.get("description", food_name).title(),
                "protein": 0.0,
                "fiber": 0.0,
                "carbs": 0.0,
                "sugar": 0.0,
                "calories": 0.0,
                "nutrients": {} 
            }

            for nut in best.get("foodNutrients", []):
                n_id = nut.get("nutrientId")
                val = nut.get("value", 0.0)
                
                # Internal nutrients map for the engine
                for key, target_id in self.NUTRIENT_IDS.items():
                    if n_id == target_id:
                        result["nutrients"][key] = val
                
                # Energy fallback
                if nut.get("nutrientName", "").lower() == "energy" and nut.get("unitName", "").lower() == "kcal":
                    result["calories"] = val
                    result["nutrients"]["calories"] = val

            # Top-level mapping for user request
            result["protein"] = result["nutrients"].get("protein", 0.0)
            result["fiber"] = result["nutrients"].get("fiber", 0.0)
            result["carbs"] = result["nutrients"].get("carbohydrates", 0.0)
            result["sugar"] = result["nutrients"].get("sugar", 0.0)
            result["calories"] = result["nutrients"].get("calories", result["calories"])

            return result

        except Exception as e:
            logger.warning(f"USDA_LOADER | API Failure for {food_name}: {e}")
            return None

    def fetch_from_local_json(self, food_name: str) -> Optional[dict]:
        """
        Fallback source: Search Indian Overrides first, then local Foundation dataset.
        """
        name_clean = food_name.lower()
        
        # 1. Check Indian Overrides (Cuisine Specialization)
        if name_clean in self.INDIAN_OVERRIDES:
            return self.INDIAN_OVERRIDES[name_clean]
        for key, val in self.INDIAN_OVERRIDES.items():
            if key in name_clean:
                return val

        # 2. Check USDA Foundation Dataset
        if not self.local_index:
            self._load_local_index()
            
        for fid, food in self.local_index.items():
            # Match strictly first, then fuzzy
            if food["name"].lower() == name_clean or name_clean in food["name"].lower():
                return {
                    "name": food["name"],
                    "protein": food["nutrients"].get("protein", 0.0),
                    "fiber": food["nutrients"].get("fiber", 0.0),
                    "carbs": food["nutrients"].get("carbohydrates", 0.0),
                    "sugar": food["nutrients"].get("sugar", 0.0),
                    "calories": food.get("calories", 0.0),
                    "nutrients": food["nutrients"]
                }
        return None

    def get_top_foods(self, nutrient_key: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Returns top sources for a given nutrient from the indexed Foundation dataset."""
        if not self.local_index:
            self._load_local_index()
            
        if nutrient_key not in self.nutrient_rankings:
            return []
            
        rankings = self.nutrient_rankings[nutrient_key]
        results = []
        for fdc_id, amount in rankings:
            if len(results) >= limit: break
            
            food = self.local_index[fdc_id]
            if amount > 0:
                results.append({
                    "name": food["name"],
                    "amount": amount,
                    "calories": food["calories"],
                    "fdc_id": fdc_id
                })
        return results

    def _load_local_index(self):
        """Loads and indexes foundations foods with rankings support."""
        self.local_index = {}
        self.nutrient_rankings = {k: [] for k in self.NUTRIENT_IDS.keys()}
        
        if not os.path.exists(self.json_path):
            logger.error(f"USDA_LOADER | Local JSON not found at {self.json_path}")
            return

        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            foods = data.get("FoundationFoods", [])
            for f in foods:
                fdc_id = f.get("fdcId")
                desc = f.get("description", "Unknown")
                nuts = f.get("foodNutrients", [])
                
                food_data = {"name": desc, "nutrients": {}, "calories": 0.0}
                for n_entry in nuts:
                    nut_obj = n_entry.get("nutrient", {})
                    name = nut_obj.get("name")
                    amount = n_entry.get("amount", 0.0)
                    
                    # Mapping logic matching internal keys
                    internal_key = None
                    if name == "Protein": internal_key = "protein"
                    elif name == "Fiber, total dietary": internal_key = "fiber"
                    elif name == "Sugars, Total": internal_key = "sugar"
                    elif name == "Carbohydrate, by difference": internal_key = "carbohydrates"
                    elif name == "Iron, Fe": internal_key = "iron"
                    elif name == "Potassium, K": internal_key = "potassium"
                    elif name == "Sodium, Na": internal_key = "sodium"
                    elif name == "Calcium, Ca": internal_key = "calcium"
                    elif name == "Magnesium, Mg": internal_key = "magnesium"
                    elif name == "Zinc, Zn": internal_key = "zinc"
                    elif name == "Vitamin C, total ascorbic acid": internal_key = "vitamin_c"
                    elif name == "Vitamin B-12": internal_key = "vitamin_b12"
                    
                    if internal_key:
                        food_data["nutrients"][internal_key] = amount
                        self.nutrient_rankings[internal_key].append((fdc_id, amount))
                        
                    if name == "Energy" and nut_obj.get("unitName") == "kcal": 
                        food_data["calories"] = amount
                
                self.local_index[fdc_id] = food_data

            # Sort rankings
            for key in self.nutrient_rankings:
                self.nutrient_rankings[key].sort(key=lambda x: x[1], reverse=True)
                
            logger.info(f"USDA_LOADER | Successfully indexed {len(self.local_index)} foods and rankings.")
        except Exception as e:
            logger.error(f"USDA_LOADER | Failed to index local JSON: {e}")

# Singleton instance
usda_loader = USDALoader()
