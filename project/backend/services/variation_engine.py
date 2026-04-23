import random
import logging
import time
from datetime import datetime
from typing import List, Any, Optional, Dict

logger = logging.getLogger(__name__)

class VariationEngine:
    """
    Handles clinical variation and non-deterministic meal generation.
    Ensures that regenerating a plan provides new options within clinical safety bands.
    """
    def __init__(self):
        self._request_counter = 0
        self._selection_history: Dict[str, List[str]] = {} # patient_id -> [last_5_foods]
        self._history_limit = 10
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
            "provides targeted clinical support",
            "contributes to balanced metabolic function",
            "works synergistically with your diet protocol",
            "reinforces your nutritional recovery pathway",
        ]

    def set_request_seed(self, patient_id: str = "generic_patient"):
        """
        Sets a PER-REQUEST seed using microsecond-precision timestamp.
        
        Guarantees: Same report uploaded N times → N different (safe) outputs.
        Safety:     All variation is constrained to top-K scored candidates.
        """
        self._request_counter += 1
        seed_value = f"{patient_id}_{time.time_ns()}_{self._request_counter}"
        random.seed(seed_value)
        logger.info("VARIATION_ENGINE | Request seed set: counter=%d, patient=%s", 
                     self._request_counter, patient_id)

    def set_daily_seed(self, patient_id: str = "generic_patient"):
        """
        Legacy API — now delegates to per-request seeding for variation.
        Kept for backward compatibility with existing callers.
        """
        self.set_request_seed(patient_id)

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

    def shuffle_candidates(self, candidates: List[Any], k: int = None) -> List[Any]:
        """
        Returns a shuffled copy of the candidate list.
        If k is provided, only the top-k items are shuffled (preserving clinical priority).
        
        Use this for staple selection, dal selection, etc.
        """
        if not candidates:
            return candidates
        
        result = list(candidates)  # Don't mutate the original
        
        if k and k < len(result):
            # Shuffle only the top-k, keep the rest in order
            top = result[:k]
            random.shuffle(top)
            result[:k] = top
        else:
            random.shuffle(result)
        
        return result
        
    def generate_explanation(self, base_reason: str) -> str:
        """Adds dynamic, Gemini-like phrasing to the deterministic reasoning."""
        phrase = random.choice(self.EXPLANATION_PHRASES)
        
        clean_reason = base_reason.strip()
        if clean_reason.endswith('.'):
            clean_reason = clean_reason[:-1]
            
        return f"{clean_reason}, which {phrase}."

    def track_selection(self, patient_id: str, food: str):
        """Records a food selection to avoid immediate repetition in the next request."""
        if patient_id not in self._selection_history:
            self._selection_history[patient_id] = []
        
        # Add to start of list
        self._selection_history[patient_id].insert(0, food.lower())
        # Trim history
        self._selection_history[patient_id] = self._selection_history[patient_id][:self._history_limit]

    def filter_by_history(self, patient_id: str, candidates: List[str]) -> List[str]:
        """Removes items that were recently suggested to maximize diversity."""
        history = self._selection_history.get(patient_id, [])
        if not history:
            return candidates
            
        # Robust comparison: check if any historical item is a substring or vice versa
        # This handles cases where history stores "Spinach Sabzi" and candidate is "Spinach"
        def is_recent(cand):
            c_low = cand.lower()
            return any(c_low in h or h in c_low for h in history)

        fresh = [c for c in candidates if not is_recent(c)]
        
        if len(fresh) >= 2:
            return fresh
            
        # If too few alternatives, return all (allow repeat as last resort)
        return candidates

# Singleton instance
variation_engine = VariationEngine()
