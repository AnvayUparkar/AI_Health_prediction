"""
Report-Based Diet Recommendation Engine
=========================================

Generates personalised diet recommendations based on *structured medical
parameters* extracted from a blood test / medical report.

This engine is separate from the existing ``diet.py`` and ``diet_plan.py``
modules because it operates on parsed lab parameters (Hemoglobin, Vitamin D,
Cholesterol, etc.) rather than user-provided form data or keywords.

    from backend.report_diet_engine import generate_report_diet

Input:  dict of important parameters (from ``report_parser.detect_important_parameters``)
Output: structured diet recommendation dict
"""

import logging
import random
from typing import Dict, List

logger = logging.getLogger(__name__)

# ===================================================================
# CONDITION → DIET RULE MAPPING
# ===================================================================

# Each rule maps a (parameter_name, status) pair to dietary advice.
# The engine accumulates advice from all matching rules, deduplicates, and
# produces a unified recommendation.

DIET_RULES: Dict[str, Dict[str, dict]] = {
    # ------------------------------------------------------------------
    # BLOOD / ANEMIA
    # ------------------------------------------------------------------
    "Hemoglobin": {
        "Low": {
            "issue": "Low Hemoglobin (possible anemia)",
            "foods": [
                "Spinach, kale, and dark leafy greens",
                "Red meat (lean cuts) or liver",
                "Lentils, chickpeas, and kidney beans",
                "Beetroot and beetroot juice",
                "Dates and dried figs",
                "Pomegranate seeds and juice",
                "Fortified cereals and whole grains",
            ],
            "avoid": [
                "Coffee/tea immediately after meals (blocks iron absorption)",
                "Excessive calcium supplements with meals",
            ],
            "tips": [
                "Pair iron-rich foods with Vitamin C (lemon, oranges) to boost absorption",
                "Cook in cast-iron cookware to increase dietary iron",
                "Soak and sprout legumes to reduce phytates that block iron",
            ],
        },
        "High": {
            "issue": "High Hemoglobin (polycythemia risk)",
            "foods": [
                "Hydrating foods — watermelon, cucumbers, celery",
                "Whole grains and fiber-rich foods",
                "Green tea (reduces iron absorption mildly)",
            ],
            "avoid": [
                "Iron-fortified cereals and supplements",
                "Excessive red meat",
                "Alcohol",
            ],
            "tips": [
                "Stay well hydrated — drink at least 8-10 glasses of water daily",
                "Consult a doctor if hemoglobin is persistently elevated",
            ],
        },
    },

    # ------------------------------------------------------------------
    # BLOOD SUGAR / DIABETES
    # ------------------------------------------------------------------
    "Glucose": {
        "High": {
            "issue": "High Blood Glucose (hyperglycemia / diabetes risk)",
            "foods": [
                "Non-starchy vegetables (broccoli, cauliflower, zucchini)",
                "Whole grains: oats, quinoa, brown rice (in moderation)",
                "Lean protein — chicken breast, fish, tofu, eggs",
                "Nuts and seeds (almonds, walnuts, flaxseeds)",
                "Legumes (lentils, black beans) for slow-release carbs",
                "Bitter gourd (karela) and fenugreek seeds",
                "Cinnamon (can help improve insulin sensitivity)",
            ],
            "avoid": [
                "Sugary drinks, sodas, and fruit juices",
                "White bread, white rice, refined flour (maida)",
                "Sweets, pastries, and desserts",
                "High-GI fruits in excess (mango, grapes, banana)",
                "Processed and packaged snacks",
            ],
            "tips": [
                "Eat smaller, more frequent meals throughout the day",
                "Always combine carbs with protein or healthy fat",
                "Walk for 15 minutes after each meal to help lower blood sugar",
                "Monitor portion sizes carefully",
            ],
        },
    },
    "Fasting Blood Sugar": {
        "High": {
            "issue": "Elevated Fasting Blood Sugar",
            "foods": [
                "High-fiber breakfast: oats, chia seeds, flaxseed",
                "Eggs and lean protein for breakfast",
                "Apple cider vinegar (1 tbsp diluted before meals)",
            ],
            "avoid": [
                "Sugary breakfast cereals and pastries",
                "Fruit juice on empty stomach",
            ],
            "tips": [
                "Have dinner at least 3 hours before bedtime",
                "Prioritise protein and fat at dinner to stabilise overnight glucose",
            ],
        },
    },
    "HbA1c": {
        "High": {
            "issue": "Elevated HbA1c (long-term blood sugar control issue)",
            "foods": [
                "Low-glycemic foods: legumes, non-starchy vegetables, berries",
                "Omega-3 rich fish (salmon, sardines, mackerel)",
                "Greek yogurt (unsweetened)",
            ],
            "avoid": [
                "All forms of added sugar",
                "Refined carbohydrates",
                "Processed meats",
            ],
            "tips": [
                "Focus on a Mediterranean-style diet pattern",
                "Regular physical activity is crucial for HbA1c control",
                "Consult an endocrinologist for comprehensive management",
            ],
        },
    },

    # ------------------------------------------------------------------
    # CHOLESTEROL / LIPIDS
    # ------------------------------------------------------------------
    "Total Cholesterol": {
        "High": {
            "issue": "High Cholesterol",
            "foods": [
                "Oats and barley (beta-glucan fiber)",
                "Fatty fish — salmon, mackerel, sardines (omega-3)",
                "Nuts — almonds, walnuts (in moderation)",
                "Olive oil and avocados (monounsaturated fats)",
                "Flaxseeds, chia seeds",
                "Beans, lentils, and chickpeas",
                "Soy products (tofu, edamame)",
            ],
            "avoid": [
                "Fried foods and trans fats",
                "Full-fat dairy (butter, cheese, cream)",
                "Processed meats (sausages, bacon, salami)",
                "Coconut oil and palm oil in large amounts",
                "Baked goods with hydrogenated oils",
            ],
            "tips": [
                "Aim for at least 25-30g of dietary fiber daily",
                "Replace saturated fats with unsaturated fats",
                "Regular aerobic exercise helps raise HDL and lower LDL",
            ],
        },
    },
    "LDL Cholesterol": {
        "High": {
            "issue": "High LDL (bad cholesterol)",
            "foods": [
                "Soluble fiber: oats, beans, barley, apples, citrus fruits",
                "Plant sterols and stanols (fortified foods)",
                "Fatty fish twice a week",
            ],
            "avoid": [
                "Saturated fat (red meat, full-fat dairy)",
                "Trans fats (partially hydrogenated oils)",
            ],
            "tips": [
                "LDL is the primary target for cardiovascular risk reduction",
                "Even small dietary changes can reduce LDL by 10-15%",
            ],
        },
    },
    "HDL Cholesterol": {
        "Low": {
            "issue": "Low HDL (good cholesterol too low)",
            "foods": [
                "Olive oil and avocados",
                "Fatty fish (salmon, tuna)",
                "Nuts (especially almonds and walnuts)",
                "Purple and red foods (grapes, berries, red cabbage)",
            ],
            "avoid": [
                "Trans fats (they lower HDL)",
                "Excessive refined carbs and sugar",
            ],
            "tips": [
                "Regular exercise is the most effective way to raise HDL",
                "Moderate alcohol consumption may raise HDL (consult doctor first)",
                "Quit smoking if applicable — smoking lowers HDL significantly",
            ],
        },
    },
    "Triglycerides": {
        "High": {
            "issue": "High Triglycerides",
            "foods": [
                "Omega-3 rich fish (salmon, sardines, mackerel)",
                "Walnuts and flaxseeds",
                "High-fiber vegetables and whole grains",
                "Legumes (lentils, chickpeas)",
            ],
            "avoid": [
                "Sugar-sweetened beverages and fruit juices",
                "Refined carbohydrates and white bread",
                "Alcohol (significant contributor to high TG)",
                "Processed and packaged snacks",
                "Excessive fruit (especially tropical fruits)",
            ],
            "tips": [
                "Reducing sugar intake is the single most effective step",
                "Replace refined carbs with whole grains",
                "Weight loss of even 5-10% can significantly lower triglyceride levels",
            ],
        },
    },

    # ------------------------------------------------------------------
    # VITAMINS AND MINERALS
    # ------------------------------------------------------------------
    "Vitamin D": {
        "Low": {
            "issue": "Low Vitamin D (deficiency)",
            "foods": [
                "Fortified milk and plant-based milks",
                "Fatty fish (salmon, tuna, sardines)",
                "Egg yolks",
                "Fortified cereals and orange juice",
                "Mushrooms (especially sun-dried or UV-exposed)",
                "Cod liver oil",
            ],
            "avoid": [],
            "tips": [
                "Get 15-20 minutes of direct sunlight daily (morning sun is best)",
                "Vitamin D supplements (D3) may be needed — consult your doctor",
                "Vitamin D is fat-soluble — take with a meal containing fat",
                "Consider supplementation especially during winter months",
            ],
        },
    },
    "Vitamin B12": {
        "Low": {
            "issue": "Low Vitamin B12 (deficiency)",
            "foods": [
                "Eggs and dairy products (milk, yogurt, cheese)",
                "Fish (salmon, tuna, sardines)",
                "Lean meat and poultry",
                "Fortified cereals and nutritional yeast",
                "Fortified plant-based milks (for vegetarians/vegans)",
            ],
            "avoid": [],
            "tips": [
                "Vegetarians and vegans are at higher risk — consider B12 supplements",
                "B12 absorption decreases with age — sublingual supplements may help",
                "Have B12 levels rechecked after 3 months of dietary changes",
            ],
        },
    },
    "Iron": {
        "Low": {
            "issue": "Low Iron (iron deficiency)",
            "foods": [
                "Red meat, liver, and organ meats",
                "Spinach, kale, Swiss chard",
                "Lentils, chickpeas, and soybeans",
                "Pumpkin seeds and sesame seeds",
                "Dark chocolate (70%+ cocoa)",
                "Fortified cereals",
            ],
            "avoid": [
                "Tea and coffee with meals (tannins block iron absorption)",
                "Calcium-rich foods at the same time as iron-rich foods",
            ],
            "tips": [
                "Combine iron-rich foods with vitamin C sources (bell peppers, citrus)",
                "Heme iron (from meat) is better absorbed than non-heme (plant) iron",
            ],
        },
    },
    "Calcium": {
        "Low": {
            "issue": "Low Calcium",
            "foods": [
                "Dairy products (milk, yogurt, cheese, paneer)",
                "Fortified plant milks (almond, soy, oat milk)",
                "Dark leafy greens (kale, bok choy, broccoli)",
                "Tofu (calcium-set)",
                "Sardines and canned salmon (with bones)",
                "Sesame seeds and tahini",
                "Ragi (finger millet)",
            ],
            "avoid": [
                "Excessive caffeine (increases calcium excretion)",
                "Very high sodium diets (sodium increases calcium loss)",
                "Excessive oxalate-rich foods (spinach) if sole calcium source",
            ],
            "tips": [
                "Spread calcium intake throughout the day for better absorption",
                "Ensure adequate Vitamin D for calcium absorption",
                "Aim for 1000-1200 mg calcium daily",
            ],
        },
    },

    # ------------------------------------------------------------------
    # KIDNEY MARKERS
    # ------------------------------------------------------------------
    "Creatinine": {
        "High": {
            "issue": "Elevated Creatinine (kidney stress)",
            "foods": [
                "Low-protein foods: fruits, vegetables, grains",
                "Cauliflower, cabbage, red bell peppers",
                "Garlic and onions (kidney-protective)",
                "Blueberries and cranberries",
                "Egg whites (high-quality protein, low creatinine)",
            ],
            "avoid": [
                "Excessive red meat and high-protein diets",
                "Processed foods high in sodium and potassium",
                "Creatine supplements",
                "NSAIDs (consult doctor)",
            ],
            "tips": [
                "Stay well hydrated — adequate water intake helps kidneys",
                "Limit protein to 0.8g/kg body weight unless advised otherwise",
                "Consult a nephrologist if creatinine is persistently elevated",
            ],
        },
    },
    "Uric Acid": {
        "High": {
            "issue": "High Uric Acid (gout / hyperuricemia risk)",
            "foods": [
                "Cherries and cherry juice (reduces uric acid)",
                "Low-fat dairy products",
                "Whole grains and complex carbs",
                "Vegetables (most are safe, even moderate-purine ones)",
                "Vitamin C rich foods (citrus, strawberries)",
            ],
            "avoid": [
                "Organ meats (liver, kidney, brain)",
                "Red meat in excess",
                "Shellfish (shrimp, lobster, mussels)",
                "Beer and spirits (alcohol increases uric acid)",
                "High-fructose corn syrup and sugary drinks",
                "Anchovies, sardines, herring",
            ],
            "tips": [
                "Drink at least 10-12 glasses of water daily",
                "Limit alcohol — especially beer",
                "Maintain healthy body weight (obesity increases uric acid)",
            ],
        },
    },

    # ------------------------------------------------------------------
    # LIVER MARKERS
    # ------------------------------------------------------------------
    "SGPT": {
        "High": {
            "issue": "Elevated SGPT/ALT (liver stress)",
            "foods": [
                "Green leafy vegetables and cruciferous veggies",
                "Garlic and turmeric (liver-protective)",
                "Green tea (in moderation)",
                "Berries (antioxidant-rich)",
                "Whole grains and lean protein",
                "Beetroot and carrot juice",
            ],
            "avoid": [
                "Alcohol (primary liver toxin)",
                "Fried and heavily processed foods",
                "Excessive sugar and refined carbs",
                "Acetaminophen/paracetamol overuse (consult doctor)",
            ],
            "tips": [
                "Avoid alcohol completely if liver enzymes are elevated",
                "Maintain a healthy weight — fatty liver is reversible",
                "Get retested after 4-6 weeks of dietary changes",
            ],
        },
    },
    "SGOT": {
        "High": {
            "issue": "Elevated SGOT/AST (liver/muscle stress)",
            "foods": [
                "Same liver-friendly foods as for SGPT",
                "Artichokes and dandelion greens",
                "Coffee (moderate consumption may be protective)",
            ],
            "avoid": [
                "Alcohol",
                "Trans fats and processed foods",
                "Excessive OTC medications",
            ],
            "tips": [
                "SGOT can also be elevated from intense exercise — context matters",
                "If both SGOT and SGPT are high, liver evaluation is important",
            ],
        },
    },

    # ------------------------------------------------------------------
    # THYROID
    # ------------------------------------------------------------------
    "TSH": {
        "High": {
            "issue": "High TSH (possible hypothyroidism)",
            "foods": [
                "Iodine-rich foods: seaweed, iodized salt, dairy",
                "Selenium-rich foods: Brazil nuts, fish, eggs",
                "Zinc-rich foods: pumpkin seeds, lentils, chickpeas",
                "Coconut oil (supports thyroid function)",
            ],
            "avoid": [
                "Raw cruciferous vegetables in excess (goitrogens)",
                "Soy products in large amounts",
                "Highly processed foods",
                "Gluten (if Hashimoto's thyroiditis is suspected)",
            ],
            "tips": [
                "Take thyroid medication on an empty stomach if prescribed",
                "Wait 30-60 minutes after thyroid medication before eating",
                "Cooking cruciferous vegetables reduces goitrogenic activity",
            ],
        },
        "Low": {
            "issue": "Low TSH (possible hyperthyroidism)",
            "foods": [
                "Cruciferous vegetables (broccoli, cauliflower, kale) — may help slow thyroid",
                "Calcium-rich foods (dairy, fortified beverages)",
                "Vitamin D foods (important for bone health with hyperthyroidism)",
                "Berries and antioxidant-rich foods",
            ],
            "avoid": [
                "Excessive iodine (seaweed, iodized salt in large amounts)",
                "Caffeine (can worsen anxiety and heart rate symptoms)",
                "Processed and sugary foods",
            ],
            "tips": [
                "Consult an endocrinologist for proper diagnosis and management",
                "Monitor bone density — hyperthyroidism can affect bones",
            ],
        },
    },

    # ------------------------------------------------------------------
    # ELECTROLYTES
    # ------------------------------------------------------------------
    "Potassium": {
        "Low": {
            "issue": "Low Potassium (hypokalemia)",
            "foods": [
                "Bananas, oranges, and avocados",
                "Sweet potatoes and white potatoes (with skin)",
                "Spinach and Swiss chard",
                "Coconut water",
                "Beans and lentils",
            ],
            "avoid": [],
            "tips": ["Potassium supplements should only be taken under medical supervision"],
        },
        "High": {
            "issue": "High Potassium (hyperkalemia)",
            "foods": [
                "Low-potassium fruits: apples, berries, grapes",
                "Low-potassium vegetables: cabbage, green beans, lettuce",
                "White rice and pasta",
            ],
            "avoid": [
                "Bananas, oranges, tomatoes, potatoes",
                "Salt substitutes containing potassium chloride",
                "Coconut water",
            ],
            "tips": [
                "Leach potassium from vegetables by soaking in water before cooking",
                "Avoid potassium supplements and consult your doctor",
            ],
        },
    },
    "Sodium": {
        "High": {
            "issue": "High Sodium",
            "foods": [
                "Fresh fruits and vegetables",
                "Unsalted nuts and seeds",
                "Herbs and spices for flavoring (instead of salt)",
            ],
            "avoid": [
                "Processed and packaged foods",
                "Pickles, soy sauce, and condiments",
                "Canned soups and frozen meals",
                "Fast food and restaurant meals",
            ],
            "tips": [
                "Aim for less than 2300 mg sodium per day",
                "Read nutrition labels carefully",
                "Cook at home to control sodium intake",
            ],
        },
    },
}


