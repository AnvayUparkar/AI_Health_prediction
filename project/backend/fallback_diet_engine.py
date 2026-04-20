import os
import re
import json
import logging
import random
import requests
from typing import Dict, List, Any, Optional, Tuple

from backend.report_parser import detect_high_level_conditions, detect_conditions_from_text
from backend.usda_loader import usda_manager

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

# ===================================================================
# HIERARCHICAL SCORING & RECOMMENDATION ENGINE
# ===================================================================

def score_food_hierarchical(food_name: str, target_nutrients: List[str], avoid_map: Dict[str, str], input_data: Dict[str, Any] = {}) -> Tuple[float, Optional[str]]:
    """
    Advanced scoring utilizing Expert KB + USDA Biochemical Evidence + Lab Context.
    Returns (score, block_reason)
    """
    score = 0.0
    name_clean = food_name.lower()
    details = expert_kb.get_food_details(name_clean)
    biochem_data = usda_manager.get_food_biochemicals(name_clean)
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

        # 3. Clinical Safety Gate (Transparent Filtering)
        sodium = biochem.get("sodium", 0.0)
        if sodium > 350 and ("hypertension" in target_nutrients or "kidney_strain" in target_nutrients):
            return -100.0, f"High sodium ({sodium}mg) is contraindicated for renal/vascular stress markers."
            
        sugar = biochem.get("sugar", 0.0)
        if sugar > 12 and "prediabetes" in target_nutrients:
            return -100.0, f"High glycemic load ({sugar}g sugar) aggravates detected insulin resistance."

    # 4. Expert Conflict Check (Absolute Safety)
    if name_clean in avoid_map:
        return -100.0, avoid_map[name_clean]
            
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
        "explanation": "Low hemoglobin and MCV suggest impaired erythropoiesis due to iron deficiency.",
        "risk": "reduced oxygen delivery and significant fatigue",
        "solution": "Focus on high bioavailability iron and Vitamin C; Avoid tannins with meals.",
        "markers": ["Hemoglobin", "MCV"]
    },
    "prediabetes": {
        "technical_name": "Prediabetes / Insulin Sensitivity Indicators",
        "explanation": "Elevated HbA1c or Fasting Glucose suggests systemic insulin resistance.",
        "risk": "metabolic syndrome and vascular inflammation",
        "solution": "Prioritize complex grains and chromium; strictly limit glycemic spikes.",
        "markers": ["HbA1c", "Fasting Blood Sugar", "Glucose"]
    },
    "hypertriglyceridemia": {
        "technical_name": "Hypertriglyceridemia",
        "explanation": "Elevated triglycerides increase the risk of pancreatitis and heart disease.",
        "risk": "cardiovascular distress and metabolic syndrome",
        "solution": "Minimize simple sugars and alcohol; focus on Omega-3 fatty acids.",
        "markers": ["Triglycerides"]
    },
    "low_hdl": {
        "technical_name": "Low HDL Cholesterol",
        "explanation": "Low levels of 'good' cholesterol reduce arterial clearing efficiency.",
        "risk": "increased arterial plaque risk",
        "solution": "Increase physical activity and monounsaturated healthy fats.",
        "markers": ["HDL Cholesterol"]
    },
    "hyperlipidemia": {
        "technical_name": "Hyperlipidemia",
        "explanation": "High total/LDL cholesterol levels correlate with atherosclerotic risk.",
        "risk": "cardiovascular disease and plaque accumulation",
        "solution": "Focus on soluble fiber and plant sterols; limit saturated fats.",
        "markers": ["Total Cholesterol", "LDL Cholesterol"]
    },
    "vitamin_b12_deficiency": {
        "technical_name": "Vitamin B12 Deficiency",
        "explanation": "Deficiency in cobalamin affects neural integrity and RBC maturation.",
        "risk": "neurological symptoms and megaloblastic fatigue",
        "solution": "Ensure dairy or fortified source intake; optimize gut health.",
        "markers": ["Vitamin B12"]
    },
    "hypocalcemia": {
        "technical_name": "Hypocalcaemia",
        "explanation": "Insufficient serum calcium impacts musculoskeletal signaling.",
        "risk": "bone density loss and muscular cramps",
        "solution": "Calcium-dense foods with Vitamin D support.",
        "markers": ["Calcium"]
    },
    "vitamin_d_deficiency": {
        "technical_name": "Hypovitaminosis D",
        "explanation": "Low Vitamin D restricts intestinal mineral absorption.",
        "risk": "impaired immunity and skeletal weakness",
        "solution": "Precursor sources (Sunlight/Mushrooms) and fortified intake.",
        "markers": ["Vitamin D"]
    },
    "high_uric_acid": {
        "technical_name": "Hyperuricaemia",
        "explanation": "Elevated uric acid levels may lead to monosodium urate crystal deposition.",
        "risk": "joint inflammation and gout development",
        "solution": "Systemic hydration (3L+) and purine restriction.",
        "markers": ["Uric Acid"]
    },
    "protein_deficiency": {
        "technical_name": "Hypoproteinaemia Indicators",
        "explanation": "Low albumin or total protein suggests net negative nitrogen balance.",
        "risk": "muscle atrophy and delayed structural repair",
        "solution": "High-quality lean protein titration.",
        "markers": ["Total Protein", "Albumin"]
    },
    "liver_stress": {
        "technical_name": "Hepatic (Liver) Stress",
        "explanation": "Elevated transaminase or GGT levels indicate hepatocyte strain or biliary congestion.",
        "risk": "impaired detoxification and metabolic toxicity",
        "solution": "Prioritize antioxidant-rich (Curcumin/Fiber) protocol; strictly zero hepatotoxins.",
        "markers": ["SGPT", "SGOT", "GGT", "Bilirubin Total", "Alkaline Phosphatase"]
    },
    "kidney_strain": {
        "technical_name": "Renal (Kidney) Strain",
        "explanation": "Increased creatinine or BUN levels suggest reduced glomerular filtering efficiency.",
        "risk": "fluid imbalance and systemic waste accumulation",
        "solution": "Regulated protein (plant-preferred) and strictly low sodium intake.",
        "markers": ["Creatinine", "BUN", "Urea"]
    },
    "thyroid_issues": {
        "technical_name": "Thyroid Metabolic Imbalance",
        "explanation": "Abnormal TSH suggests disruption in the systemic metabolic regulation rate.",
        "risk": "metabolic instability and chronic fatigue",
        "solution": "Optimized Selenium and Zinc; Iodine balance (if indicated).",
        "markers": ["TSH", "T3", "T4"]
    },
    "electrolyte_imbalance": {
        "technical_name": "Electrolyte Dysregulation",
        "explanation": "Abnormal Sodium, Potassium, or Chloride levels affect cellular signaling.",
        "risk": "cardiac conduction issues and fluid volume stress",
        "solution": "Mineral-specific titration (e.g., Potassium sources for High Sodium).",
        "markers": ["Sodium", "Potassium", "Chloride"]
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
                    if status in ("Low", "High", "Borderline", "Critical") or status is None:
                        has_evidence = True
                        break
            if has_evidence:
                valid_conditions.append(cond)

    # De-duplication Logic
    final_set = set(valid_conditions)
    
    # Rule: Hypertriglyceridemia + Hyperlipidemia -> Keep Hypertriglyceridemia (more specific)
    if "hypertriglyceridemia" in final_set and "hyperlipidemia" in final_set:
        final_set.discard("hyperlipidemia")
        logger.info("VALIDATION | Deduplicated: Hyperlipidemia removed in favor of Hypertriglyceridemia")

    return list(final_set)

def distribute_meals(top_foods: List[str], avoid_set: set) -> Dict[str, List[str]]:
    """
    Logically distributes recommended foods into Breakfast, Lunch, Dinner, and Snack slots.
    """
def distribute_meals(top_foods: List[str], target_nutrients: List[str]) -> Dict[str, List[str]]:
    """
    Constructs a 5-slot synergistic meal plan using top-scored biochemical sources.
    """
    meal_plan = {
        "breakfast": [],
        "mid_morning": [],
        "lunch": [],
        "evening_snack": [],
        "dinner": []
    }

    # Internal helper for synergy lookup
    synergy_rules = expert_kb.data.get("synergies", {})
    used = set()

    for food in top_foods:
        if food in used: continue
        details = expert_kb.get_food_details(food)
        tags = details.get("tags", [])
        
        assigned_slot = None
        for meal_tag in ["meal_breakfast", "meal_lunch", "meal_dinner", "meal_snack"]:
            if meal_tag in tags:
                key = meal_tag.replace("meal_", "")
                if key == "snack":
                    # Distribute snacks between mid-morning and evening
                    slot = "mid_morning" if not meal_plan["mid_morning"] else "evening_snack"
                    if len(meal_plan[slot]) < 2:
                        meal_plan[slot].append(food.title())
                        assigned_slot = slot
                elif len(meal_plan[key]) < 2:
                    meal_plan[key].append(food.title())
                    assigned_slot = key
                
                if assigned_slot:
                    used.add(food)
                    # --- Synergy Layer ---
                    # Check if this food triggers a synergy protocol
                    for nut in tags:
                        if nut in synergy_rules:
                            rule = synergy_rules[nut]
                            for enhancer in rule.get("enhancers", []):
                                # Find a booster in the rest of top_foods
                                for booster in top_foods:
                                    if booster not in used:
                                        b_details = expert_kb.get_food_details(booster)
                                        if enhancer in b_details.get("tags", []):
                                            if len(meal_plan[assigned_slot]) < 3:
                                                meal_plan[assigned_slot].append(f"{booster.title()} (Synergy Booster)")
                                                used.add(booster)
                                            break
                    break # Next food
    
    # Fill empty slots with clinical placeholders
    fallbacks = {
        "breakfast": ["Hydration: Lemon Water", "Oats with Flaxseeds"],
        "mid_morning": ["Walnuts & Almonds"],
        "lunch": ["Moong Dal & Quinoa"],
        "evening_snack": ["Green Tea & Roasted Chana"],
        "dinner": ["Bottle Gourd Soup"]
    }
    for slot, items in meal_plan.items():
        if not items:
            meal_plan[slot] = fallbacks.get(slot, ["Balanced Whole Food Portion"])
            
    return meal_plan

# ===================================================================
# ENGINE LOGIC
# ===================================================================

def fallback_diet_engine(input_data: Dict[str, Any], raw_text: Optional[str] = None) -> Dict[str, Any]:
    """
    Clinically accurate Expert Engine with dynamic meal planning.
    """
    # 1. Detect & 2. Validate
    initial_conditions = detect_high_level_conditions(input_data)
    if raw_text:
        text_conditions = detect_conditions_from_text(raw_text)
        initial_conditions = list(set(initial_conditions + text_conditions))
    
    conditions = validate_and_deduplicate(initial_conditions, input_data)
    
    # 3. Hierarchical Recommendation Logic (Expert + USDA)
    target_nutrients = expert_kb.get_nutrients_for_conditions(conditions)
    avoid_map = expert_kb.get_avoid_data(conditions)
    avoid_set = set(avoid_map.keys())
    
    # Merge Expert KB foods with USDA high-density sources
    candidate_foods = set(expert_kb.get_foods_for_nutrients(target_nutrients))
    
    for nut in target_nutrients:
        top_usda = usda_manager.get_top_foods(nut, limit=10)
        for uf in top_usda:
            candidate_foods.add(uf["name"])
    
    scored_candidates = []
    safety_registry = {} # food -> reason for block

    # Pre-populate registry with expert avoidance rules
    for food, reason in avoid_map.items():
        safety_registry[food.title()] = reason

    for food in list(candidate_foods):
        score, block_reason = score_food_hierarchical(food, target_nutrients, avoid_map, input_data)
        if score > 0:
            scored_candidates.append((food, score))
        elif block_reason:
            safety_registry[food.title()] = block_reason
            
    scored_candidates.sort(key=lambda x: x[1], reverse=True)
    top_foods = [f[0] for f in scored_candidates[:25]] 

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
        biochem_data = usda_manager.get_food_biochemicals(food)
        biochem = biochem_data.get("nutrients", {}) if biochem_data else {}
        
        benefit = details.get("benefits", "")
        # Link to lab markers if possible
        for cond, val in marker_map.items():
            if any(nut in target_nutrients for nut in expert_kb.get_nutrients_for_conditions([cond])):
                # If this food provides a nutrient for this condition
                food_nutrients = details.get("tags", []) + list(biochem.keys())
                target_uts = expert_kb.get_nutrients_for_conditions([cond])
                if any(tn in food_nutrients for tn in target_uts):
                    benefit = f"{details.get('benefits', '')} — Supporting your marker ({val})."
                    break

        if not benefit and biochem:
            best_nut = max(biochem.items(), key=lambda x: x[1]) if biochem else (None, 0)
            if best_nut[0]:
                unit = biochem_data.get("units", {}).get(best_nut[0], "units")
                benefit = f"Biochemical potency: {best_nut[1]} {unit} of {best_nut[0].replace('_', ' ').title()} per 100g."
                
        if not benefit:
            benefit = "Clinical-grade substrate for metabolic balance."
            
        recommended_with_reason.append(f"{food.title()} — {benefit}")

    # Conflict Resolution (Pre-flight check)
    recommended_with_reason = resolve_diet_conflicts(recommended_with_reason, avoid_map)

    # 5. Generate Dynamic Meal Plan with SYNERGISTIC OVERLAYS
    # Base Plan (Healthy Balanced)
    plan = {
        "breakfast": ["Poha with Vegetables", "Milk"],
        "mid_morning": ["Walnuts & Almonds"],
        "lunch": ["Multigrain Roti", "Lentil Dal", "Vegetable Sabzi", "Curd"],
        "evening_snack": ["Green Tea", "Roasted Makhana"],
        "dinner": ["Roti", "Lentil Dal", "Bottle Gourd Sabzi"]
    }

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
        plan["lunch"].append("Beetroot Salad")
        plan["dinner"].append("Moringa Soup")

    # Overlay 4: Metabolic / Glucose
    if "prediabetes" in conditions or "hyperglycemia" in conditions:
        plan["breakfast"] = ["Oats with Flaxseeds", "Moong Dal Sprouts"]
        plan["evening_snack"].append("Cinnamon Tea")

    # Overlay 5: Thyroid (Selenium & Iodine)
    if "thyroid_issues" in conditions:
        plan["breakfast"].append("Brazil Nuts (Selenium support)")
        plan["lunch"].append("Seaweed (Natural Iodine source)")

    # Convert to structured clinical reasoning output
    def get_reasoning(meal_items):
        reasons = []
        for item in meal_items:
            # Handle common multi-word items or variations
            clean = item.split('(')[0].split(' with ')[0].strip().lower()
            
            # Sub-string match or exact match
            details = {}
            if clean in expert_kb.data.get("food_details", {}):
                details = expert_kb.get_food_details(clean)
            else:
                # Try simple word match (e.g. "Moong Dal Soup" -> "Moong Dal")
                for key in expert_kb.data.get("food_details", {}):
                    if key in clean or clean in key:
                        details = expert_kb.get_food_details(key)
                        break

            if details.get("benefits"):
                reasons.append(details["benefits"])
            
            # USDA Biochemical check
            biochem = usda_manager.get_food_biochemicals(clean)
            if not biochem and " " in clean: # try base word
                biochem = usda_manager.get_food_biochemicals(clean.split()[-1])
            
            if biochem:
                nuts = biochem.get("nutrients", {})
                if "kidney_strain" in conditions and nuts.get("sodium", 0) < 50:
                    reasons.append("Low sodium supports renal stability.")
                if "liver_stress" in conditions and "antioxidants" in details.get("tags", []):
                    reasons.append("High antioxidants assist hepatic recovery.")
        return " ".join(list(set(reasons))[:2])

    meal_plan = {
        slot: {
            "items": items,
            "reasoning": get_reasoning(items)
        } for slot, items in plan.items()
    }

    avoid_with_reason = []
    for food, reason in avoid_map.items():
        avoid_with_reason.append(f"{food.title()} — {reason}")
    avoid_with_reason = list(set(avoid_with_reason))[:10] # limit 10

    # descriptive issues
    descriptive_issues = []
    for cond in conditions:
        info = CONDITION_MAP[cond]
        lab_markers = []
        for m in info["markers"]:
            if m in input_data:
                val = input_data[m].get("value", "?")
                unit = input_data[m].get("unit", "")
                rng = input_data[m].get("ref_range", "")
                lab_markers.append(f"{m} {val}{unit} (Range: {rng})")
        des_str = f"{info['technical_name']} [Validated via: {', '.join(lab_markers)}] — {info['explanation']}"
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
