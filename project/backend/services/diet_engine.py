
import logging
from backend.services.usda_service import usda_service
from backend.services.food_classifier import food_classifier
from backend.services.diet_filter import diet_filter
from backend.services.meal_generator import meal_generator
from backend.services.meal_explainer import meal_explainer

logger = logging.getLogger(__name__)

def generate_diet_plan_modular(patient_data: dict):
    """
    Modular Orchestration Pipeline:
    USDA Search -> Classification -> Filtering -> Meal Gen -> Explainer
    """
    logger.info("DIET_ENGINE | Starting modular diet generation pipeline.")
    
    try:
        # 1. USDA Search (Fetch nutritional raw data)
        # Use a diverse set of base ingredients to start with
        search_query = "oats, lentils, rice, spinach, apple, walnut, chicken breast, broccoli, dal"
        raw_foods = usda_service.search_foods(search_query)
        
        if not raw_foods:
            logger.warning("DIET_ENGINE | USDA API returned no data. Pipeline halted.")
            return {"error": "Failed to fetch nutritional data from USDA."}

        # 2. Classification (Meta-tagging)
        classified = food_classifier.classify_foods(raw_foods)
        
        # 3. Filtering (Condition matching)
        filtered = diet_filter.filter_foods(patient_data, classified)
        
        if not filtered:
            logger.warning("DIET_ENGINE | Filtering resulted in empty list. Using general wellness fallback.")
            filtered = classified

        # 4. Meal Assembly (Bucket into slots)
        meals = meal_generator.generate_meals(filtered)
        
        # 5. Clinical Explanation (Add reasoning)
        explained = meal_explainer.add_explanations(meals, patient_data)
        
        return explained

    except Exception as e:
        logger.error(f"DIET_ENGINE | Pipeline failure: {e}")
        return {"error": str(e)}