# ===================================================================
# INGREDIENT-FIRST LAYER (Senior Architect Implementation)
# ===================================================================

def derive_base_ingredients(important_parameters: Dict[str, dict], health_data: dict = None) -> List[str]:
    """
    Derive essential biochemical building blocks based on lab abnormalities.
    """
    ingredients = []
    
    # Blood Sugar / Metabolic
    glucose = important_parameters.get("Glucose") or important_parameters.get("Fasting Blood Sugar") or important_parameters.get("HbA1c")
    if glucose and glucose.get("status") == "High":
        ingredients += ["oats", "lentils", "leafy vegetables", "bitter gourd", "cinnamon", "fenugreek"]
        
    # Anemia / Blood
    hb = important_parameters.get("Hemoglobin") or important_parameters.get("Iron")
    if hb and hb.get("status") == "Low":
        ingredients += ["spinach", "beetroot", "pomegranate", "dates", "lean meat", "lentils"]
        
    # Kidney Stress
    creatinine = important_parameters.get("Creatinine")
    if creatinine and creatinine.get("status") == "High":
        ingredients += ["cauliflower", "cabbage", "blueberries", "egg whites", "garlic"]

    # Cholesterol
    chol = important_parameters.get("Total Cholesterol") or important_parameters.get("LDL Cholesterol")
    if chol and chol.get("status") == "High":
        ingredients += ["oats", "fatty fish", "almonds", "walnuts", "flaxseeds", "garlic"]

    # Activity Level Context
    activity = (health_data or {}).get("activityLevel", "moderate").lower()
    if "low" in activity:
        ingredients += ["high fiber foods", "light proteins", "cucumber", "lemon"]
    elif "high" in activity:
        ingredients += ["quinoa", "sweet potato", "banana", "eggs", "chicken"]
        
    # 🏥 BMI Context (Metabolic Load)
    weight = float((health_data or {}).get("weight") or 0)
    height = float((health_data or {}).get("height") or 0)
    if weight > 0 and height > 0:
        h_m = height / 100
        bmi = weight / (h_m * h_m)
        if bmi >= 25:
            ingredients += ["oats", "leafy vegetables", "bitter gourd", "green tea"]
        elif bmi < 18.5:
            ingredients += ["walnuts", "avocado", "paneer", "whole milk"]

    return list(set(ingredients))

