import os
import re
import json
import logging
import random
import requests
from typing import Dict, List, Any, Optional, Tuple

from backend.report_parser import detect_high_level_conditions, detect_conditions_from_text
from backend.usda_manager import usda_manager
from backend.indian_meal_builder import indian_meal_builder
from backend.clinical_validator import clinical_validator
from backend.services.variation_engine import variation_engine
from backend.nutrient_pipeline import get_enriched_food_profile, filter_unsafe_foods as pipeline_filter
from backend.report_diet_engine import derive_base_ingredients, expand_ingredients_with_mapper

logger = logging.getLogger(__name__)

# ===================================================================
# KNOWLEDGE BASE MANAGER (Hierarchical Expert System)
# ===================================================================

# ===================================================================
# KNOWLEDGE BASE MANAGER (Hierarchical Expert System)
# ===================================================================

class DietKnowledgeManager:
    """
    Expert system for nutritional counseling.
    Architecture: Condition -> Nutrient -> Food -> Scoring.
    """
    def __init__(self, json_path: str):
        self.path = json_path
        self.data = self._load_data()
        
    def _load_data(self) -> Dict[str, Any]:
        try:
            if not os.path.exists(self.path):
                logger.error("Knowledge base file not found: %s", self.path)
                return {}
            with open(self.path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to load dietary knowledge: %s", e)
            return {}

    def get_nutrients_for_conditions(self, conditions: List[str]) -> List[str]:
        nutrients = set()
        cmap = self.data.get("condition_nutrients", {})
        for cond in conditions:
            if cond in cmap:
                nutrients.update(cmap[cond])
        return list(nutrients)

    def get_foods_for_nutrients(self, nutrients: List[str]) -> List[str]:
        foods = set()
        nmap = self.data.get("nutrient_foods", {})
        for nut in nutrients:
            if nut in nmap:
                foods.update(nmap[nut])
        return list(foods)

    def get_avoid_data(self, conditions: List[str]) -> Dict[str, str]:
        """Returns map of food -> reason for avoidance"""
        avoid_map = {}
        amap = self.data.get("condition_avoid", {})
        for cond in conditions:
            if cond in amap:
                data = amap[cond]
                reason = data.get("reason", "Aggravates detected metabolic markers.")
                for food in data.get("foods", []):
                    avoid_map[food.lower()] = reason
        return avoid_map

    def get_food_details(self, food_name: str) -> Dict[str, Any]:
        return self.data.get("food_details", {}).get(food_name.lower(), {})

# Initialize the manager
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_PATH = os.path.join(BASE_DIR, "data", "dietary_knowledge.json")
expert_kb = DietKnowledgeManager(KNOWLEDGE_PATH)

# Scoring Weight Constants
CUISINE_BIAS = 5.0


# ===================================================================
# HIERARCHICAL SCORING & RECOMMENDATION ENGINE
# ===================================================================

def score_food_hierarchical(food_name: str, target_nutrients: List[str], avoid_map: Dict[str, str], input_data: Dict[str, Any] = {}, context: Dict[str, Any] = None) -> Tuple[float, Optional[str]]:
    """
    Advanced scoring utilizing Expert KB + USDA Biochemical Evidence + Lab Context + Clinical Context.
    Returns (score, block_reason)
    """
    score = 0.0
    name_clean = food_name.lower()
    details = expert_kb.get_food_details(name_clean)
    biochem_data = usda_manager.get_food_nutrients_local(name_clean)
    biochem = biochem_data.get("nutrients", {}) if biochem_data else {}
    
    # 1. Expert Nutrient Match (+2.0)
    food_tags = details.get("tags", [])
    for nut in target_nutrients:
        if nut in food_tags:
            score += 2.0
            
    # 2. USDA Biochemical Density Bonus (mg/100g)
    if biochem:
        for nut in target_nutrients:
            amount = biochem.get(nut, 0.0)
            if amount > 0:
                weight = 0.5 if nut in ["fiber", "protein"] else 2.0
                score += min((amount * weight), 5.0)

    # 3. [NEW] ARCHITECT'S CLINICAL CONTEXT SCORING
    if context:
        # A. Recommended Food Boost (+4.0)
        # Check for keyword matches in the boost set
        if any(keyword in name_clean for keyword in context.get("boost", [])):
            score += 4.0
            
        # B. Avoid Food Penalty (-10.0)
        if any(keyword in name_clean for keyword in context.get("avoid", [])):
            return -100.0, f"Contraindicated by clinical report findings."

        # C. Nutritional Goal Scoring
        goals = context.get("goals", {})
        if biochem:
            # Iron Goal
            if goals.get("iron") == "high" and biochem.get("iron", 0) > 2.0:
                score += 2.0
            # Sugar Goal
            if goals.get("sugar") == "low" and biochem.get("sugar", 0) > 10:
                score -= 3.0
            # Sodium Goal
            if goals.get("sodium") == "low" and biochem.get("sodium", 0) > 200:
                score -= 3.0

    # 4. Clinical Safety Gate (Transparent Filtering)
    if biochem:
        sodium = biochem.get("sodium", 0.0)
        if sodium > 350 and ("hypertension" in target_nutrients or "kidney_strain" in target_nutrients):
            return -100.0, f"High sodium ({sodium}mg) is contraindicated for renal/vascular stress markers."
            
        sugar = biochem.get("sugar", 0.0)
        if sugar > 12 and "prediabetes" in target_nutrients:
            return -100.0, f"High glycemic load ({sugar}g sugar) aggravates detected insulin resistance."

    # 5. Expert Conflict Check (Absolute Safety)
    if name_clean in avoid_map:
        return -100.0, avoid_map[name_clean]
            
    # 5. [NEW] Ingredient-First Bonus (+6.0)
    # If this food was explicitly derived from the patient's lab markers
    if context and "derived_ingredients" in context:
        if any(ing in name_clean for ing in context["derived_ingredients"]):
            score += 6.0

    # 6. Cuisine Preference Bonus (+5.0 for Indian Staples)
    if "indian_staple" in details.get("tags", []):
        score += CUISINE_BIAS
        
    return score, None

def resolve_diet_conflicts(recommended: List[str], avoid_map: Dict[str, str]) -> List[str]:
    """
    Ensures no overlap between recommended and avoid lists.
    Priority: Safety (Avoid list wins).
    """
    cleaned_recommended = []
    avoid_set = set(avoid_map.keys())
    
    for rec in recommended:
        food_name = rec.split(" — ")[0].split(" (")[0].lower()
        if food_name not in avoid_set:
            cleaned_recommended.append(rec)
        else:
            logger.warning("CLINICAL_VALIDATION | Conflict resolved: Removing %s from Recommended (found in Avoid)", food_name)
            
    return cleaned_recommended

# ===================================================================
# CLINICAL CONDITION MAP & VALIDATION
# ===================================================================

CONDITION_MAP = {
    "iron_deficiency_anemia": {
        "technical_name": "Iron-deficiency Anaemia",
        "explanation": {
            "Low": "Low hemoglobin and MCV suggest impaired erythropoiesis due to iron deficiency.",
            "High": "Elevated hemoglobin levels; requires clinical correlation to rule out polycythemia.",
            "default": "Hemoglobin markers deviate from clinical reference ranges."
        },
        "risk": "reduced oxygen delivery and significant fatigue",
        "solution": "Focus on high bioavailability iron and Vitamin C; Avoid tannins with meals.",
        "markers": ["Hemoglobin", "MCV"]
    },
    "prediabetes": {
        "technical_name": "Glycemic Dysregulation Indicators",
        "explanation": {
            "High": "Elevated HbA1c or Fasting Glucose suggests systemic insulin resistance or prediabetes.",
            "Low": "Low glucose levels (hypoglycemia) may indicate metabolic instability or medication impact.",
            "default": "Glucose metabolism markers deviate from clinical reference ranges."
        },
        "risk": "metabolic syndrome and vascular inflammation",
        "solution": "Prioritize complex grains and chromium; strictly limit glycemic spikes.",
        "markers": ["HbA1c", "Fasting Blood Sugar", "Glucose"]
    },
    "hypertriglyceridemia": {
        "technical_name": "Hypertriglyceridemia",
        "explanation": {
            "High": "Elevated triglycerides increase the risk of pancreatitis and heart disease.",
            "Low": "Very low triglycerides; may require evaluation for malabsorption or malnutrition.",
            "default": "Triglyceride levels deviate from optimal clinical ranges."
        },
        "risk": "cardiovascular distress and metabolic syndrome",
        "solution": "Minimize simple sugars and alcohol; focus on Omega-3 fatty acids.",
        "markers": ["Triglycerides"]
    },
    "low_hdl": {
        "technical_name": "Dyslipidemia (Low HDL)",
        "explanation": {
            "Low": "Low levels of 'good' cholesterol reduce arterial clearing efficiency.",
            "High": "Optimally high HDL levels support cardiovascular protection.",
            "default": "HDL cholesterol levels deviate from optimal clearing efficiency range."
        },
        "risk": "increased arterial plaque risk",
        "solution": "Increase physical activity and monounsaturated healthy fats.",
        "markers": ["HDL Cholesterol"]
    },
    "hyperlipidemia": {
        "technical_name": "Hyperlipidemia / Lipid Stress",
        "explanation": {
            "High": "High total/LDL cholesterol levels correlate with atherosclerotic risk.",
            "Low": "Low cholesterol levels; may indicate dietary insufficiency or hyperthyroidism.",
            "default": "Lipid profile markers deviate from cardiovascular safety ranges."
        },
        "risk": "cardiovascular disease and plaque accumulation",
        "solution": "Focus on soluble fiber and plant sterols; limit saturated fats.",
        "markers": ["Total Cholesterol", "LDL Cholesterol"]
    },
    "vitamin_b12_deficiency": {
        "technical_name": "Vitamin B12 Deficiency",
        "explanation": {
            "Low": "Deficiency in cobalamin affects neural integrity and RBC maturation.",
            "High": "Elevated B12; often due to supplementation or hepatic release.",
            "default": "Vitamin B12 levels deviate from neural stability ranges."
        },
        "risk": "neurological symptoms and megaloblastic fatigue",
        "solution": "Ensure dairy or fortified source intake; optimize gut health.",
        "markers": ["Vitamin B12"]
    },
    "hypocalcemia": {
        "technical_name": "Calcium Imbalance",
        "explanation": {
            "Low": "Insufficient serum calcium impacts musculoskeletal signaling.",
            "High": "Hypercalcemia; may indicate hyperparathyroidism or excessive intake.",
            "default": "Serum calcium levels deviate from musculoskeletal signaling ranges."
        },
        "risk": "bone density loss and muscular cramps",
        "solution": "Calcium-dense foods with Vitamin D support.",
        "markers": ["Calcium"]
    },
    "vitamin_d_deficiency": {
        "technical_name": "Vitamin D Imbalance",
        "explanation": {
            "Low": "Low Vitamin D restricts intestinal mineral absorption.",
            "High": "Elevated Vitamin D; usually due to excessive supplementation.",
            "default": "Vitamin D levels deviate from optimal mineral absorption ranges."
        },
        "risk": "impaired immunity and skeletal weakness",
        "solution": "Precursor sources (Sunlight/Mushrooms) and fortified intake.",
        "markers": ["Vitamin D"]
    },
    "high_uric_acid": {
        "technical_name": "Hyperuricaemia",
        "explanation": {
            "High": "Elevated uric acid levels may lead to monosodium urate crystal deposition.",
            "Low": "Low uric acid; usually clinically insignificant but can indicate molybdenum deficiency.",
            "default": "Uric acid levels deviate from solubility ranges."
        },
        "risk": "joint inflammation and gout development",
        "solution": "Systemic hydration (3L+) and purine restriction.",
        "markers": ["Uric Acid"]
    },
    "protein_deficiency": {
        "technical_name": "Protein Profile Imbalance",
        "explanation": {
            "Low": "Low albumin or total protein suggests net negative nitrogen balance.",
            "High": "Elevated protein/albumin often suggests dehydration or chronic inflammation.",
            "default": "Serum protein markers deviate from metabolic stability ranges."
        },
        "risk": "muscle atrophy and delayed structural repair",
        "solution": "High-quality lean protein titration.",
        "markers": ["Total Protein", "Albumin"]
    },
    "liver_stress": {
        "technical_name": "Hepatic (Liver) Stress",
        "explanation": {
            "High": "Elevated transaminase or GGT levels indicate hepatocyte strain or biliary congestion.",
            "Low": "Low liver enzymes; generally normal but can rarely indicate vitamin B6 deficiency.",
            "default": "Hepatic enzyme markers deviate from optimal detoxification ranges."
        },
        "risk": "impaired detoxification and metabolic toxicity",
        "solution": "Prioritize antioxidant-rich (Curcumin/Fiber) protocol; strictly zero hepatotoxins.",
        "markers": ["SGPT", "SGOT", "GGT", "Bilirubin Total", "Alkaline Phosphatase"]
    },
    "kidney_strain": {
        "technical_name": "Renal (Kidney) Markers",
        "explanation": {
            "High": "Increased creatinine or BUN levels suggest reduced glomerular filtering efficiency.",
            "Low": "Low creatinine levels often reflect low muscle mass or high hydration status.",
            "default": "Renal filtration markers deviate from optimal glomerular ranges."
        },
        "risk": "fluid imbalance and systemic waste accumulation",
        "solution": "Regulated protein (plant-preferred) and strictly low sodium intake.",
        "markers": ["Creatinine", "BUN", "Urea"]
    },
    "thyroid_issues": {
        "technical_name": "Thyroid Metabolic Imbalance",
        "explanation": {
            "High": "Elevated TSH may suggest hypothyroidism (underactive thyroid).",
            "Low": "Low TSH may suggest hyperthyroidism (overactive thyroid).",
            "default": "Abnormal TSH suggests disruption in systemic metabolic regulation."
        },
        "risk": "metabolic instability and chronic fatigue",
        "solution": "Optimized Selenium and Zinc; Iodine balance (if indicated).",
        "markers": ["TSH", "T3", "T4"]
    },
    "electrolyte_imbalance": {
        "technical_name": "Electrolyte Dysregulation",
        "explanation": {
            "High": "Elevated electrolyte levels (Hypernatremia/Hyperkalemia) impact cardiac conduction.",
            "Low": "Low electrolyte levels (Hyponatremia/Hypokalemia) affect cellular signaling.",
            "default": "Abnormal electrolyte levels affect systemic cellular signaling."
        },
        "risk": "cardiac conduction issues and fluid volume stress",
        "solution": "Mineral-specific titration (e.g., Potassium sources for High Sodium).",
        "markers": ["Sodium", "Potassium", "Chloride"]
    },
    "obesity": {
        "technical_name": "Metabolic Overload (Obesity)",
        "explanation": {
            "default": "BMI >= 30 indicates significant adipose tissue accumulation and metabolic stress."
        },
        "risk": "systemic inflammation, insulin resistance, and joint stress",
        "solution": "Focus on high-fiber, low-glycemic index foods and sustainable caloric deficit.",
        "markers": []
    },
    "underweight": {
        "technical_name": "Nutritional Insufficiency (Underweight)",
        "explanation": {
            "default": "BMI < 18.5 suggests insufficient caloric/nutrient reserve for optimal physiological function."
        },
        "risk": "immune dysfunction, muscle wasting, and bone density loss",
        "solution": "Focus on nutrient-dense healthy fats and protein-rich frequent small meals.",
        "markers": []
    }
}

def validate_and_deduplicate(conditions: List[str], input_data: Dict[str, Any]) -> List[str]:
    """
    MANDATORY VALIDATION LAYER:
    1. Removes conditions that don't have abnormal lab evidence.
    2. Deduplicates overlaps (e.g., keeping Hypertriglyceridemia over Hyperlipidemia).
    """
    valid_conditions = []
    
    # Validation
    for cond in conditions:
        if cond in CONDITION_MAP:
            markers = CONDITION_MAP[cond].get("markers", [])
            has_evidence = False
            for m in markers:
                if m in input_data:
                    # If status is missing, assume it's valid evidence if it exists at all
                    # (Fallback monitoring engine now adds status, but this adds robustness)
                    marker_info = input_data[m]
                    status = marker_info.get("status")
                    if status in ("Low", "High", "Borderline", "Critical", "Abnormal") or status is None:
                        has_evidence = True
                        break
            if not markers or has_evidence:
                valid_conditions.append(cond)

    # De-duplication Logic
    final_set = set(valid_conditions)
    
    # Rule: Hypertriglyceridemia + Hyperlipidemia -> Keep Hypertriglyceridemia (more specific)
    if "hypertriglyceridemia" in final_set and "hyperlipidemia" in final_set:
        final_set.discard("hyperlipidemia")
        logger.info("VALIDATION | Deduplicated: Hyperlipidemia removed in favor of Hypertriglyceridemia")

    return list(final_set)

def distribute_meals(top_foods: List[str], target_nutrients: List[str]) -> Dict[str, List[str]]:
    """
    Constructs a 5-slot synergistic meal plan.
    Prioritizes Indian Meal Pairings: [Carb + Protein + Fiber].
    """
    meal_plan = {
        "breakfast": [], "mid_morning": [], "lunch": [], "evening_snack": [], "dinner": []
    }
    
    used = set()
    
    # Categorize available top foods
    categories = {"breakfast": [], "lunch_dinner": [], "snack": [], "staple": [], "protein": [], "veggie": []}
    
    for food in top_foods:
        details = expert_kb.get_food_details(food)
        tags = details.get("tags", [])
        
        # Indian Staples take priority
        if "indian_staple" in tags: categories["staple"].append(food)
        if "meal_breakfast" in tags: categories["breakfast"].append(food)
        if "meal_lunch" in tags or "meal_dinner" in tags: categories["lunch_dinner"].append(food)
        if "meal_snack" in tags: categories["snack"].append(food)
        if "protein" in tags or "iron" in tags: categories["protein"].append(food)
        if "fiber" in tags or "antioxidants" in tags: categories["veggie"].append(food)

    def fill_slot(slot, type_keys, limit=3):
        for type_key in type_keys:
            for food in categories[type_key]:
                if food not in used and len(meal_plan[slot]) < limit:
                    meal_plan[slot].append(food.title())
                    used.add(food)
                    break

    # 1. Breakfast: Focus on Poha/Upma/Oats
    fill_slot("breakfast", ["breakfast", "staple"])
    
    # 2. Lunch & Dinner: Proper Pairing [Staple + Protein + Veggie]
    for slot in ["lunch", "dinner"]:
        fill_slot(slot, ["staple"])   # e.g. Roti
        fill_slot(slot, ["protein"]) # e.g. Dal
        fill_slot(slot, ["veggie"])  # e.g. Sabzi

    # 3. Snacks
    fill_slot("mid_morning", ["snack", "veggie"], limit=2)
    fill_slot("evening_snack", ["snack", "protein"], limit=2)

    # Fill empty slots with clinical placeholders
    fallbacks = {
        "breakfast": ["Poha with Vegetables", "Moong Dal Sprouts"],
        "mid_morning": ["Walnuts", "Pomegranate"],
        "lunch": ["Multigrain Roti", "Lentil Dal", "Vegetable Sabzi"],
        "evening_snack": ["Roasted Makhana", "Green Tea"],
        "dinner": ["Jowar Roti", "Moong Dal", "Bottle Gourd Sabzi"]
    }
    for slot, items in meal_plan.items():
        if not items:
            meal_plan[slot] = fallbacks.get(slot, ["Balanced Indian Portion"])
            
    return meal_plan

# ===================================================================
# ENGINE LOGIC
# ===================================================================

def fallback_diet_engine(input_data: Dict[str, Any], raw_text: Optional[str] = None, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Clinically accurate Expert Engine with dynamic meal planning.
    Includes controlled variability for dynamic outputs.
    """
    # 0. Set Daily Seed for controlled variability
    patient_id = input_data.get("patient_id", "generic_patient")
    variation_engine.set_daily_seed(patient_id)

    # 1. Detect & 2. Validate
    health_data = context.get("raw_analysis", {}).get("health_data") if context else None
    if not health_data and context:
        # Reconstruct health_data from context if needed
        health_data = {
            "age": context.get("age"),
            "weight": context.get("weight"),
            "height": context.get("height"),
            "activityLevel": context.get("activityLevel"),
            "dietaryPreference": context.get("diet_preference")
        }

    initial_conditions = detect_high_level_conditions(input_data, health_data=health_data)
    if raw_text:
        text_conditions = detect_conditions_from_text(raw_text)
        initial_conditions = list(set(initial_conditions + text_conditions))
    
    conditions = validate_and_deduplicate(initial_conditions, input_data)
    
    # [Step 1] Build Clinical Context Profile
    if not context:
        primary = conditions[0] if conditions else "general_wellness"
        context = {
            "conditions": conditions,
            "primary_condition": primary,
            "secondary_conditions": conditions[1:],
            "goals": [CONDITION_MAP[c]["technical_name"] for c in conditions],
            "avoid": []
        }
    
    # 🧠 NEW: Store derived ingredients in context for scoring boost
    activity_level = context.get("activityLevel", "moderate")
    context["derived_ingredients"] = expand_ingredients_with_mapper(derive_base_ingredients(input_data, {"activityLevel": activity_level}))

    logger.info("ENGINE | Clinical Context Initialized: Primary=%s", context.get("primary_condition", "General"))
    
    # 3. Hierarchical Recommendation Logic (Expert + USDA)
    target_nutrients = expert_kb.get_nutrients_for_conditions(conditions)
    avoid_map = expert_kb.get_avoid_data(conditions)
    
    # Merge Expert KB foods with USDA high-density sources
    candidate_foods = set(expert_kb.get_foods_for_nutrients(target_nutrients))
    
    for nut in target_nutrients:
        top_usda = usda_manager.get_top_foods(nut, limit=10)
        for uf in top_usda:
            candidate_foods.add(uf["name"])
    
    # 🧠 NEW INGREDIENT-FIRST EXPANSION
    activity_level = (context or {}).get("activityLevel", "moderate")
    base_needs = derive_base_ingredients(input_data, {"activityLevel": activity_level})
    mapper_ingredients = expand_ingredients_with_mapper(base_needs)
    
    for ing in mapper_ingredients:
        candidate_foods.add(ing)

    scored_candidates = []
    safety_registry = {} # food -> reason for block

    # Pre-populate registry with expert avoidance rules
    for food, reason in avoid_map.items():
        safety_registry[food.title()] = reason

    for food in list(candidate_foods):
        score, block_reason = score_food_hierarchical(food, target_nutrients, avoid_map, input_data, context=context)
        if score > 0:
            scored_candidates.append((food, score))
        elif block_reason:
            safety_registry[food.title()] = block_reason
            
    scored_candidates.sort(key=lambda x: x[1], reverse=True)
    all_candidates = [f[0] for f in scored_candidates]
    
    # 🍽️ DIETARY PREFERENCE FILTERING (Safety-First)
    from backend.indian_meal_builder import indian_meal_builder
    top_foods = indian_meal_builder._filter_by_dietary_preference(all_candidates, context)[:25]

    # 4. Final Output Formatting (Lab-Linked Justifications)
    recommended_with_reason = []
    
    # Get condition-nutrient-marker map for dynamic text
    marker_map = {}
    for c in conditions:
        for m in CONDITION_MAP[c]["markers"]:
            if m in input_data:
                marker_map[c] = f"{input_data[m]['value']} {input_data[m].get('unit', '')}"

    for food in top_foods[:12]: 
        details = expert_kb.get_food_details(food)
        
        # [PIPELINE] Decompose dish -> fetch USDA per ingredient -> aggregate
        enriched = get_enriched_food_profile(food)
        biochem = enriched.get("nutrients", {}).get("nutrients", {})
        
        benefit = details.get("benefits", "")
        # Link to lab markers if possible
        for cond, val in marker_map.items():
            if any(nut in target_nutrients for nut in expert_kb.get_nutrients_for_conditions([cond])):
                # If this food provides a nutrient for this condition
                food_nutrients = details.get("tags", []) + list(biochem.keys())
                target_uts = expert_kb.get_nutrients_for_conditions([cond])
                if any(tn in food_nutrients for tn in target_uts):
                    benefit = f"{details.get('benefits', '')} -- Supporting your marker ({val})."
                    break

        if not benefit and biochem:
            best_nut = max(biochem.items(), key=lambda x: x[1]) if biochem else (None, 0)
            if best_nut[0]:
                benefit = f"Biochemical potency: {best_nut[1]} of {best_nut[0].replace('_', ' ').title()} per 100g."
                
        if not benefit:
            benefit = "Clinical-grade substrate for metabolic balance."
            
        recommended_with_reason.append(f"{food.title()} -- {benefit}")

    # Conflict Resolution (Pre-flight check)
    recommended_with_reason = resolve_diet_conflicts(recommended_with_reason, avoid_map)

    # 5. Generate Dynamic Meal Plan with SYNERGISTIC OVERLAYS
    # Use USDA high-scored items to build the base plan
    plan = distribute_meals(top_foods, target_nutrients)

    # Overlay 1: Liver Stress (Antioxidant / Detox)
    if "liver_stress" in conditions:
        plan["breakfast"].append("Lemon Water (Detox support)")
        plan["lunch"].append("Turmeric Rice (Curcumin support)")
        plan["dinner"] = ["Moong Dal Soup", "Steamed Broccoli"]

    # Overlay 2: Kidney Strain (Low Sodium / Regulated Protein)
    if "kidney_strain" in conditions:
        plan["lunch"] = ["Rice (1 bowl)", "Lentil Dal (Limit portion)", "Bottle Gourd Sabzi"]
        plan["evening_snack"] = ["Apple (1 unit)"]
        # Remove high sodium or high protein items if any
        if "Spinach" in str(plan): plan["lunch"] = [i for i in plan["lunch"] if "Spinach" not in i]

    # Overlay 3: Hypoxia / Anemia (Iron & Oxygen Support)
    if "hypoxia" in conditions or "iron_deficiency_anemia" in conditions:
        plan["breakfast"].append("Pomegranate")
        plan["mid_morning"].append("Walnuts")
        plan["lunch"].append("Beetroot Salad")
        plan["evening_snack"].append("Amla Juice")
        plan["dinner"].append("Moringa Soup")

    # Overlay 4: Metabolic / Glucose
    if "prediabetes" in conditions or "hyperglycemia" in conditions:
        plan["breakfast"] = ["Savory Oats with Flaxseeds", "Moong Dal Sprouts"]
        plan["mid_morning"] = ["Almonds", "Soaked Seeds"]
        plan["evening_snack"].append("Cinnamon Tea")

    # Overlay 5: Thyroid (Selenium & Iodine)
    if "thyroid_issues" in conditions:
        plan["breakfast"].append("Brazil Nuts (Selenium support)")
        plan["lunch"].append("Seaweed (Natural Iodine source)")

    # Convert to structured clinical reasoning output
    def synthesize_clinical_explanation(meal_items: List[str], current_conditions: List[str]) -> str:
        reasons = []
        for item in meal_items:
            clean = item.split('(')[0].split(' with ')[0].strip().lower()
            details = expert_kb.get_food_details(clean)
            if details.get("benefits"):
                reasons.append(details["benefits"])
        
        if not reasons:
            return "Optimized biochemical synergy for your laboratory profile."
        
        # Combine leading benefits into a professional sentence
        distinct_reasons = []
        seen = set()
        for r in reasons:
            core = r.split(' supporting ')[0].split(' for ')[0].lower()
            if core not in seen:
                distinct_reasons.append(r)
                seen.add(core)
        
        explanation = " ".join(distinct_reasons[:2])
        
        # Add condition-specific prefix
        if current_conditions:
            pref = f"Targeting {', '.join([c.replace('_', ' ').title() for c in current_conditions[:2]])}: "
            return pref + explanation
            
        return explanation

    # Structure the meal plan using the strict Indian Meal Builder [Step 10]
    meal_plan = {}
    used_items = {"staples": set(), "dals": set(), "sabzis": set()}
    
    # Priority order for generation to ensure Selection Memory flows [Step 5]
    slots_priority = ["breakfast", "mid_morning", "lunch", "evening_snack", "dinner"]
    for slot in slots_priority:
        if slot in plan:
            # 🎲 Shuffle food inputs per-request for variation
            slot_foods = variation_engine.shuffle_candidates(plan[slot])
            # Pass clinical context for primary-condition-based shaping [Step 4]
            composed = indian_meal_builder.build_meal(
                slot_foods, 
                slot, 
                conditions=conditions, 
                used_items=used_items,
                context=context
            )
            composed["benefit"] = variation_engine.generate_explanation(
                synthesize_clinical_explanation(plan[slot], conditions)
            )
            meal_plan[slot] = composed

    # [Step 7] Final Clinical Validation & Auto-Correction Engine
    meal_plan = clinical_validator.validate_and_fix(meal_plan, conditions)

    # 6. Final descriptive issues with dynamic explanations
    descriptive_issues = []
    for cond in conditions:
        info = CONDITION_MAP[cond]
        lab_markers = []
        dominant_status = "Normal"
        
        for m in info["markers"]:
            if m in input_data:
                marker_data = input_data[m]
                val = marker_data.get("value", "?")
                unit = marker_data.get("unit", "")
                rng = marker_data.get("ref_range", "")
                status = marker_data.get("status", "Normal")
                
                lab_markers.append(f"{m} {val}{unit} (Range: {rng})")
                
                # Pick the most "abnormal" status as dominant for the explanation
                if status in ("Critical", "High", "Low"):
                    dominant_status = status
        
        # Select explanation based on dominant status
        explanation_options = info.get("explanation", {})
        explanation = explanation_options.get(dominant_status) or explanation_options.get("default", "Marker levels deviate from reference range.")
        
        des_str = f"{info['technical_name']} [Validated via: {', '.join(lab_markers)}] — {explanation}"
        descriptive_issues.append(des_str)

    detailed_analysis = [CONDITION_MAP[c]["solution"] for c in conditions]

    # 6. Synergy Pairing (Professional Protocol)
    synergy_rules = expert_kb.data.get("synergies", {})
    synergy_protocol = []
    for nut in target_nutrients:
        if nut in synergy_rules:
            rule = synergy_rules[nut]
            enhancers = rule.get("enhancers", [])
            if enhancers:
                synergy_protocol.append(f"Protocol [{nut.title()}]: {rule['protocol']}")

    return {
        "status": "Success",
        "conditions_profile": [CONDITION_MAP[c]["technical_name"] for c in conditions],
        "issues_detected": descriptive_issues or ["Optimization of general wellness markers."],
        "clinical_protocol": detailed_analysis or ["Focus on balanced whole-food nutrition."],
        "synergy_pairing": synergy_protocol or ["Ensure diversified whole-food intake."],
        "recommended_foods": recommended_with_reason,
        "foods_to_avoid": [f"{f} — {r}" for f, r in safety_registry.items()] or ["Refined sugar — Minimizes glycemic volatility."],
        "blocked_foods_safety": safety_registry,
        "meal_plan": meal_plan,
        "summary": "Full Clinical/Biochemical Protocol using USDA Evidence and Expert System heuristics.",
        "disclaimer": "Safety-First Deterministic Engine. Consult a physician for medical diagnosis."
    }
