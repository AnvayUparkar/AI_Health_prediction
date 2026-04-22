import random
import logging
from datetime import datetime
from typing import List, Any, Optional

logger = logging.getLogger(__name__)

class VariationEngine:
    """
    Controlled Variability Layer.
    Adds safe variation to deterministic outputs, ensuring that 
    the same clinical input can produce slightly different, yet 
    clinically safe and USDA-backed meal plans.
    """
    
    def __init__(self):
        # Basic history cache: patient_id -> set of recent meals (Diversity tracking)
        self.history_cache = {} 
        
        # Meal Options Bank for structured fallback variability
        self.MEAL_OPTIONS = {
            "LOW_GLYCEMIC_CONTROL": {
                "breakfast": ["Oats Upma", "Vegetable Daliya", "Moong Dal Chilla"],
                "lunch": ["Brown Rice + Dal", "Multigrain Roti + Sabzi"],
                "dinner": ["Lauki Sabzi + Roti", "Vegetable Khichdi"]
            }
        }
        
        self.EXPLANATION_PHRASES = [
            "helps regulate your markers",
            "supports systemic stability",
            "optimizes your nutritional intake",
            "aids in maintaining metabolic balance",
            "ensures safe and steady energy levels",
            "provides targeted clinical support"
        ]

    def set_daily_seed(self, patient_id: str = "generic_patient"):
        """
        Sets a day-based seed. 
        Same patient + same day = consistent output.
        Different day = variation.
        """
        seed_value = f"{patient_id}_{datetime.now().date()}"
        random.seed(seed_value)
        logger.info("VARIATION_ENGINE | Set daily seed for patient: %s", patient_id)

    def select_meal_option(self, food_list: List[Any], k: int = 5) -> Optional[Any]:
        """
        Selects a random option from the top-k foods.
        Ensures we only pick from the highest-scoring (safest) options.
        """
        if not food_list:
            return None
            
        if len(food_list) <= k:
            return random.choice(food_list)
            
        top_k = food_list[:k]
        return random.choice(top_k)
        
    def generate_explanation(self, base_reason: str) -> str:
        """Adds dynamic, Gemini-like phrasing to the deterministic reasoning."""
        phrase = random.choice(self.EXPLANATION_PHRASES)
        
        clean_reason = base_reason.strip()
        if clean_reason.endswith('.'):
            clean_reason = clean_reason[:-1]
            
        return f"{clean_reason}, which {phrase}."

# Singleton instance
variation_engine = VariationEngine()
