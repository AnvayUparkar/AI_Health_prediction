"""
Gemini-Powered Step-Based Meal Planner
=======================================

Generates a personalized daily meal plan based on the user's
yesterday step count and activity level, using the Google Gemini API.

Architecture mirrors ``gemini_diet_planner.py`` — reuses:
  - ``_call_gemini()``  (robust caller with model fallback chain)
  - ``parse_gemini_response()`` (JSON parser with truncation repair)

Pipeline:
    yesterday_steps (int)
        → categorize_activity()
        → build_step_meal_prompt()
        → Gemini API
        → parse_gemini_response()
        → structured MealPlanResult (dict)

Usage::

    from backend.step_meal_planner import generate_step_meal_plan

    result = generate_step_meal_plan(5200)
    print(result["meal_plan"]["breakfast"]["items"])

No changes to existing diet/health analysis modules.
"""

from __future__ import annotations

import json
import logging
import textwrap
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Reuse the existing Gemini infrastructure
from backend.gemini_diet_planner import _call_gemini, parse_gemini_response


# ---------------------------------------------------------------------------
# ACTIVITY CATEGORISATION
# ---------------------------------------------------------------------------

def categorize_activity(steps: int) -> dict:
    """
    Categorize yesterday's step count into an activity level with
    clinical context for the Gemini prompt.

    Returns
    -------
    dict
        Keys: level, label, clinical_context
    """
    if steps < 3000:
        return {
            "level": "Low",
            "label": "Low Activity",
            "clinical_context": (
                "Patient logged fewer than 3,000 steps — classified as sedentary. "
                "Caloric expenditure is minimal. Dietary focus should be on: "
                "light, easily digestible meals to avoid caloric surplus; "
                "high-fibre foods to maintain gut motility despite low movement; "
                "adequate hydration; and micronutrient-dense foods to compensate "
                "for reduced sunlight/outdoor exposure."
            ),
        }
    elif steps <= 8000:
        return {
            "level": "Moderate",
            "label": "Moderate Activity",
            "clinical_context": (
                "Patient logged 3,000–8,000 steps — moderate activity. "
                "Metabolic demand is balanced. Dietary focus should be on: "
                "sustained energy from complex carbohydrates; adequate protein "
                "for muscle maintenance and repair; balanced macro distribution; "
                "and sufficient hydration to support moderate exertion."
            ),
        }
    else:
        return {
            "level": "High",
            "label": "High Activity",
            "clinical_context": (
                "Patient logged over 8,000 steps — high activity. "
                "Significant caloric expenditure and muscle micro-damage expected. "
                "Dietary focus should be on: high-quality protein for muscle recovery; "
                "complex carbohydrates for glycogen replenishment; anti-inflammatory "
                "foods; electrolyte-rich hydration; and calorie-dense meals to prevent "
                "energy deficit."
            ),
        }


# ---------------------------------------------------------------------------
# PROMPT BUILDER
# ---------------------------------------------------------------------------

def build_step_meal_prompt(steps: int, activity: dict) -> str:
    """
    Build a Gemini prompt for step-based meal plan generation.

    Uses the same Senior Doctor / Clinical Diet Planner persona
    as the existing ``gemini_diet_planner.py``, adapted for
    step-count-based nutritional planning.
    """

    role_block = textwrap.dedent("""\
        You are a Senior Doctor, Senior Clinical Diet Planner, Senior Nutrition
        Specialist, and Medical Diet Consultant with more than 30 years of
        clinical experience in:
          • Creating personalised diet plans based on physical activity levels,
            step counts, metabolic demand, and recovery nutrition
          • Indian and South-Asian clinical nutrition
          • Functional medicine and integrative dietary therapy
          • Safe, realistic, and affordable dietary guidance

        You always produce evidence-based, practical, and culturally relevant
        recommendations. You never give generic advice — every recommendation
        is based on the specific activity data provided.
    """)

    patient_block = textwrap.dedent(f"""\
        PATIENT ACTIVITY DATA (YESTERDAY):

        Steps Taken: {steps:,}
        Activity Level: {activity['label']} ({activity['level']})

        CLINICAL ASSESSMENT:
        {activity['clinical_context']}
    """)

    task_block = textwrap.dedent("""\
        YOUR TASK:

        Based on the patient's activity level and step count above, generate a
        comprehensive, personalised DAILY MEAL PLAN for today. Follow these steps:

        STEP 1 — ASSESS METABOLIC NEEDS
        Analyse the caloric expenditure from yesterday's activity. Determine
        macronutrient requirements (protein, carbs, fats) based on the activity level.

        STEP 2 — BUILD THE MEAL PLAN
        Create a practical, culturally relevant plan that:
          • Directly addresses the activity level's nutritional demands
          • Is realistic for daily Indian/home cooking
          • Uses specific food items, not vague categories
          • Includes portion guidance where applicable
          • Prioritises whole foods over supplements
          • Balances all three macronutrients appropriately

        STEP 3 — PROVIDE REASONING
        For each meal, briefly explain WHY those specific foods were chosen,
        linking back to the activity level and recovery/fueling needs.

        IMPORTANT CONSTRAINTS:
          • No extreme diets or unsafe restrictions
          • Assume the patient is Indian, middle-class, home-cooking
          • Focus on affordable, locally available ingredients
          • Consider digestive comfort and meal timing
    """)

    format_block = textwrap.dedent(f"""\
        OUTPUT FORMAT — VERY IMPORTANT:

        Respond with ONLY a valid JSON object. No markdown, no explanation
        outside the JSON. Use this exact schema:

        {{
          "activity_level": "{activity['level']}",
          "yesterday_steps": {steps},
          "clinical_assessment": "2-3 sentence assessment of the patient's activity and metabolic needs",
          "meal_plan": {{
            "breakfast": {{
              "title": "Descriptive meal title",
              "items": ["Specific food item 1", "Specific food item 2", "Specific food item 3"],
              "reasoning": "Clinical reasoning for this meal selection"
            }},
            "lunch": {{
              "title": "Descriptive meal title",
              "items": ["Specific food item 1", "Specific food item 2", "Specific food item 3"],
              "reasoning": "Clinical reasoning for this meal selection"
            }},
            "dinner": {{
              "title": "Descriptive meal title",
              "items": ["Specific food item 1", "Specific food item 2", "Specific food item 3"],
              "reasoning": "Clinical reasoning for this meal selection"
            }}
          }},
          "hydration_tips": [
            "Specific hydration advice based on activity level"
          ],
          "lifestyle_tips": [
            "Practical lifestyle tips that complement the meal plan"
          ],
          "safety_note": "Brief wellness disclaimer in 1 sentence."
        }}

        Be specific. Be practical. Be medically accurate.
        Do NOT hallucinate — only use the activity data provided.
    """)

    full_prompt = "\n".join([
        role_block,
        "=" * 70,
        patient_block,
        "=" * 70,
        task_block,
        "=" * 70,
        format_block,
    ])

    return full_prompt


