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


def aggregate_confidence(ingredient_metadata: List[dict], dish_source_meta: dict) -> float:
    """
    Calculates overall dish confidence based on:
    1. The decomposition source (DishMapper confidence)
    2. The USDA grounding quality (Ingredient-level confidence)
    """
    if not ingredient_metadata:
        return dish_source_meta.get("confidence", 0.5)

    # Calculate mean ingredient confidence
    avg_ing_confidence = sum(m["confidence"] for m in ingredient_metadata) / len(ingredient_metadata)
    
    # Combined score: 60% decomposition quality, 40% ingredient grounding quality
    overall = (dish_source_meta.get("confidence", 0.5) * 0.6) + (avg_ing_confidence * 0.4)
    
    return round(overall, 2)


LOW_CONFIDENCE_THRESHOLD = 0.6
MODERATE_CONFIDENCE_THRESHOLD = 0.75

def classify_confidence(confidence: float) -> str:
    """Classifies confidence score into discrete clinical reliability levels."""
    if confidence >= MODERATE_CONFIDENCE_THRESHOLD:
        return "high_confidence"
    elif confidence >= LOW_CONFIDENCE_THRESHOLD:
        return "moderate_confidence"
    else:
        return "low_confidence"

def generate_safety_response(confidence: float) -> dict:
    """
    Generates an actionable safety response based on confidence level.
    Provides proactive clinical guidance for the end-user.
    """
    level = classify_confidence(confidence)

    if level == "high_confidence":
        return {
            "status": "safe",
            "level": level,
            "message": "High confidence in dietary estimation.",
            "action": "Proceed with recommended meal plan."
        }
    elif level == "moderate_confidence":
        return {
            "status": "caution",
            "level": level,
            "message": "Moderate confidence. Minor uncertainty detected.",
            "action": "Monitor patient response and re-evaluate if needed."
        }
    else:
        return {
            "status": "warning",
            "level": level,
            "message": "Low confidence in estimation.",
            "action": "Manual review recommended. Verify ingredients or select a known dish."
        }


def get_enriched_food_profile(food_name: str) -> dict:
    """
    Full pipeline for a single food/dish:
      1. Decompose dish into ingredients (Spoonacular/Static/Inferred)
      2. Fetch USDA nutrients + Metadata for each ingredient
      3. Aggregate nutrients and Confidence scores
    """
    # Step 1: Decompose
    result = get_ingredients(food_name)
    ingredients, source = result["ingredients"], result["meta"]["source"]
    dish_meta = result["meta"]

    # Step 2: Fetch USDA data + Meta per ingredient
    nutrient_data = []
    ingredient_meta = []
    
    for ingredient in ingredients:
        data, meta = usda_manager.get_food_nutrients_with_meta(ingredient)
        nutrient_data.append(data)
        ingredient_meta.append(meta)

    # Step 3: Aggregate
    combined_nutrients = aggregate_nutrients(nutrient_data)
    overall_confidence = aggregate_confidence(ingredient_meta, dish_meta)
    
    # Step 4: Safety Check (Multi-Level Classification)
    safety = generate_safety_response(overall_confidence)
    
    # Debug Logging for Clinical Traceability
    print(f"[PIPELINE] {food_name} | Confidence: {overall_confidence} | Level: {safety['level'].upper()}")
    print(f"[PIPELINE SAFETY] Action: {safety['action']}")

    return {
        "name": food_name,
        "ingredients": ingredients,
        "nutrients": combined_nutrients,
        "meta": {
            "source": source,
            "confidence": overall_confidence,
            "safety": safety,
            "ingredient_count": len(ingredients)
        }
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


def calculate_diet_plan_confidence(meal_plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculates the overall confidence score for a complete diet plan.
    Aggregates confidence from all unique dishes across all meals.
    Returns both overall stats and granular per-dish profiles.
    """
    unique_dishes = set()
    # Handle both list and dict formats of meal plan
    for slot, dishes in meal_plan.items():
        if isinstance(dishes, list):
            for dish in dishes:
                if isinstance(dish, str):
                    unique_dishes.add(dish)
        elif isinstance(dishes, dict):
            # If dishes is a complex object (like MealDish)
            title = dishes.get("title")
            if title:
                unique_dishes.add(title)
            
            # 🧠 NEW: For deterministic thalis, also track individual components
            # This ensures "Palak Sabzi" gets a clinical trace even if the meal title is generic.
            components = dishes.get("components", {})
            if isinstance(components, dict):
                for comp_val in components.values():
                    if isinstance(comp_val, str):
                        unique_dishes.add(comp_val)
    
    if not unique_dishes:
        return {
            "confidence": 0.5,
            "safety": generate_safety_response(0.5),
            "dish_profiles": {}
        }
    
    confidences = []
    dish_profiles = {}
    for dish in unique_dishes:
        profile = get_enriched_food_profile(dish)
        confidences.append(profile["meta"]["confidence"])
        dish_profiles[dish] = {
            "ingredients": profile["ingredients"],
            "confidence": profile["meta"]["confidence"],
            "source": profile["meta"]["source"]
        }
    
    overall_confidence = round(sum(confidences) / len(confidences), 2)
    safety = generate_safety_response(overall_confidence)
    
    return {
        "confidence": overall_confidence,
        "safety": safety,
        "dish_profiles": dish_profiles
    }
