"""
Dynamic Dish Name Generator
=============================

Generates human-friendly, appetizing dish names from raw ingredient sets
using pattern matching. Replaces static DISH_MAP lookups with intelligent,
context-aware naming that mirrors natural culinary language.

Pipeline:
    Ingredient Set  →  Pattern Detection  →  Contextual Name Assembly

No LLM required — pure deterministic pattern matching.

⚠️ This module does NOT modify clinical logic, confidence, or mapper data.
   It ONLY produces display-friendly dish names from ingredient inputs.
"""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


# ===================================================================
# 1. DISH PATTERN RULES
# ===================================================================
# Each pattern defines a recognizable Indian dish archetype.
# "triggers" = ingredient keywords that, when matched, activate the pattern.
# "min_score" = minimum trigger hits needed to confirm the pattern.

DISH_PATTERNS = [
    # ---- Breakfast Patterns ----
    {
        "name": "Porridge",
        "category": "breakfast",
        "triggers": {
            "base":     ["ragi", "oats", "daliya", "dalia", "millet", "bajra"],
            "liquid":   ["milk", "water", "almond milk"],
            "toppings": ["nuts", "seeds", "fruits", "walnuts", "flaxseeds",
                         "chia seeds", "almonds", "dates", "honey", "banana"],
        },
        "min_score": 2,
    },
    {
        "name": "Upma",
        "category": "breakfast",
        "triggers": {
            "base":   ["semolina", "rava", "oats", "upma"],
            "veggies": ["vegetables", "carrot", "peas", "beans", "onion"],
            "fat":    ["ghee", "mustard seeds", "curry leaves"],
        },
        "min_score": 2,
    },
    {
        "name": "Chilla",
        "category": "breakfast",
        "triggers": {
            "base":   ["besan", "moong", "chilla", "gram flour", "lentil"],
            "stuffing": ["paneer", "vegetables", "onion", "tomato", "spinach"],
        },
        "min_score": 2,
    },
    {
        "name": "Poha",
        "category": "breakfast",
        "triggers": {
            "base":   ["poha", "flattened rice", "beaten rice"],
            "extras": ["peanuts", "vegetables", "onion", "turmeric", "curry leaves"],
        },
        "min_score": 1,
    },
    {
        "name": "Smoothie",
        "category": "breakfast",
        "triggers": {
            "base":   ["smoothie", "shake", "banana", "berries", "mango"],
            "liquid": ["milk", "yogurt", "curd", "almond milk"],
            "boost":  ["protein", "chia seeds", "flaxseeds", "spinach"],
        },
        "min_score": 2,
    },

    # ---- Main Meal Patterns ----
    {
        "name": "Khichdi",
        "category": "main",
        "triggers": {
            "grain":   ["rice", "brown rice", "millet"],
            "protein": ["lentils", "dal", "moong", "masoor"],
            "extras":  ["ghee", "spices", "turmeric", "cumin"],
        },
        "min_score": 2,
    },
    {
        "name": "Sabzi",
        "category": "main",
        "triggers": {
            "veggies": ["spinach", "palak", "beetroot", "broccoli", "moringa",
                        "bitter gourd", "karela", "bottle gourd", "lauki",
                        "cabbage", "cauliflower", "carrot", "methi", "bhindi",
                        "mushroom", "capsicum"],
            "base":   ["sabzi", "curry", "stir-fry"],
            "spices": ["cumin", "turmeric", "garlic", "ginger", "mustard seeds"],
        },
        "min_score": 1,
    },
    {
        "name": "Dal",
        "category": "main",
        "triggers": {
            "protein": ["moong dal", "masoor dal", "chana dal", "toor dal",
                        "dal", "lentil", "lentils", "urad dal"],
            "method":  ["tadka", "fry", "temper"],
            "spices":  ["turmeric", "cumin", "garlic", "asafoetida", "mustard seeds"],
        },
        "min_score": 1,
    },
    {
        "name": "Curry",
        "category": "main",
        "triggers": {
            "protein": ["paneer", "chicken", "egg", "fish", "tofu",
                        "soy", "chickpea", "rajma"],
            "gravy":   ["tomato", "onion", "cream", "coconut"],
            "spices":  ["masala", "garam masala", "chili", "coriander"],
        },
        "min_score": 2,
    },
    {
        "name": "Raita",
        "category": "side",
        "triggers": {
            "base":   ["curd", "yogurt", "dahi"],
            "veggies": ["cucumber", "onion", "boondi", "mint"],
        },
        "min_score": 2,
    },

    # ---- Snack Patterns ----
    {
        "name": "Snack Bowl",
        "category": "snack",
        "triggers": {
            "base": ["nuts", "makhana", "seeds", "almonds", "walnuts",
                     "peanuts", "pumpkin seeds", "flaxseeds", "chia seeds"],
        },
        "min_score": 1,
    },
    {
        "name": "Chaat",
        "category": "snack",
        "triggers": {
            "base":   ["sprouts", "moong", "chickpea", "chana"],
            "extras": ["onion", "tomato", "lemon", "chaat masala", "pomegranate"],
        },
        "min_score": 2,
    },
    {
        "name": "Fruit Bowl",
        "category": "snack",
        "triggers": {
            "fruits": ["pomegranate", "apple", "orange", "banana", "papaya",
                       "berries", "guava", "kiwi", "mango", "seasonal fruit"],
        },
        "min_score": 1,
    },

    # ---- Soup / Light Dinner ----
    {
        "name": "Soup",
        "category": "main",
        "triggers": {
            "method": ["soup", "broth", "clear"],
            "base":   ["tomato", "spinach", "lentil", "chicken", "mixed vegetable",
                       "moringa", "mushroom"],
        },
        "min_score": 1,
    },
]