def expand_ingredients_with_mapper(base_ingredients: List[str]) -> List[str]:
    """
    Use the clinical dish_mapper to decompose base needs into constituent ingredients.
    """
    from backend.services.dish_mapper import get_ingredients as mapper_get
    expanded = []
    
    for item in base_ingredients:
        result = mapper_get(item)
        # Handle MapperResult (dict-like)
        ing_list = result.get("ingredients", [item])
        expanded.extend(ing_list)
        
    return list(set(expanded))

# ===================================================================
# MAIN DIET GENERATION
# ===================================================================

def generate_report_diet(important_parameters: Dict[str, dict], health_data: dict = None) -> dict:
    """
    Generate a personalised diet plan based on abnormal medical parameters.

    Parameters
    ----------
    important_parameters : dict
        Dict of important/abnormal parameters from
        :func:`report_parser.detect_important_parameters`. Each entry has
        ``value``, ``unit``, ``status``, ``is_important``.

    Returns
    -------
    dict
        Structured diet recommendation::

            {
                "issues_detected": ["Low Hemoglobin", ...],
                "recommended_foods": ["Spinach", ...],
                "foods_to_avoid": ["Fried foods", ...],
                "diet_tips": ["Pair iron foods with vitamin C", ...],
                "meal_suggestions": {
                    "breakfast": [...],
                    "lunch": [...],
                    "dinner": [...],
                    "snacks": [...]
                },
                "hydration_notes": "...",
                "disclaimer": "..."
            }
    """
    # Initialize variation seed for non-deterministic meal shuffling
    from backend.services.variation_engine import variation_engine
    variation_engine.set_daily_seed("report_engine")

    issues: List[str] = []
    foods: List[str] = []
    avoid: List[str] = []
    tips: List[str] = []

    for param_name, param_info in important_parameters.items():
        status = param_info.get("status", "Normal")

        if status == "Normal":
            continue

        # Look up diet rules
        param_rules = DIET_RULES.get(param_name, {})
        status_rule = param_rules.get(status)

        if status_rule:
            issues.append(status_rule["issue"])
            foods.extend(status_rule.get("foods", []))
            avoid.extend(status_rule.get("avoid", []))
            tips.extend(status_rule.get("tips", []))
        else:
            # Generic fallback
            issues.append(f"{status} {param_name}")
            tips.append(
                f"Consult a healthcare provider about your {status.lower()} "
                f"{param_name} level ({param_info.get('value', '?')} {param_info.get('unit', '')})"
            )

    # 🏥 NEW: Physical Attribute Analysis (Senior Architect Enhancement)
    if health_data:
        weight = float(health_data.get("weight") or 0)
        height = float(health_data.get("height") or 0)
        age = int(health_data.get("age") or 0)
        
        if weight > 0 and height > 0:
            # BMI Calculation (h in cm -> m)
            h_m = height / 100
            bmi = weight / (h_m * h_m)
            
            if bmi < 18.5:
                issues.append("Underweight (Low BMI)")
                tips.append("Focus on nutrient-dense, calorie-rich foods to reach a healthy weight.")
                foods.extend(["Peanut butter", "Avocados", "Full-fat dairy", "Nuts", "Seeds"])
            elif 25 <= bmi < 30:
                issues.append("Overweight (Elevated BMI)")
                tips.append("Adopt a slight calorie deficit and focus on high-fiber, filling foods.")
                avoid.extend(["Refined sugars", "Sugary drinks", "Deep-fried foods"])
            elif bmi >= 30:
                issues.append("Obesity (High BMI)")
                tips.append("Clinical weight management recommended. Focus on low-glycemic index foods.")
                avoid.extend(["Processed meats", "White bread", "Sweetened beverages", "Trans fats"])

        if age >= 65:
            issues.append("Senior Nutritional Requirements")
            tips.append("Prioritize protein and Vitamin B12 for muscle and nerve health.")
            foods.extend(["Eggs", "Soft-cooked vegetables", "Fortified cereals"])
        elif age <= 12 and age > 0:
            issues.append("Child Growth Support")
            tips.append("Ensure adequate calcium and healthy fats for developmental growth.")

    # Deduplicate while preserving order
    issues = _deduplicate(issues)
    foods = _deduplicate(foods)
    avoid = _deduplicate(avoid)
    tips = _deduplicate(tips)

    # 🧠 NEW INGREDIENT-FIRST FLOW
    base_ingredients = derive_base_ingredients(important_parameters, health_data)
    expanded_ingredients = expand_ingredients_with_mapper(base_ingredients)

    # 🍽️ Dietary Preferences — drive food filtering
    diet_pref = "balanced"
    non_veg_prefs = []
    allergies = []
    if health_data:
        diet_pref = health_data.get("dietaryPreference", health_data.get("diet_preference", "balanced"))
        non_veg_prefs = health_data.get("nonVegPreferences", health_data.get("non_veg_preferences", []))
        allergies = health_data.get("allergies", [])

    # Generate legacy meal suggestions (backward compatibility)
    meal_suggestions = _generate_meals(
        foods, 
        avoid, 
        expanded_ingredients, 
        diet_preference=diet_pref, 
        allergies=allergies
    )

    # 🧠 NEW: Generate structured meal_plan using IndianMealBuilder + Dynamic Names
    from backend.indian_meal_builder import indian_meal_builder
    from backend.report_parser import detect_high_level_conditions
    from backend.services.variation_engine import variation_engine

    # 🎲 Per-request seed — ensures different output on every upload
    variation_engine.set_request_seed()

    conditions = detect_high_level_conditions(important_parameters)
    all_food_inputs = variation_engine.shuffle_candidates(list(set(foods + expanded_ingredients)))

    structured_meal_plan = {}
    used_items = {"staples": set(), "dals": set(), "sabzis": set()}
    
    build_context = {
        "conditions": conditions,
        "primary_condition": conditions[0] if conditions else "general_wellness",
        "diet_preference": diet_pref,
        "non_veg_preferences": non_veg_prefs,
        "allergies": allergies
    }

    for slot in ["breakfast", "mid_morning", "lunch", "evening_snack", "dinner"]:
        composed = indian_meal_builder.build_meal(
            all_food_inputs,
            slot,
            conditions=conditions,
            used_items=used_items,
            context=build_context,
        )
        structured_meal_plan[slot] = composed

    # Hydration notes
    hydration = _generate_hydration_notes(important_parameters)

    result = {
        "issues_detected": issues,
        "recommended_foods": foods,
        "foods_to_avoid": avoid,
        "diet_tips": tips,
        "meal_suggestions": meal_suggestions,   # Legacy flat lists
        "meal_plan": structured_meal_plan,       # Structured daily plan with dynamic names
        "hydration_notes": hydration,
        "disclaimer": (
            "This is an AI-generated diet suggestion based on lab report analysis. "
            "It is NOT a substitute for professional medical advice. "
            "Please consult a qualified dietitian or doctor before making "
            "significant dietary changes."
        ),
    }

    if not issues:
        result["issues_detected"] = ["All detected parameters appear normal"]
        result["diet_tips"] = [
            "Maintain a balanced diet rich in fruits, vegetables, and whole grains",
            "Stay hydrated — aim for 8-10 glasses of water daily",
            "Include lean protein with every meal",
            "Exercise regularly — at least 150 minutes of moderate activity per week",
        ]

    return result


