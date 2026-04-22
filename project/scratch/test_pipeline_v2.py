import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")

load_dotenv()

from backend.nutrient_pipeline import get_enriched_food_profile

def run_test():
    test_dishes = [
        "Paneer Butter Masala",  # Should hit Cache (Confidence 0.95) + USDA Cache/API
        "Masala Egg Curry",      # Should hit Inferred (Confidence 0.7) + USDA
        "Random Garbage 456"     # Low confidence raw fallback
    ]
    
    print("\nStarting Full Pipeline Confidence Test...")
    print("-" * 60)
    
    for dish in test_dishes:
        print(f"\nProcessing: {dish}")
        profile = get_enriched_food_profile(dish)
        
        print(f"Final Confidence Score: {profile['meta']['confidence']}")
        print(f"Calculation Basis: {profile['meta']['source'].upper()} with {profile['meta']['ingredient_count']} ingredients")
        print(f"Calories: {profile['nutrients']['calories']}")
        print("-" * 40)

if __name__ == "__main__":
    run_test()