# ===================================================================
# 2. CULINARY ADJECTIVE LIBRARY (for appetizing names)
# ===================================================================

COOKING_STYLE = {
    "spinach":      "Spiced",
    "palak":        "Spiced",
    "beetroot":     "Roasted",
    "broccoli":     "Stir-Fried",
    "moringa":      "Superfood",
    "bitter gourd":  "Masala",
    "karela":       "Masala",
    "bottle gourd":  "Light",
    "lauki":        "Light",
    "cabbage":      "Tangy",
    "carrot":       "Fresh",
    "methi":        "Aromatic",
    "mushroom":     "Sautéed",
    "capsicum":     "Charred",
    "paneer":       "Soft",
    "chicken":      "Grilled",
    "fish":         "Steamed",
    "egg":          "Spiced",
    "tofu":         "Crispy",
    "soy":          "Protein-Rich",
    "sprouts":      "Fresh",
    "oats":         "Savory",
    "ragi":         "Warm",
    "bajra":        "Hearty",
    "makhana":      "Roasted",
    "walnuts":      "Crunchy",
    "almonds":      "Toasted",
    "flaxseeds":    "Nutty",
    "chia seeds":   "Power-Packed",
    "dates":        "Natural",
    "pomegranate":  "Fresh",
    "curd":         "Probiotic",
    "buttermilk":   "Spiced",
    "milk":         "Warm",
}


# ===================================================================
# 3. CORE FUNCTIONS
# ===================================================================


def _sanitize_ingredient(raw: str) -> str:
    """
    Cleans up raw ingredient strings from mappers/pipelines.
    'whole grains: oats, dalia, brown rice' → 'oats'
    'lentils, chickpeas, and kidney beans' → 'lentils'
    'beetroot and beetroot juice' → 'beetroot'
    """
    clean = raw.strip().lower()

    # Strip everything after colon (e.g., "whole grains: oats, dalia")
    if ':' in clean:
        clean = clean.split(':')[-1].strip()

    # Take only the first item if comma-separated
    if ',' in clean:
        clean = clean.split(',')[0].strip()

    # Take only the first item if 'and'-separated
    if ' and ' in clean:
        clean = clean.split(' and ')[0].strip()

    # Remove parenthetical content
    if '(' in clean:
        clean = clean.split('(')[0].strip()

    # Cap length — names longer than 20 chars are almost never real ingredients
    if len(clean) > 20:
        # Try to find a known keyword in it
        for keyword in COOKING_STYLE:
            if keyword in clean:
                return keyword
        clean = clean[:20].rsplit(' ', 1)[0]  # Truncate at word boundary

    # Strip common mapper suffixes that don't add culinary value
    STRIP_SUFFIXES = [" leaves", " leaf", " bulb", " breast", " seeds", " powder",
                      " chunks", " pieces", " juice", " fresh", " dried", " ground"]
    for suffix in STRIP_SUFFIXES:
        if clean.endswith(suffix) and len(clean) > len(suffix) + 2:
            clean = clean[:-len(suffix)]

    return clean.strip()