def format_diet_plan_text(diet_result: dict) -> str:
    """
    Format the diet recommendation dict into a clean, human-readable string.

    Parameters
    ----------
    diet_result : dict
        Output of :func:`generate_report_diet`.

    Returns
    -------
    str
        Formatted text.
    """
    lines = []
    lines.append("=" * 60)
    lines.append("🍽️  PERSONALIZED DIET RECOMMENDATION")
    lines.append("=" * 60)
    lines.append("")

    # Issues
    issues = diet_result.get("issues_detected", [])
    if issues:
        lines.append("⚠️  ISSUES DETECTED:")
        for issue in issues:
            lines.append(f"  • {issue}")
        lines.append("")

    # Recommended foods
    foods = diet_result.get("recommended_foods", [])
    if foods:
        lines.append("✅ RECOMMENDED FOODS:")
        for food in foods:
            lines.append(f"  • {food}")
        lines.append("")

    # Foods to avoid
    avoid = diet_result.get("foods_to_avoid", [])
    if avoid:
        lines.append("❌ FOODS TO AVOID:")
        for item in avoid:
            lines.append(f"  • {item}")
        lines.append("")

    # Diet tips
    tips = diet_result.get("diet_tips", [])
    if tips:
        lines.append("💡 DIET TIPS:")
        for tip in tips:
            lines.append(f"  • {tip}")
        lines.append("")

    # Meal suggestions
    meals = diet_result.get("meal_suggestions", {})
    if meals:
        lines.append("🥗 SUGGESTED MEALS:")
        for meal_type in ["breakfast", "lunch", "dinner", "snacks"]:
            items = meals.get(meal_type, [])
            if items:
                lines.append(f"  {meal_type.title()}:")
                for item in items:
                    lines.append(f"    • {item}")
        lines.append("")

    # Hydration
    hydration = diet_result.get("hydration_notes", "")
    if hydration:
        lines.append(f"💧 HYDRATION: {hydration}")
        lines.append("")

    # Disclaimer
    lines.append(f"⚕️  {diet_result.get('disclaimer', '')}")
    lines.append("=" * 60)

    return "\n".join(lines)


