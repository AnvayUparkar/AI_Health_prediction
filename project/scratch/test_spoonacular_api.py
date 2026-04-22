import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")

load_dotenv()

from backend.services.dish_mapper import get_ingredients

def run_test():
    test_dishes = [
        "Oats Upma",             # Should hit Static
        "Paneer Butter Masala",  # Should hit Spoonacular
        "Keto Avocado Salad"     # Should hit Spoonacular/Inferred
    ]
    
    print("\nStarting Spoonacular Integration Test...")
    print("-" * 50)
    
    for dish in test_dishes:
        print(f"\nTesting Dish: {dish}")
        ingredients, source = get_ingredients(dish)
        print(f"Source Used: {source.upper()}")
        print(f"Extracted Ingredients: {ingredients}")
        print("-" * 30)

if __name__ == "__main__":
    if not os.getenv("SPOONACULAR_API_KEY"):
        print("❌ ERROR: SPOONACULAR_API_KEY not found in .env file.")
        print("Please add 'SPOONACULAR_API_KEY=your_key' to your .env to run this test.")
    else:
        run_test()