def detect_dish_type(ingredients: List[str]) -> Optional[dict]:
    """
    Match an ingredient list against DISH_PATTERNS.
    Returns the best-scoring pattern dict, or None.
    """
    ingredients_lower = [_sanitize_ingredient(i) for i in ingredients]

    best_pattern = None
    best_score = 0

    for pattern in DISH_PATTERNS:
        score = 0
        for key, trigger_list in pattern["triggers"].items():
            for trigger in trigger_list:
                # Check if any ingredient contains the trigger word
                if any(trigger in ing for ing in ingredients_lower):
                    score += 1

        if score >= pattern["min_score"] and score > best_score:
            best_score = score
            best_pattern = pattern

    return best_pattern


def _pick_hero_ingredient(ingredients: List[str]) -> str:
    """
    Select the most 'appetizing' ingredient to lead the dish name.
    Prioritises vegetables/grains over generic modifiers.
    """
    HERO_PRIORITY = [
        "palak", "spinach", "beetroot", "broccoli", "moringa", "methi",
        "bitter gourd", "karela", "bottle gourd", "lauki", "cabbage",
        "mushroom", "capsicum", "carrot",
        "paneer", "chicken", "fish", "egg", "tofu", "soy",
        "ragi", "bajra", "oats", "dalia", "daliya", "poha",
        "moong dal", "masoor dal", "chana dal", "toor dal",
        "makhana", "sprouts", "pomegranate", "apple",
    ]

    ingredients_lower = [_sanitize_ingredient(i) for i in ingredients]

    for hero in HERO_PRIORITY:
        for ing in ingredients_lower:
            if hero in ing:
                return ing.title()

    # Fallback: sanitize the first ingredient
    return _sanitize_ingredient(ingredients[0]).title() if ingredients else "Mixed"


def _pick_accent_ingredients(ingredients: List[str], hero: str, max_count: int = 2) -> List[str]:
    """
    Select supporting ingredients for the dish name (the '& Walnuts' part).
    Excludes the hero ingredient and generic items.
    """
    SKIP_WORDS = {"water", "spices", "salt", "oil", "ghee", "turmeric",
                  "cumin", "masala", "garam masala", "curry leaves",
                  "mustard seeds", "asafoetida"}

    accents = []
    hero_lower = hero.lower()

    for ing in ingredients:
        ing_clean = _sanitize_ingredient(ing)
        if ing_clean == hero_lower or ing_clean in SKIP_WORDS:
            continue
        if len(ing_clean) < 3:
            continue
        accents.append(ing_clean.title())
        if len(accents) >= max_count:
            break

    return accents


