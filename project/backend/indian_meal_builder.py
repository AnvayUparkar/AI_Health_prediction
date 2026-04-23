
import logging
from typing import List, Dict, Any, Optional
from backend.usda_manager import usda_manager
from backend.services.dish_name_generator import generate_dish_name, generate_component_name, COOKING_STYLE

logger = logging.getLogger(__name__)

class IndianMealBuilder:
    """
    Architect-Level Component: Enforces STRICT Indian Meal Structure [Steps 3, 5, 6, 8, 9].
    Transitions from ingredient generation to deterministic dish construction.
    """

    # 1. High-Precision Dish Library (Step 9 - Localization)
    DISH_MAP = {
        "spinach": "Palak Sabzi with Garlic & Cumin",
        "palak": "Spiced Palak Sabzi",
        "beetroot": "Roasted Beetroot & Coconut Sabzi",
        "moringa": "Superfood Moringa Leaf Soup",
        "broccoli": "Stir-fried Spiced Broccoli Sabzi",
        "bitter gourd": "Karela Masala (Low Oil)",
        "bottle gourd": "Lauki Ki Sabzi (Digestive Support)",
        "cabbage": "Cabbage & Green Pea Poriyal",
        "carrot": "Gajar-Matar Dry Sabzi",
        "methi": "Methi-Thepla Style Sabzi",
        "moong dal": "Yellow Moong Dal Tadka",
        "masoor dal": "Masoor Protein Curry",
        "chana dal": "High-Fiber Chana Dal",
        "paneer": "Soft Paneer Matar Curry",
        "soy": "Soybean Chunk Curry",
        "egg": "Spiced Egg Bhurji",
        "sprouts": "Moong Sprouts Chaat",
        "poha": "Vegetable Poha with Peanuts",
        "upma": "Semolina / Oats Upma",
        "ragi": "Ragi Porridge / Malt",
        "oats": "Savory Oats with Veggies",
        "chia seeds": "Chia Seed & Almond Pudding",
        "flaxseeds": "Roasted Seed Garnish",
        "walnuts": "Walnut & Herb Chutney",
        "makhana": "Roasted Spiced Makhana",
        "pomegranate": "Fresh Pomegranate Bowl",
        "apple": "Seasonal Apple Slices",
        "curd": "Probiotic Fresh Curd",
        "buttermilk": "Spiced Masala Buttermilk",
        "milk": "High-Calcium Low-Fat Milk",
        "dalia": "Vegetable Dalia Khichdi",
        "groundnut": "Peanut / Groundnut Chutney"
    }

    # Step 9: Localization Map (Western -> Indian)
    LOCALIZATION_MAP = {
        "kale": "palak",
        "barley": "dalia",
        "peanut butter": "groundnut",
        "salmon": "paneer",  # High-protein clinical swap
        "greek yogurt": "curd",
        "quinoa": "dalia"
    }

    def build_meal(self, top_foods: List[str], meal_type: str, conditions: List[str], used_items: Optional[Dict[str, set]] = None, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Builds a meal following NON-NEGOTIABLE structural templates [Step 3].
        Includes Step 4 personalization based on primary condition.
        """
        meal_type = meal_type.lower()
        if used_items is None: used_items = {"staples": set(), "dals": set(), "sabzis": set()}
        primary = context.get("primary_condition") if context else None
        
        # Apply Localization Step 9
        clean_foods = []
        for f in top_foods:
            f_clean = f.split('(')[0].strip().lower()
            for western, indian in self.LOCALIZATION_MAP.items():
                if western in f_clean:
                    f_clean = f_clean.replace(western, indian)
            clean_foods.append(f_clean)

        # [Step 4] Personalization - Inject Mandatory Clinical Ingredients
        if primary == "iron_deficiency_anemia":
            # Force high-iron candidates into top of search
            clean_foods = ["palak", "beetroot", "moringa"] + clean_foods
        elif primary == "low_hdl":
            clean_foods = ["walnuts", "flaxseeds", "chia seeds"] + clean_foods
        elif primary == "vitamin_d_deficiency":
            clean_foods = ["milk", "mushrooms"] + clean_foods
        elif primary == "hypocalcemia":
            clean_foods = ["milk", "curd", "paneer", "ragi"] + clean_foods
        
        components = {}
        
        if meal_type in ["lunch", "dinner"]:
            # Rule: [Roti + Sabzi + Dal + Probiotic + Side] [Step 3]
            
            # A. Roti (Staple) with Diversity [Step 5]
            staple = self._select_staple_with_diversity(conditions, used_items["staples"])
            components["Roti"] = f"{staple} Roti"
            used_items["staples"].add(staple)

            # B. Sabzi (Clinical vehicle)
            veggie = self._find_best_match(clean_foods, ["sabzi", "spinach", "beetroot", "broccoli", "moringa", "bitter gourd", "bottle gourd", "cabbage", "carrot", "methi"], exclude=used_items["sabzis"])
            if veggie:
                components["Sabzi"] = generate_component_name(veggie, "Sabzi")
                used_items["sabzis"].add(veggie)
            else:
                components["Sabzi"] = "Mixed Vegetable Masala"

            # C. Dal (Protein)
            protein = self._find_best_match(clean_foods, ["dal", "lentil", "paneer", "soy", "egg", "chickpea"], exclude=used_items["dals"])
            if protein:
                components["Dal"] = generate_component_name(protein, "Dal")
                used_items["dals"].add(protein)
            else:
                components["Dal"] = self._select_best_dal(conditions)
                used_items["dals"].add(components["Dal"].lower())

            # D. Mandatory Probiotic (Curd)
            components["Probiotic"] = "Fresh Probiotic Curd"
            
            # E. Absorption Side (Step 3)
            components["Absorption"] = "Fresh Cucumber & Lemon Salad"

            # 🧠 Dynamic Title from actual ingredients
            title = generate_dish_name(
                [staple, veggie or "vegetables", protein or "dal"],
                meal_type=meal_type
            )

        elif "breakfast" in meal_type:
            # Rule: [Main + Calcium Source + Healthy Fat] [Step 3]
            main_food = self._find_best_match(clean_foods, ["poha", "upma", "chilla", "ragi", "oats", "paratha"])
            if main_food:
                # 🧠 Dynamic breakfast name from actual ingredients
                breakfast_ings = [main_food, "milk", "walnuts", "flaxseeds"]
                components["Main"] = generate_dish_name(breakfast_ings, meal_type="breakfast")
            else:
                components["Main"] = self._select_best_breakfast(conditions)
            
            components["Calcium Source"] = "High-Calcium Low-Fat Milk"
            components["Healthy Fat"] = "Walnuts & Flaxseeds"
            
            title = components["Main"]

        elif "snack" in meal_type:
            # Rule: Light Indian Snacks only [Step 3 & 8]
            snack_food = self._find_best_match(clean_foods, ["makhana", "nuts", "sprouts", "fruit", "pomegranate", "apple", "seeds", "almonds", "walnuts", "dates"])
            if snack_food:
                snack_ings = [snack_food] + [f for f in clean_foods if f != snack_food][:2]
                components["Snack"] = generate_dish_name(snack_ings, meal_type="snack")
            elif "morning" in meal_type:
                components["Snack"] = "Fresh Seasonal Fruit Bowl"
            else:
                components["Snack"] = "Roasted Masala Makhana"
            title = components["Snack"]

        else:
            # NO PLACEHOLDERS ALLOWED.
            components = {"Main": "Moong Dal Khichdi", "Side": "Fresh Curd"}
            title = "Moong Dal Khichdi with Curd"

        # Step 6: Strict Nutrient Tagging
        tags = self._get_tags_for_meal(components)

        return {
            "title": title,
            "components": components,
            "nutrient_tags": tags,
            "benefit": "Optimized for your specific laboratory profile." # Fixed by Explainer
        }

    def _select_staple_with_diversity(self, conditions: List[str], used: set) -> str:
        """Selects staple based on biochemical audit [Step 5]."""
        # Condition priority logic
        candidates = ["Bajra", "Jowar", "Ragi", "Whole Wheat"]
        
        if any(c in conditions for c in ["iron_deficiency_anemia", "hypoxia"]):
            candidates = ["Bajra", "Ragi", "Jowar", "Whole Wheat"]
        elif any(c in conditions for c in ["prediabetes", "hyperglycemia"]):
            candidates = ["Jowar", "Ragi", "Bajra", "Whole Wheat"]

        # Selection Memory [Step 5]
        for cand in candidates:
            if cand not in used:
                return cand
        return candidates[0]

    def _select_best_dal(self, conditions: List[str]) -> str:
        """Determines best protein based on clinic context."""
        if any(c in conditions for c in ["liver_stress", "kidney_strain"]):
            return "Yellow Moong Dal Tadka"
        return "Masoor Protein Curry"

    def _select_best_breakfast(self, conditions: List[str]) -> str:
        """Determines best breakfast based on clinical context."""
        if any(c in conditions for c in ["prediabetes", "hyperglycemia"]):
            return "Moong Dal Chilla"
        if any(c in conditions for c in ["iron_deficiency_anemia"]):
            return "Ragi Porridge"
        return "Vegetable Poha"

    def _get_tags_for_meal(self, components: Dict[str, str]) -> List[str]:
        """STRICT Nutrient Tagging: Only tag if source exists [Step 6]."""
        tags = []
        comp_str = " ".join(components.values()).lower()
        
        # Step 6 Evidence Table
        evidence = {
            "B12": ["milk", "curd", "paneer", "egg", "fortified"],
            "Calcium": ["milk", "curd", "paneer", "ragi", "sesame"],
            "Omega-3": ["walnut", "flax", "chia", "seeds"]
        }
        
        for tag, sources in evidence.items():
            if any(src in comp_str for src in sources):
                tags.append(tag)
        
        # General markers
        if any(k in comp_str for k in ["palak", "spinach", "beetroot", "moringa", "bajra"]):
            tags.append("Iron")
        if any(k in comp_str for k in ["oats", "dalia", "jowar", "sabzi", "millet"]):
            tags.append("Fiber")
            
        return list(set(tags))

    def _find_best_match(self, foods: List[str], keywords: List[str], exclude: Optional[set] = None) -> Optional[str]:
        """Finds matches from the USDA list and picks one dynamically using the variation engine."""
        if exclude is None: exclude = set()
        valid_matches = []
        for f in foods:
            for k in keywords:
                if k in f and f not in exclude:
                    valid_matches.append(f)
                    break # Move to next food
                    
        if not valid_matches:
            return None
            
        from backend.services.variation_engine import variation_engine
        return variation_engine.select_meal_option(valid_matches, k=3)

# Singleton
indian_meal_builder = IndianMealBuilder()