# ---------------------------------------------------------------------------
# SAFETY-NET FALLBACK (when Gemini is unavailable)
# ---------------------------------------------------------------------------

_SAFETY_NET_MEALS = {
    "Low": {
        "activity_level": "Low",
        "clinical_assessment": (
            "Low activity (under 3,000 steps). Caloric expenditure is minimal. "
            "Focus on light, nutrient-dense meals to avoid caloric surplus."
        ),
        "meal_plan": {
            "breakfast": {
                "title": "Light Energising Breakfast",
                "items": [
                    "Oats porridge with seasonal fruits",
                    "Green tea or warm lemon water",
                    "A handful of soaked almonds",
                ],
                "reasoning": (
                    "Oats provide soluble fibre for sustained energy without caloric excess. "
                    "Fruits add micronutrients. Green tea supports metabolism."
                ),
            },
            "lunch": {
                "title": "Balanced Light Lunch",
                "items": [
                    "1 bowl dal (moong/masoor) with steamed rice",
                    "Seasonal vegetable sabzi",
                    "Cucumber-tomato salad with lemon",
                ],
                "reasoning": (
                    "Dal provides plant protein. Steamed rice is easily digestible. "
                    "Vegetables add fibre and micronutrients for a sedentary day."
                ),
            },
            "dinner": {
                "title": "Light Restorative Dinner",
                "items": [
                    "Mixed vegetable soup",
                    "1 multigrain roti with light sabzi",
                    "Warm turmeric milk before bed",
                ],
                "reasoning": (
                    "Light dinner prevents caloric surplus during sedentary recovery. "
                    "Turmeric milk supports anti-inflammatory processes and sleep quality."
                ),
            },
        },
        "hydration_tips": [
            "Drink at least 2L of water throughout the day",
            "Include warm water in the morning for digestion",
        ],
        "lifestyle_tips": [
            "Try to increase steps to at least 5,000 tomorrow",
            "Take a 15-minute post-meal walk to aid digestion",
        ],
        "safety_note": (
            "This is wellness guidance based on activity data, "
            "not a substitute for professional medical advice."
        ),
    },
    "Moderate": {
        "activity_level": "Moderate",
        "clinical_assessment": (
            "Moderate activity (3,000–8,000 steps). Balanced metabolic demand. "
            "Focus on sustained energy and adequate protein for muscle maintenance."
        ),
        "meal_plan": {
            "breakfast": {
                "title": "Protein-Rich Breakfast",
                "items": [
                    "2 boiled eggs or paneer paratha",
                    "1 glass warm milk with turmeric",
                    "Whole grain toast with peanut butter",
                ],
                "reasoning": (
                    "Protein at breakfast supports muscle maintenance after moderate activity. "
                    "Complex carbs provide sustained morning energy."
                ),
            },
            "lunch": {
                "title": "Balanced Macro Lunch",
                "items": [
                    "2 chapati with paneer/chicken curry",
                    "Dal tadka with jeera rice",
                    "Cucumber-tomato raita",
                ],
                "reasoning": (
                    "Balanced macro distribution supports moderate energy expenditure. "
                    "Raita aids digestion and provides probiotics."
                ),
            },
            "dinner": {
                "title": "Healthy Recovery Dinner",
                "items": [
                    "Moong dal khichdi with ghee",
                    "Mixed vegetable salad",
                    "Buttermilk (chaas)",
                ],
                "reasoning": (
                    "Khichdi is easily digestible and protein-rich. "
                    "Light dinner supports overnight recovery without excess calories."
                ),
            },
        },
        "hydration_tips": [
            "Drink 2.5–3L of water throughout the day",
            "Add nimbu pani (lemon water) with a pinch of salt post-activity",
        ],
        "lifestyle_tips": [
            "Maintain consistent meal timing for metabolic rhythm",
            "Aim for 7–8 hours of sleep for optimal recovery",
        ],
        "safety_note": (
            "This is wellness guidance based on activity data, "
            "not a substitute for professional medical advice."
        ),
    },
    "High": {
        "activity_level": "High",
        "clinical_assessment": (
            "High activity (over 8,000 steps). Significant caloric expenditure. "
            "Focus on high-protein recovery meals and glycogen replenishment."
        ),
        "meal_plan": {
            "breakfast": {
                "title": "High-Protein Power Breakfast",
                "items": [
                    "3 egg omelette with vegetables",
                    "Whole wheat toast with peanut butter",
                    "1 banana and a glass of milk",
                ],
                "reasoning": (
                    "High protein intake at breakfast is critical for muscle repair "
                    "after significant physical activity. Banana provides quick glycogen."
                ),
            },
            "lunch": {
                "title": "Carb + Protein Recovery Lunch",
                "items": [
                    "Steamed rice with chicken/paneer curry",
                    "Rajma or chole (chickpea) with roti",
                    "Curd (dahi) with a side of mixed salad",
                ],
                "reasoning": (
                    "Complex carbs replenish glycogen stores. Legumes and protein "
                    "support tissue repair. Curd provides probiotics for gut health."
                ),
            },
            "dinner": {
                "title": "Recovery & Repair Dinner",
                "items": [
                    "Grilled fish/tofu with steamed vegetables",
                    "Protein-rich moong dal soup",
                    "1 roti with palak (spinach) sabzi",
                ],
                "reasoning": (
                    "Lean protein at dinner supports overnight muscle repair. "
                    "Spinach provides iron and anti-inflammatory compounds. "
                    "Fibre-rich vegetables aid recovery digestion."
                ),
            },
        },
        "hydration_tips": [
            "Drink 3–4L of water throughout the day",
            "Add electrolyte-rich drinks (coconut water, ORS) post-activity",
            "Avoid excessive caffeine which can dehydrate",
        ],
        "lifestyle_tips": [
            "Include 10 minutes of stretching for muscle recovery",
            "Prioritise 8 hours of sleep for tissue repair",
            "Consider a post-workout protein snack (chana, sprouts)",
        ],
        "safety_note": (
            "This is wellness guidance based on activity data, "
            "not a substitute for professional medical advice."
        ),
    },
}


