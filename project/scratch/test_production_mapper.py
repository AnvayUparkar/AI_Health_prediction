import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")

load_dotenv()

from backend.services.dish_mapper import get_ingredients

def run_test():
    test_dishes = [
        "Oats Upma",             # Static
        "Paneer Butter Masala",  # Cache
        "Masala Egg Curry",      # Should hit Inferred (Rule-based)
        "Random Garbage 123"     # Should hit Raw
    ]
    
    print("\nStarting Production-Grade Mapper Test...")
    print("-" * 50)
    
    for dish in test_dishes:
        print(f"\nTesting Dish: {dish}")
        result = get_ingredients(dish)
        
        # Test Unpacking (Backward Compatibility)
        ingredients, source = result
        
        print(f"Source Used: {source.upper()}")
        print(f"Confidence: {result['meta']['confidence']}")
        print(f"Extracted Ingredients: {ingredients}")
        print("-" * 30)

if __name__ == "__main__":
    run_test()