# ===================================================================
# HELPERS
# ===================================================================

def _deduplicate(items: List[str]) -> List[str]:
    """Deduplicate a list while preserving insertion order."""
    seen = set()
    result = []
    for item in items:
        key = item.lower().strip()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _generate_meals(
    recommended_foods: List[str],
    foods_to_avoid: List[str],
    expanded_ingredients: List[str] = None,
    diet_preference: str = "balanced",
    allergies: List[str] = None
) -> dict:
    """
    Generate simple meal suggestions based on recommended and avoided foods.
    """
    # Default balanced meals
    breakfast = [
        "Oatmeal with mixed berries, flaxseeds, and honey",
        "Whole grain toast with eggs and avocado",
        "Green smoothie (spinach, banana, almond milk, chia seeds)",
    ]
    lunch = [
        "Grilled chicken/fish or paneer with quinoa and steamed vegetables",
        "Lentil soup (dal) with brown rice and a side salad",
        "Mixed vegetable stir-fry with tofu and whole wheat roti",
    ]
    dinner = [
        "Baked salmon/fish or grilled paneer with roasted vegetables",
        "Vegetable khichdi with cucumber raita",
        "Chicken/vegetable soup with multigrain bread",
    ]
    snacks = [
        "A handful of almonds and walnuts",
        "Fresh fruit (apple, orange, or berries)",
        "Carrot and cucumber sticks with hummus",
        "Greek yogurt with a drizzle of honey",
    ]

    # Safety-First Architecture: Define restricted items for filtering
    NON_VEG_ITEMS = {
        "chicken", "fish", "egg", "eggs", "mutton", "lamb", "pork", "beef",
        "prawn", "shrimp", "crab", "lobster", "salmon", "tuna", "sardine",
        "mackerel", "turkey", "bacon", "sausage", "ham", "lean meat",
        "chicken breast", "chicken broth", "fish sauce", "egg whites",
    }
    DAIRY_ITEMS = {
        "milk", "curd", "paneer", "cheese", "cream", "butter", "ghee",
        "buttermilk", "yogurt", "greek yogurt", "whey", "casein", "raita",
    }

    def is_safe(meal_text: str) -> bool:
        meal_lower = meal_text.lower()
        
        # 1. Allergy gate
        if allergies:
            for allergen in allergies:
                if allergen.lower() in meal_lower:
                    return False
        
        # 2. Vegetarian gate
        if diet_preference in ("veg", "vegetarian"):
            if any(nv in meal_lower for nv in NON_VEG_ITEMS):
                return False
                
        # 3. Vegan gate
        elif diet_preference == "vegan":
            if any(nv in meal_lower for nv in NON_VEG_ITEMS):
                return False
            if any(d in meal_lower for d in DAIRY_ITEMS):
                return False
                
        return True

    # Filter out initial defaults that violate preferences
    breakfast = [m for m in breakfast if is_safe(m)]
    lunch = [m for m in lunch if is_safe(m)]
    dinner = [m for m in dinner if is_safe(m)]
    snacks = [m for m in snacks if is_safe(m)]

    # Enhance based on specific recommended foods and expanded ingredients
    all_inputs = recommended_foods + (expanded_ingredients or [])
    
    for food in all_inputs:
        lower = food.lower()
        
        # 1. Breakfast Mapping
        if any(x in lower for x in ["oats", "milk", "eggs", "poha", "ragi", "banana"]):
            if "oats" in lower: 
                m = "Oatmeal with flaxseeds and berries"
                if is_safe(m): breakfast.append(m)
            if "eggs" in lower: 
                m = "Spinach and mushroom omelette"
                if is_safe(m): breakfast.append(m)
            if "ragi" in lower: 
                m = "Ragi porridge with nuts"
                if is_safe(m): breakfast.append(m)
            if "poha" in lower: 
                m = "Vegetable poha with peanuts"
                if is_safe(m): breakfast.append(m)

        # 2. Lunch Mapping
        if any(x in lower for x in ["lentils", "rice", "chicken", "paneer", "vegetables", "dal", "fish"]):
            if "dal" in lower or "lentils" in lower: 
                m = "Moong dal with brown rice and salad"
                if is_safe(m): lunch.append(m)
            if "chicken" in lower: 
                m = "Grilled chicken with quinoa and steamed veggies"
                if is_safe(m): lunch.append(m)
            if "paneer" in lower: 
                m = "Paneer bhurji with whole wheat roti"
                if is_safe(m): lunch.append(m)
            if "fish" in lower: 
                m = "Steamed fish with lemon and sautéed greens"
                if is_safe(m): lunch.append(m)

        # 3. Snacks Mapping
        if any(x in lower for x in ["nuts", "seeds", "fruit", "berries", "beetroot", "dates"]):
            if "nuts" in lower or "almonds" in lower or "walnuts" in lower: 
                m = "Handful of mixed nuts (almonds, walnuts)"
                if is_safe(m): snacks.append(m)
            if "seeds" in lower: 
                m = "Chia seed pudding or roasted pumpkin seeds"
                if is_safe(m): snacks.append(m)
            if "beetroot" in lower: 
                m = "Fresh beetroot and carrot juice"
                if is_safe(m): snacks.append(m)
            if "dates" in lower: 
                m = "Dates and dried figs"
                if is_safe(m): snacks.append(m)

        # 4. Dinner Mapping
        if any(x in lower for x in ["soup", "khichdi", "light", "daliya", "curd"]):
            if "khichdi" in lower: 
                m = "Vegetable khichdi with cucumber raita"
                if is_safe(m): dinner.append(m)
            if "soup" in lower: 
                m = "Mixed vegetable clear soup"
                if is_safe(m): dinner.append(m)
            if "daliya" in lower: 
                m = "Vegetable daliya (broken wheat) upma"
                if is_safe(m): dinner.append(m)
            
    # Deduplicate, then shuffle for per-request variation
    b = _deduplicate(breakfast); random.shuffle(b)
    l = _deduplicate(lunch); random.shuffle(l)
    d = _deduplicate(dinner); random.shuffle(d)
    s = _deduplicate(snacks); random.shuffle(s)
    return {
        "breakfast": b[:4],
        "lunch": l[:3],
        "dinner": d[:3],
        "snacks": s[:4],
    }


def _generate_hydration_notes(parameters: Dict[str, dict]) -> str:
    """Generate hydration advice based on the detected conditions."""
    notes = ["Drink at least 8-10 glasses (2-2.5 liters) of water daily."]

    param_names = set(parameters.keys())

    if "Creatinine" in param_names or "Uric Acid" in param_names:
        notes.append(
            "Extra hydration recommended — aim for 10-12 glasses daily "
            "to support kidney function and flush uric acid."
        )

    if "Sodium" in param_names:
        notes.append(
            "Proper hydration helps maintain electrolyte balance and flush excess sodium."
        )

    if "Glucose" in param_names or "HbA1c" in param_names:
        notes.append(
            "Avoid sugary beverages — choose water, herbal teas, or infused water."
        )

    return " ".join(notes)
