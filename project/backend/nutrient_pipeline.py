"""
Nutrient Pipeline: Full Integration Layer

Pipeline Flow:
  dietary_knowledge.json (clinical intent)
    -> Food candidates
    -> Spoonacular / Dish Mapper (ingredient decomposition)
    -> USDA API (nutrition per ingredient)
    -> Nutrient Aggregation
    -> Validation (clinical safety)
    -> Return enriched food profiles

This module DOES NOT modify clinical reasoning logic.
It ONLY provides accurate nutrient profiles for dishes
by decomposing them into ingredients first.
"""

import logging
from typing import Dict, List, Any, Optional

from backend.usda_manager import usda_manager
from backend.services.dish_mapper import get_ingredients

logger = logging.getLogger(__name__)


def aggregate_nutrients(nutrient_list: List[dict]) -> dict:
    """
    Sums up nutrient values across a list of USDA ingredient profiles.
    Each item in nutrient_list is a USDA-format dict with top-level keys
    (protein, fiber, carbs, sugar, calories) and a nested 'nutrients' dict.
    """
    total = {
        "calories": 0, "protein": 0, "fiber": 0,
        "carbs": 0, "sugar": 0
    }
    detailed = {}

    for item in nutrient_list:
        if not item:
            continue
        for key in total:
            total[key] += item.get(key, 0) or 0

        # Also aggregate the detailed nutrients dict
        nested = item.get("nutrients", {})
        for nk, nv in nested.items():
            if isinstance(nv, (int, float)):
                detailed[nk] = detailed.get(nk, 0) + nv

    return {
        "calories": total["calories"],
        "protein": total["protein"],
        "fiber": total["fiber"],
        "carbs": total["carbs"],
        "sugar": total["sugar"],
        "nutrients": detailed
    }


def get_enriched_food_profile(food_name: str) -> dict:
    """
    Full pipeline for a single food/dish:
      1. Decompose dish into ingredients (Spoonacular/Static/Inferred)
      2. Fetch USDA nutrients for each ingredient
      3. Aggregate into a single profile
    
    Returns:
        {
            "name": "paneer butter masala",
            "ingredients": ["paneer", "butter", "tomato", ...],
            "nutrients": { aggregated USDA data },
            "source": "spoonacular" | "static" | "inferred" | "raw"
        }
    """
    # Step 1: Decompose
    ingredients, source = get_ingredients(food_name)
    print(f"[PIPELINE] {food_name} -> decomposed via {source.upper()} -> {ingredients}")

    # Step 2: Fetch USDA data per ingredient
    nutrient_data = []
    for ingredient in ingredients:
        data = usda_manager.get_food_nutrients(ingredient)
        nutrient_data.append(data)

    # Step 3: Aggregate
    combined = aggregate_nutrients(nutrient_data)

    return {
        "name": food_name,
        "ingredients": ingredients,
        "nutrients": combined,
        "source": source
    }


def build_food_profiles(condition: str, knowledge_manager) -> List[dict]:
    """
    Full pipeline for a clinical condition:
      1. Get target nutrients from knowledge base
      2. Get candidate foods from knowledge base
      3. For each food: decompose -> USDA fetch -> aggregate
      4. Filter unsafe foods
    
    Args:
        condition: Clinical condition string (e.g., "iron_deficiency_anemia")
        knowledge_manager: The DietKnowledgeManager instance (expert_kb)
    
    Returns:
        List of enriched food profile dicts
    """
    # Step 1: Knowledge Base -> Target Nutrients
    nutrients = knowledge_manager.get_nutrients_for_conditions([condition])
    print(f"[PIPELINE] Condition '{condition}' -> target nutrients: {nutrients}")

    # Step 2: Knowledge Base -> Candidate Foods
    foods = knowledge_manager.get_foods_for_nutrients(nutrients)
    print(f"[PIPELINE] Found {len(foods)} candidate foods")

    # Step 3: Enrich each food
    enriched_foods = []
    for food in foods:
        profile = get_enriched_food_profile(food)
        enriched_foods.append(profile)

    # Step 4: Filter unsafe
    avoid_map = knowledge_manager.get_avoid_data([condition])
    safe_foods = filter_unsafe_foods(enriched_foods, avoid_map)

    print(f"[PIPELINE] {len(enriched_foods)} candidates -> {len(safe_foods)} after safety filter")
    return safe_foods


def filter_unsafe_foods(foods: List[dict], avoid_map: Dict[str, str]) -> List[dict]:
    """
    Removes foods that are clinically contraindicated.
    Checks both the dish name AND its decomposed ingredients.
    """
    avoid_set = set(k.lower() for k in avoid_map.keys())
    safe = []

    for food in foods:
        name = food["name"].lower()
        ingredients = [i.lower() for i in food.get("ingredients", [])]

        # Block if the dish name itself is avoided
        if name in avoid_set:
            print(f"[PIPELINE SAFETY] Blocked '{name}' (dish name in avoid list)")
            continue

        # Block if any ingredient is in avoid list
        blocked_ingredient = None
        for ing in ingredients:
            if ing in avoid_set:
                blocked_ingredient = ing
                break

        if blocked_ingredient:
            print(f"[PIPELINE SAFETY] Blocked '{name}' (ingredient '{blocked_ingredient}' is contraindicated)")
            continue

        safe.append(food)

    return safe


def get_meal_nutrition_summary(meal_components: Dict[str, str]) -> dict:
    """
    Takes a structured meal (from IndianMealBuilder) and computes
    aggregate nutrition across all components.
    
    Args:
        meal_components: {"Roti": "Bajra Roti", "Sabzi": "Palak Sabzi", ...}
    
    Returns:
        Aggregated nutrient profile for the entire meal
    """
    all_profiles = []

    for slot, dish_name in meal_components.items():
        if not dish_name:
            continue
        profile = get_enriched_food_profile(dish_name)
        all_profiles.append(profile["nutrients"])

    return aggregate_nutrients(
        # Re-wrap so aggregate_nutrients can process them
        [{"calories": p.get("calories", 0), "protein": p.get("protein", 0),
          "fiber": p.get("fiber", 0), "carbs": p.get("carbs", 0),
          "sugar": p.get("sugar", 0), "nutrients": p.get("nutrients", {})}
         for p in all_profiles]
    )
