
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class ClinicalValidator:
    """
    Architect-Level Component: Mandatory Nutrient Injection & Hard Validation [Step 7].
    Implements Step 2 Condition Rules and Step 12 Lifestyle logic.
    """

    # Step 2: Protocol Definition
    CONDITION_RULES = {
        "vitamin_b12_deficiency": {
            "sources": ["milk", "curd", "paneer", "eggs", "fortified"],
            "min_meals": 2,
            "fix_food": "High-B12 Fortified Milk",
            "tag": "B12"
        },
        "hypocalcemia": {
            "sources": ["milk", "curd", "buttermilk", "sesame", "paneer"],
            "min_meals": 2,
            "fix_food": "High-Calcium Probiotic Curd",
            "tag": "Calcium"
        },
        "low_hdl": {
            "sources": ["almonds", "walnuts", "flaxseed", "chia"],
            "min_meals": 1,
            "fix_food": "Omega-rich Walnut Garnish",
            "tag": "Omega-3"
        },
        "iron_deficiency_anemia": {
            "sources": ["palak", "spinach", "beetroot", "lentils", "ragi", "bajra"],
            "min_meals": 2,
            "requires": "vitamin_c",
            "synergy_fix": "Fresh Lemon & Amla Garnish",
            "tag": "Iron"
        },
        "vitamin_d_deficiency": {
            "lifestyle": "15-20 minutes sunlight exposure daily",
            "sources": ["fortified milk", "mushrooms", "egg yolk"],
            "fix_food": "D-Fortified Milk"
        }
    }

    def validate_and_fix(self, meal_plan: Dict[str, Any], conditions: List[str]) -> Dict[str, Any]:
        """
        Main orchestration for clinical validation [Step 7].
        Returns the optimized and corrected meal plan.
        """
        logger.info("VALIDATOR | Auditing clinical plan for conditions: %s", conditions)
        
        # 1. Clear any leftover placeholders [Step 10]
        self._remove_placeholders(meal_plan)

        # 2. Daily Requirement Audit
        for cond in conditions:
            if cond in self.CONDITION_RULES:
                rule = self.CONDITION_RULES[cond]
                meal_plan = self._enforce_rule(meal_plan, cond, rule)

        # 3. Synergy & Lifestyle [Step 12]
        lifestyle_tips = []
        if "vitamin_d_deficiency" in conditions:
            lifestyle_tips.append(self.CONDITION_RULES["vitamin_d_deficiency"]["lifestyle"])
        
        meal_plan["lifestyle_recommendations"] = lifestyle_tips
        
        return meal_plan

    def _remove_placeholders(self, meal_plan: Dict[str, Any]):
        """Ensures NO 'Balanced Clinical Intake' strings remain."""
        for slot, meal in meal_plan.items():
            if meal.get("title") == "Balanced Clinical Intake":
                meal["title"] = "Clinical Nutrient-Dense Meal"
                meal["components"] = {"Main": "Moong Dal Khichdi", "Side": "Fresh Curd"}

    def _enforce_rule(self, meal_plan: Dict[str, Any], cond: str, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Checks counts and injects fixes where counts are low."""
        sources = rule.get("sources", [])
        min_meals = rule.get("min_meals", 0)
        
        present_count = 0
        for slot, meal in meal_plan.items():
            comp_str = " ".join(meal["components"].values()).lower()
            if any(src in comp_str for src in sources):
                present_count += 1
        
        # Injection Logic
        while present_count < min_meals:
            # Find a slot to inject
            target_slot = self._find_injection_slot(meal_plan, cond)
            if target_slot:
                fix = rule.get("fix_food", "Nutrient Booster")
                # Add to components
                meal_plan[target_slot]["components"]["Clinical Support"] = fix
                # Append to tags if relevant
                if "tag" in rule:
                    if rule["tag"] not in meal_plan[target_slot]["nutrient_tags"]:
                        meal_plan[target_slot]["nutrient_tags"].append(rule["tag"])
                present_count += 1
                logger.info("VALIDATOR | Injected %s into %s for %s", fix, target_slot, cond)
            else:
                break
                
        # Synergy Injection (Iron + Vit C)
        if cond == "iron_deficiency_anemia":
            meal_plan = self._apply_synergy(meal_plan, rule)
            
        return meal_plan

    def _find_injection_slot(self, meal_plan: Dict[str, Any], cond: str) -> Optional[str]:
        """Identifies logical slots for specific nutrient injections."""
        preferred_slots = ["lunch", "dinner", "breakfast"]
        for slot in preferred_slots:
            if slot in meal_plan:
                # Avoid double injecting same clinical support if already present
                if "Clinical Support" not in meal_plan[slot]["components"]:
                    return slot
        return None

    def _apply_synergy(self, meal_plan: Dict[str, Any], rule: Dict[str, Any]) -> Dict[str, Any]:
        """Ensures every iron-rich meal has the absorption synergy [Step 4]."""
        synergy_fix = rule.get("synergy_fix", "Absorption Garnish")
        iron_sources = rule.get("sources", [])
        
        for slot, meal in meal_plan.items():
            comp_str = " ".join(meal["components"].values()).lower()
            if any(src in comp_str for src in iron_sources):
                if "Absorption" not in meal["components"]:
                    meal["components"]["Absorption"] = synergy_fix
        return meal_plan

# Singleton
clinical_validator = ClinicalValidator()
