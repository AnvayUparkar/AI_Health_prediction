
import logging
from typing import List, Dict, Any, Optional
from backend.usda_manager import usda_manager
from backend.services.dish_name_generator import generate_dish_name, generate_component_name, COOKING_STYLE
from backend.services.variation_engine import variation_engine

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

    # ===================================================================
    # DIETARY PREFERENCE FILTERING (Safety-First Architecture)
    # ===================================================================

    # Non-vegetarian items (must be filtered for veg/vegan users)
    NON_VEG_ITEMS = {
        "chicken", "fish", "egg", "eggs", "mutton", "lamb", "pork", "beef",
        "prawn", "shrimp", "crab", "lobster", "salmon", "tuna", "sardine",
        "mackerel", "turkey", "bacon", "sausage", "ham", "lean meat",
        "chicken breast", "chicken broth", "fish sauce", "egg whites",
    }

    # Dairy items (must be filtered for vegan users)
    DAIRY_ITEMS = {
        "milk", "curd", "paneer", "cheese", "cream", "butter", "ghee",
        "buttermilk", "yogurt", "greek yogurt", "whey", "casein",
    }

    # Veg protein substitutes (used when non-veg is filtered out)
    VEG_PROTEIN_SUBS = ["paneer", "soy", "sprouts", "chickpea", "rajma", "moong dal", "chana dal"]
    VEGAN_PROTEIN_SUBS = ["soy", "sprouts", "chickpea", "rajma", "moong dal", "chana dal", "tofu"]

    def _filter_by_dietary_preference(self, foods: List[str], context: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Filters food list based on dietary preferences from the patient profile.
        
        Preference values: 'veg'/'vegetarian', 'vegan', 'non_veg'/'non-vegetarian', 'both', 'balanced', 'none'
        """
        if not context:
            return foods

        pref = (context.get("diet_preference") or "balanced").lower().strip()
        allergies = [a.lower().strip() for a in (context.get("allergies") or [])]
        non_veg_prefs = [p.lower().strip() for p in (context.get("non_veg_preferences") or [])]

        filtered = []

        for food in foods:
            food_lower = food.lower().strip()

            # 1. Allergy gate (absolute safety — always applies)
            if any(allergen in food_lower for allergen in allergies):
                logger.info("DIET_FILTER | Removed '%s' — allergy match: %s", food, allergies)
                continue

            # 2. Vegetarian filter
            if pref in ("veg", "vegetarian"):
                if any(nv in food_lower for nv in self.NON_VEG_ITEMS):
                    logger.info("DIET_FILTER | Removed '%s' — non-veg (user is vegetarian)", food)
                    continue

            # 3. Vegan filter (stricter — no dairy either)
            elif pref == "vegan":
                if any(nv in food_lower for nv in self.NON_VEG_ITEMS):
                    logger.info("DIET_FILTER | Removed '%s' — non-veg (user is vegan)", food)
                    continue
                if any(d in food_lower for d in self.DAIRY_ITEMS):
                    logger.info("DIET_FILTER | Removed '%s' — dairy (user is vegan)", food)
                    continue

            # 4. Non-veg / Both — allow everything, but prefer stated preferences
            # (No filtering, but could boost preferred proteins later)

            filtered.append(food)

        return filtered

    def build_meal(self, top_foods: List[str], meal_type: str, conditions: List[str], used_items: Optional[Dict[str, set]] = None, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Builds a meal following NON-NEGOTIABLE structural templates [Step 3].
        Includes Step 4 personalization based on primary condition.
        Now respects dietary preferences from patient profile.
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

        # 🍽️ DIETARY PREFERENCE FILTER (Safety-First — runs before any meal logic)
        clean_foods = self._filter_by_dietary_preference(clean_foods, context)

        # [Step 4] Personalization - Inject Mandatory Clinical Ingredients
        # (Respect dietary preference: use veg/vegan protein subs if needed)
        pref = (context.get("diet_preference") or "balanced").lower().strip() if context else "balanced"

        if primary == "iron_deficiency_anemia":
            # Force high-iron candidates into top of search
            clean_foods = ["palak", "beetroot", "moringa"] + clean_foods
        elif primary == "low_hdl":
            clean_foods = ["walnuts", "flaxseeds", "chia seeds"] + clean_foods
        elif primary == "vitamin_d_deficiency":
            if pref not in ("vegan",):
                clean_foods = ["milk", "mushrooms"] + clean_foods
            else:
                clean_foods = ["mushrooms", "fortified cereals"] + clean_foods
        elif primary == "hypocalcemia":
            if pref in ("veg", "vegetarian", "balanced", "both", "none"):
                clean_foods = ["milk", "curd", "paneer", "ragi"] + clean_foods
            elif pref == "vegan":
                clean_foods = ["ragi", "sesame", "fortified plant milk"] + clean_foods
            else:
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
                # 🧠 Track raw ingredient for diversity
                variation_engine.track_selection(context.get("patient_id", "generic"), veggie)
            else:
                # 🧠 Dynamic fallback for Sabzi variety
                sabzi_options = ["Bottle Gourd Masala", "Ridge Gourd Sabzi", "Ivy Gourd (Kundru) Fry", "Cabbage with Peas"]
                components["Sabzi"] = variation_engine.select_meal_option(sabzi_options, k=len(sabzi_options))
                used_items["sabzis"].add(components["Sabzi"].lower())
                variation_engine.track_selection(context.get("patient_id", "generic"), components["Sabzi"])

            # C. Dal (Protein)
            protein = self._find_best_match(clean_foods, ["dal", "lentil", "paneer", "soy", "egg", "chickpea"], exclude=used_items["dals"])
            if protein:
                components["Dal"] = generate_component_name(protein, "Dal")
                used_items["dals"].add(protein)
                variation_engine.track_selection(context.get("patient_id", "generic"), protein)
            else:
                components["Dal"] = self._select_best_dal(conditions)
                used_items["dals"].add(components["Dal"].lower())
                variation_engine.track_selection(context.get("patient_id", "generic"), components["Dal"])

            # D. Mandatory Probiotic (Curd / Vegan alternative)
            if pref == "vegan":
                components["Probiotic"] = "Fermented Plant Probiotic"
            else:
                probiotic_options = ["Fresh Probiotic Curd", "Spiced Masala Buttermilk", "Mint & Cumin Raita"]
                components["Probiotic"] = variation_engine.select_meal_option(probiotic_options, k=len(probiotic_options))
            
            # E. Absorption Side (Step 3)
            side_options = ["Fresh Cucumber & Lemon Salad", "Garden Fresh Kachumber Salad", "Beetroot & Carrot Juliennes"]
            components["Absorption"] = variation_engine.select_meal_option(side_options, k=len(side_options))

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
            
            if pref == "vegan":
                components["Calcium Source"] = "Fortified Almond Milk"
            else:
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
            if pref == "vegan":
                components = {"Main": "Moong Dal Khichdi", "Side": "Fermented Plant Probiotic"}
                title = "Moong Dal Khichdi with Plant Probiotic"
            else:
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
        """Selects staple based on biochemical audit [Step 5] with per-request variation."""
        # Condition priority logic
        candidates = ["Bajra", "Jowar", "Ragi", "Whole Wheat"]
        
        if any(c in conditions for c in ["iron_deficiency_anemia", "hypoxia"]):
            candidates = ["Bajra", "Ragi", "Jowar", "Whole Wheat"]
        elif any(c in conditions for c in ["prediabetes", "hyperglycemia"]):
            candidates = ["Jowar", "Ragi", "Bajra", "Whole Wheat"]

        # 🧠 Per-request shuffle within clinical priority band
        candidates = variation_engine.shuffle_candidates(candidates)

        # Selection Memory [Step 5]
        for cand in candidates:
            if cand not in used:
                return cand
        return candidates[0]

    def _select_best_dal(self, conditions: List[str]) -> str:
        """Determines best protein based on clinic context with variation."""
        if any(c in conditions for c in ["liver_stress", "kidney_strain"]):
            options = ["Yellow Moong Dal Tadka", "Light Toor Dal", "Moong Dal Soup"]
        else:
            options = ["Masoor Dal Curry", "Yellow Moong Dal Tadka", "Chana Dal Fry", "Toor Dal Tadka"]
        return variation_engine.select_meal_option(options, k=len(options))

    def _select_best_breakfast(self, conditions: List[str]) -> str:
        """Determines best breakfast based on clinical context with variation."""
        if any(c in conditions for c in ["prediabetes", "hyperglycemia"]):
            options = ["Moong Dal Chilla", "Savory Oats Upma", "Vegetable Daliya"]
        elif any(c in conditions for c in ["iron_deficiency_anemia"]):
            options = ["Ragi Porridge", "Bajra Roti with Jaggery", "Beetroot Poha"]
        else:
            options = ["Vegetable Poha", "Oats Upma", "Moong Dal Chilla", "Ragi Porridge"]
        return variation_engine.select_meal_option(options, k=len(options))

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
