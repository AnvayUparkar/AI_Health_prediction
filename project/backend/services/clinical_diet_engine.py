import random
import os
import logging
from backend.usda_loader import usda_manager
from backend.fallback_diet_engine import expert_kb

logger = logging.getLogger(__name__)

def generate_clinical_diet(patient_data: dict, trend_data: dict):
    """
    Upgraded multi-condition clinical diet engine.
    Responsive to SpO2 (Hypoxia), Glucose (Hyperglycemia), and BP (Hypertension).
    """
    
    # 1. TREND CALCULATIONS
    def calculate_metrics(values):
        if not values or len(values) == 0:
            return 0, 0
        avg = sum(values) / len(values)
        slope = (values[-1] - values[0]) / (len(values) - 1) if len(values) > 1 else 0
        return avg, slope

    glucose_vals = trend_data.get("glucose_values", [])
    bp_vals = trend_data.get("bp_values", [])
    spo2_vals = trend_data.get("spo2_values", [])
    
    avg_glucose, glucose_slope = calculate_metrics(glucose_vals)
    avg_bp, bp_slope = calculate_metrics(bp_vals)
    avg_spo2, spo2_slope = calculate_metrics(spo2_vals)

    # 2. CONDITION MAPPING
    detected_conditions = []
    if avg_glucose > 180 or glucose_slope > 5:
        detected_conditions.append("hyperglycemia")
    elif avg_glucose > 140:
        detected_conditions.append("prediabetes")
    
    # BP Detection Logic (Both ends)
    is_hypertension = avg_bp >= 140 or bp_slope > 3
    is_hypotension = avg_bp < 95 or (bp_vals and bp_vals[-1] < 90)
    
    if is_hypertension:
        detected_conditions.append("hypertension")
    elif is_hypotension:
        detected_conditions.append("hypotension")
    
    # SpO2 Responsive Logic
    is_hypoxia = avg_spo2 < 95 or (spo2_vals and spo2_vals[-1] < 94)
    if is_hypoxia:
        detected_conditions.append("hypoxia")

    # 3. NARRATIVE CONTEXT
    vitals_summary = []
    if "hyperglycemia" in detected_conditions: vitals_summary.append("elevated glucose")
    if "hypoxia" in detected_conditions: vitals_summary.append("declining oxygen saturation")
    if "hypertension" in detected_conditions: vitals_summary.append("hypertensive vascular pressure")
    if "hypotension" in detected_conditions: vitals_summary.append("hypotensive blood pressure")
    
    context = {
        "conditions": detected_conditions,
        "is_glucose_high": "hyperglycemia" in detected_conditions or "prediabetes" in detected_conditions,
        "is_hypoxia": "hypoxia" in detected_conditions,
        "is_hypertension": is_hypertension,
        "is_hypotension": is_hypotension,
        "avg_spo2": avg_spo2,
        "vitals_summary": ", ".join(vitals_summary) if vitals_summary else "stable vitals"
    }

    # 4. STRATEGY GENERATOR (With Random Variation for 'Regenerate')
    def generate_clinical_strategy(context):
        openers = [
            f"The dietary strategy is precisely calibrated for {context['vitals_summary']}.",
            f"Our nutritional intervention is currently optimized based on {context['vitals_summary']}.",
            f"Current physiological trends necessitate a protocol targeting {context['vitals_summary']}."
        ]
        
        hypoxia_variations = [
            "Clinical priority is given to nitrate-rich and iron-dense substrates to support vascular dilation and oxygen transport efficiency.",
            "Nutritional strategy focuses on optimizing hematologic capacity through targeted iron and nitrate loading.",
            "We are prioritizing oxygen-transport substrates to stabilize respiratory markers and optimize SpO2 levels."
        ]
        
        glucose_variations = [
            "Simultaneously, we maintain a defensive low-glycemic load to prevent metabolic volatility during respiratory stress.",
            "The protocol enforces metabolic stability by utilizing strictly complex, high-fiber structures for glycemic modulation.",
            "Concurrently, glycemic shielding is applied using USDA-verified fiber density to regulate insulin response."
        ]

        bp_variations = []
        if context["is_hypertension"]:
            bp_variations = [
                "Focus is placed on DASH-aligned potassium loading to modulate sodium impact and maintain vascular flexibility.",
                "Hypertensive management is prioritized through magnesium and potassium substrates to support systemic vasodilation.",
                "We are implementing a low-sodium foundation with elevated electrolyte substrates to assist in blood pressure regulation."
            ]
        elif context["is_hypotension"]:
            bp_variations = [
                "The protocol emphasizes clinical hydration and electrolyte-rich substrates to support blood pressure stability.",
                "Priority is given to osmolar-density support through moderate sodium and fluid retention substrates.",
                "The strategy focuses on preventing orthostatic variances through regular electrolyte intake and volume support."
            ]
        
        strategy = random.choice(openers) + " "
        
        if context["is_hypoxia"]:
            strategy += random.choice(hypoxia_variations) + " "
        
        if context["is_glucose_high"]:
            strategy += random.choice(glucose_variations) + " "

        if bp_variations:
            strategy += random.choice(bp_variations) + " "
        
        if not context["conditions"]:
            strategy += "The logic remains centered on localized nutrient density and preserving core metabolic stability."
            
        return strategy.strip()

    # 5. MEAL REASONING ENGINE
    def generate_meal_reasoning(items):
        reasons = []
        avoid_map = expert_kb.get_avoid_data(context["conditions"])
        
        for item in items:
            clean_name = item.split('(')[0].strip().lower()
            details = expert_kb.get_food_details(clean_name)
            
            # Priority 1: Clinical Benefit from KB
            kb_benefit = details.get("benefits", "")
            
            # Priority 2: USDA Biochemical Density
            biochem_data = usda_manager.get_food_biochemicals(clean_name)
            biochem_notes = ""
            if biochem_data:
                nuts = biochem_data.get("nutrients", {})
                if context["is_hypoxia"] and "iron" in details.get("tags", []):
                    biochem_notes = f" USDA verified iron content supports SpO2 stabilization."
                elif context["is_glucose_high"] and nuts.get("fiber", 0) > 2:
                    biochem_notes = f" High fiber ({nuts.get('fiber')}g) modulates glucose."
                elif context["is_hypertension"] and nuts.get("potassium", 0) > 300:
                    biochem_notes = f" High potassium ({nuts.get('potassium')}mg) supports vascular tension reduction."
                elif context["is_hypotension"] and "hydration" in details.get("tags", []):
                    biochem_notes = f" High water content supports blood volume stability."

            if kb_benefit:
                reasons.append(f"{kb_benefit}.{biochem_notes}")
            elif biochem_notes:
                reasons.append(biochem_notes.strip())

        return " ".join(reasons[:2])

    # 6. SYNERGISTIC MEAL PLANNER
    def generate_meal_plan(context):
        # Base Plan (Healthy Balanced)
        plan = {
            "breakfast": ["Poha (1 bowl) with Vegetables", "Milk (200ml)"],
            "lunch": ["Roti (2 units)", "Lentil Dal (1 bowl)", "Vegetable Sabzi", "Curd (100g)"],
            "snacks": ["Almonds (5-6)", "Green Tea"],
            "dinner": ["Roti (1 unit)", "Lentil Dal (1 bowl)", "Bottle Gourd Sabzi"]
        }

        # Overlay: Hyperglycemia (Low GI)
        if context["is_glucose_high"]:
            plan["breakfast"] = ["Oats (40g) with Skimmed Milk", "Moong Dal Sprouts (1 cup)"]
            plan["lunch"][0] = "Multigrain Roti (2 units)"
            plan["snacks"] = ["Roasted Makhana (1 bowl)", "Buttermilk (1 glass)"]
            plan["dinner"] = ["Moong Dal Khichdi (1 bowl)", "Steamed Vegetables"]

        # Overlay: BP - Hypertension (DASH focus)
        if context["is_hypertension"]:
            plan["breakfast"].append("Banana (1 unit)")
            plan["snacks"] = ["Pumpkin Seeds (20g)", "Coconut Water (1 unit)"]
            plan["lunch"].append("Cucumber Salad")

        # Overlay: BP - Hypotension (Hydration focus)
        if context["is_hypotension"]:
            plan["breakfast"] = ["Stuffed Paratha", "Curd (1 bowl)"] # Moderate sodium
            plan["snacks"] = ["Buttermilk with Salt (1 glass)", "Walnuts (3-4)"]
            plan["lunch"].append("Tomato Soup (1 bowl)")
            plan["dinner"].append("Vegetable Broth")

        # Overlay: Hypoxia (Iron & Nitrates) - HIGHER PRIORITY
        if context["is_hypoxia"]:
            plan["breakfast"].append("Pomegranate (1 bowl)")
            plan["lunch"].append("Beetroot Salad")
            plan["lunch"][2] = "Spinach Sabzi" 
            plan["snacks"].append("Dates (2 units)")
            plan["dinner"].append("Moringa Soup")

        return {
            slot: {
                "items": items,
                "reason": generate_meal_reasoning(items)
            } for slot, items in plan.items()
        }

    return {
        "strategy": generate_clinical_strategy(context),
        "meals": generate_meal_plan(context)
    }