# ---------------------------------------------------------------------------
# MAIN PUBLIC API
# ---------------------------------------------------------------------------

def generate_step_meal_plan(steps: int) -> Dict[str, Any]:
    """
    Full pipeline: steps → activity level → Gemini prompt → meal plan.

    Parameters
    ----------
    steps : int
        Yesterday's step count.

    Returns
    -------
    dict
        Keys:
        ``meal_plan_data`` — structured Gemini output (parsed dict)
        ``source``         — "gemini" | "safety_net"
        ``error``          — error message if any (else None)
    """
    activity = categorize_activity(steps)

    prompt = build_step_meal_prompt(steps, activity)
    source = "gemini"
    meal_plan_data: Dict[str, Any] = {}
    error_msg: Optional[str] = None

    try:
        raw = _call_gemini(prompt)
        meal_plan_data = parse_gemini_response(raw)

        # Ensure critical fields exist
        if "meal_plan" not in meal_plan_data:
            raise ValueError("Gemini response missing 'meal_plan' key")

        # Inject activity data if Gemini missed it
        meal_plan_data.setdefault("activity_level", activity["level"])
        meal_plan_data.setdefault("yesterday_steps", steps)

        logger.info(
            "Gemini step meal plan generated for %d steps (%s activity)",
            steps,
            activity["level"],
        )

    except Exception as exc:
        error_msg = str(exc)
        logger.warning(
            "Gemini meal plan failed (%s). Using safety-net fallback.",
            error_msg,
        )
        source = "safety_net"
        meal_plan_data = _SAFETY_NET_MEALS.get(
            activity["level"],
            _SAFETY_NET_MEALS["Moderate"],
        )
        # Add step count to fallback
        meal_plan_data = {**meal_plan_data, "yesterday_steps": steps}

    return {
        "meal_plan_data": meal_plan_data,
        "source": source,
        "error": error_msg,
    }