def generate_dish_name(ingredients: List[str], meal_type: str = "") -> str:
    """
    Generate a dynamic, appetizing dish name from an ingredient list.

    Examples:
        ["ragi", "milk", "flaxseeds", "walnuts"]  →  "Warm Ragi Porridge with Flaxseeds & Walnuts"
        ["rice", "lentils", "ghee", "spices"]      →  "Rice Khichdi with Spices"
        ["spinach", "cumin", "garlic"]              →  "Spiced Spinach Sabzi"
        ["makhana", "almonds", "pumpkin seeds"]     →  "Roasted Makhana Snack Bowl"

    Parameters
    ----------
    ingredients : list
        Raw ingredient names (from mapper / clinical derivation).
    meal_type : str
        Optional hint: 'breakfast', 'lunch', 'dinner', 'snack'.

    Returns
    -------
    str
        A human-friendly dish name.
    """
    if not ingredients:
        return "Healthy Balanced Meal"

    pattern = detect_dish_type(ingredients)
    hero = _pick_hero_ingredient(ingredients)
    accents = _pick_accent_ingredients(ingredients, hero)
    adjective = COOKING_STYLE.get(hero.lower(), "")

    # Build the name based on the detected pattern
    if pattern:
        dish_type = pattern["name"]

        if dish_type == "Porridge":
            base = f"{adjective} {hero}" if adjective else hero
            if accents:
                return f"{base} Porridge with {' & '.join(accents)}"
            return f"{base} Porridge"

        elif dish_type == "Upma":
            base = f"{adjective} {hero}" if adjective else hero
            if accents:
                return f"{base} Upma with {' & '.join(accents)}"
            return f"{base} Upma"

        elif dish_type == "Chilla":
            if accents:
                return f"{hero} Chilla with {' & '.join(accents)}"
            return f"{hero} Chilla"

        elif dish_type == "Poha":
            if accents:
                return f"Vegetable Poha with {' & '.join(accents)}"
            return "Vegetable Poha with Peanuts"

        elif dish_type == "Smoothie":
            if accents:
                return f"{hero} Smoothie with {' & '.join(accents)}"
            return f"{hero} Power Smoothie"

        elif dish_type == "Khichdi":
            if accents:
                return f"{hero} Khichdi with {' & '.join(accents)}"
            return f"{hero} Khichdi with Spices"

        elif dish_type == "Sabzi":
            base = f"{adjective} {hero}" if adjective else hero
            if accents:
                return f"{base} Sabzi with {' & '.join(accents)}"
            return f"{base} Sabzi"

        elif dish_type == "Dal":
            base = hero
            if "dal" not in base.lower():
                base = f"{hero} Dal"
            if adjective:
                base = f"{adjective} {base}"
            if accents:
                return f"{base} Tadka with {' & '.join(accents)}"
            return f"{base} Tadka"

        elif dish_type == "Curry":
            base = f"{adjective} {hero}" if adjective else hero
            if accents:
                return f"{base} Curry with {' & '.join(accents)}"
            return f"{base} Curry"

        elif dish_type == "Raita":
            if accents:
                return f"{hero} Raita with {' & '.join(accents)}"
            return f"Fresh {hero} Raita"

        elif dish_type == "Snack Bowl":
            base = f"{adjective} {hero}" if adjective else hero
            if accents:
                return f"{base} Mix with {' & '.join(accents)}"
            return f"{base} Mix"

        elif dish_type == "Chaat":
            if accents:
                return f"{hero} Chaat with {' & '.join(accents)}"
            return f"Fresh {hero} Chaat"

        elif dish_type == "Fruit Bowl":
            if accents:
                return f"Fresh {hero} Bowl with {' & '.join(accents)}"
            return f"Fresh {hero} Bowl"

        elif dish_type == "Soup":
            base = f"{adjective} {hero}" if adjective else hero
            return f"{base} Soup"

    # ---- Fallback: No pattern matched ----
    # Use meal_type hint for contextual naming
    meal_lower = meal_type.lower() if meal_type else ""

    if "breakfast" in meal_lower:
        base = f"{adjective} {hero}" if adjective else hero
        if accents:
            return f"{base} Breakfast Bowl with {' & '.join(accents)}"
        return f"{base} Breakfast Bowl"

    if "snack" in meal_lower:
        base = f"{adjective} {hero}" if adjective else hero
        return f"{base} Snack"

    # Generic fallback
    base = f"{adjective} {hero}" if adjective else hero
    if accents:
        return f"{base} Healthy Meal with {' & '.join(accents)}"
    return f"{base} Healthy Meal"


def generate_component_name(ingredient: str, slot: str = "") -> str:
    """
    Generate a name for a single meal component (used by IndianMealBuilder).

    Parameters
    ----------
    ingredient : str
        Single ingredient or food name.
    slot : str
        Meal slot context: 'Roti', 'Sabzi', 'Dal', etc.

    Returns
    -------
    str
        A contextual display name.
    """
    ing_clean = _sanitize_ingredient(ingredient)
    adjective = COOKING_STYLE.get(ing_clean, "")

    slot_lower = slot.lower()

    if "sabzi" in slot_lower or "vegetable" in slot_lower:
        base = f"{adjective} {ing_clean.title()}" if adjective else ing_clean.title()
        if "sabzi" in base.lower():
            return base
        return f"{base} Sabzi"

    if "dal" in slot_lower or "protein" in slot_lower:
        base = f"{adjective} {ing_clean.title()}" if adjective else ing_clean.title()
        if "dal" not in base.lower() and "curry" not in base.lower():
            return f"{base} Curry"
        return f"{base} Tadka"

    if "roti" in slot_lower or "staple" in slot_lower:
        return f"{ing_clean.title()} Roti"

    # Default
    base = f"{adjective} {ing_clean.title()}" if adjective else ing_clean.title()
    return base
