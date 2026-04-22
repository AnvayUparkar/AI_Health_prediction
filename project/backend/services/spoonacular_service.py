import os
import requests
import logging

logger = logging.getLogger(__name__)

API_KEY = os.getenv("SPOONACULAR_API_KEY")
BASE_URL = "https://api.spoonacular.com/recipes/complexSearch"

def get_ingredients_from_spoonacular(dish_name: str) -> list:
    """
    Extracts base ingredients from a complex dish name using Spoonacular.
    Returns a list of ingredient strings.
    """
    if not API_KEY:
        logger.warning("Spoonacular API key not found. Ensure SPOONACULAR_API_KEY is in .env")
        return []

    try:
        response = requests.get(
            BASE_URL,
            params={
                "query": dish_name,
                "number": 1,
                "addRecipeInformation": True,
                "fillIngredients": True,
                "apiKey": API_KEY
            },
            timeout=3
        )
        response.raise_for_status()

        data = response.json()

        if not data.get("results"):
            return []

        recipe = data["results"][0]
        
        ingredients = [
            ing.get("name", "").lower().strip()
            for ing in recipe.get("extendedIngredients", [])
        ]
        
        return list(set(ingredients)) # basic normalization

    except Exception as e:
        print("Spoonacular API failed:", e)
        return []
