"""
Full Pipeline Integration Test.
Tests: Knowledge Base -> Decomposition -> USDA -> Aggregation -> Safety Filter
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

from backend.nutrient_pipeline import (
    get_enriched_food_profile,
    build_food_profiles,
    aggregate_nutrients,
    filter_unsafe_foods
)
from backend.fallback_diet_engine import expert_kb

def test_single_dish():
    print("=" * 60)
    print("TEST 1: Single Dish Decomposition + USDA Aggregation")
    print("=" * 60)

    dishes = ["oats upma", "paneer butter masala", "spinach"]

    for dish in dishes:
        print(f"\n--- Testing: {dish} ---")
        profile = get_enriched_food_profile(dish)
        print(f"  Ingredients ({profile['source']}): {profile['ingredients']}")
        n = profile["nutrients"]
        print(f"  Calories: {n['calories']}, Protein: {n['protein']}g, Fiber: {n['fiber']}g")
        print(f"  Detailed keys: {list(n.get('nutrients', {}).keys())[:5]}...")


def test_condition_pipeline():
    print("\n" + "=" * 60)
    print("TEST 2: Full Condition Pipeline (iron_deficiency_anemia)")
    print("=" * 60)

    profiles = build_food_profiles("iron_deficiency_anemia", expert_kb)
    print(f"\nTotal safe food profiles: {len(profiles)}")
    for p in profiles[:5]:
        n = p["nutrients"]
        print(f"  {p['name']:25s} | Cal:{n['calories']:6.0f} | Pro:{n['protein']:5.1f}g | Source:{p['source']}")


def test_safety_filter():
    print("\n" + "=" * 60)
    print("TEST 3: Safety Filter")
    print("=" * 60)

    fake_foods = [
        {"name": "spinach", "ingredients": ["spinach"], "nutrients": {}, "source": "raw"},
        {"name": "refined sugar", "ingredients": ["sugar"], "nutrients": {}, "source": "raw"},
        {"name": "dal makhani", "ingredients": ["lentils", "butter", "cream"], "nutrients": {}, "source": "spoonacular"},
    ]
    avoid = {"refined sugar": "High glycemic index", "cream": "Saturated fat"}

    safe = filter_unsafe_foods(fake_foods, avoid)
    print(f"  Input: {len(fake_foods)} foods, Output: {len(safe)} safe foods")
    for s in safe:
        print(f"    PASS: {s['name']}")


if __name__ == "__main__":
    test_single_dish()
    test_condition_pipeline()
    test_safety_filter()
    print("\n[DONE] All pipeline tests complete.")
