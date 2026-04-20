import json
from datetime import datetime
from backend.fallback_diet_engine import fallback_diet_engine

def get_risk_level(alerts):
    """Determine risk level from alerts."""
    if not alerts:
        return "LOW"
    alert_types = [a.get('type', '').upper() for a in alerts]
    if "CRITICAL" in alert_types:
        return "CRITICAL"
    if "HIGH" in alert_types:
        return "HIGH"
    if "WARNING" in alert_types:
        return "MODERATE"
    return "LOW"

def _map_trends_to_diet_input(trends, risk_level):
    """
    Transforms vital trends into the format `fallback_diet_engine` expects.
    We convert the vitals into 'lab markers' for the engine.
    """
    input_data = {}
    
    glucose_avg = trends.get('glucose', {}).get('average', 100)
    glucose_trend = trends.get('glucose', {}).get('trend', 'STABLE')
    if glucose_avg > 140 or glucose_trend in ["INCREASING", "STRONGLY_INCREASING"]:
        input_data["Glucose"] = {"value": glucose_avg, "unit": "mg/dL"}
        
    bp_sys_avg = trends.get('bp_systolic', {}).get('average', 120)
    bp_sys_trend = trends.get('bp_systolic', {}).get('trend', 'STABLE')
    if bp_sys_avg > 130 or bp_sys_trend in ["INCREASING", "STRONGLY_INCREASING"]:
        input_data["Blood Pressure (Systolic)"] = {"value": bp_sys_avg, "unit": "mmHg"}

    spo2_avg = trends.get('spo2', {}).get('average', 98)
    if spo2_avg < 95:
        input_data["SpO2"] = {"value": spo2_avg, "unit": "%"}

    # Hack to force specific conditions in the condition engine
    clinical_summary = []
    if "Glucose" in input_data and glucose_avg > 140:
        clinical_summary.append("Patient has hyperglycemia.")
    elif "Glucose" in input_data and glucose_avg < 70:
        clinical_summary.append("Patient has hypoglycemia.")
        
    if "Blood Pressure (Systolic)" in input_data and bp_sys_avg > 130:
        clinical_summary.append("Patient has hypertension.")
    elif "Blood Pressure (Systolic)" in input_data and bp_sys_avg < 90:
        clinical_summary.append("Patient has hypotension.")
        
    if "SpO2" in input_data:
        clinical_summary.append("Patient is facing hypoxia.")
        
    raw_text_pad = " ".join(clinical_summary)
    
    return input_data, raw_text_pad

def generate_fallback_monitoring_text(patient_data: dict, trends: dict, alerts: list) -> str:
    """
    Generates a deeply structured, logic-based clinical summary that identically
    matches the requested Peer-to-Peer Gemini prompt output, leveraging the USDA
    Fallback Diet Engine for the Diet Plan.
    """
    
    # 1. Evaluate Risk
    risk_level = get_risk_level(alerts)
    risk_justification = "Patient vitals are stable and within normal parameters."
    if risk_level == "CRITICAL":
        risk_justification = "Multiple parameters severely out of bounds requiring immediate intervention."
    elif risk_level == "HIGH":
        risk_justification = "Elevated risk due to compounding abnormal acute vital trends."
    elif risk_level == "MODERATE":
        risk_justification = "Early warning indicators triggered in recent tracking windows."

    # 2. Extract specific trend states
    glucose_trend = trends.get("glucose", {})
    glucose_val = glucose_trend.get("average", "N/A")
    glucose_dir = glucose_trend.get("trend", "STABLE")
    
    bp_sys_trend = trends.get("bp_systolic", {})
    bp_sys_val = bp_sys_trend.get("average", "N/A")
    bp_sys_dir = bp_sys_trend.get("trend", "STABLE")
    
    spo2_trend = trends.get("spo2", {})
    spo2_val = spo2_trend.get("average", "N/A")
    
    # 3. Formulate Clinical Insight & Root Causes based on heuristics
    insight_components = []
    root_causes = []
    actions = []
    
    is_diabetic_high = str(glucose_val) != "N/A" and (float(glucose_val) > 140 or glucose_dir in ["INCREASING", "STRONGLY_INCREASING"])
    is_diabetic_low = str(glucose_val) != "N/A" and float(glucose_val) < 70
    is_hypertensive = str(bp_sys_val) != "N/A" and (float(bp_sys_val) > 130 or bp_sys_dir in ["INCREASING", "STRONGLY_INCREASING"])
    is_hypotensive = str(bp_sys_val) != "N/A" and float(bp_sys_val) < 90
    is_hypoxic = str(spo2_val) != "N/A" and float(spo2_val) < 95

    # Base Insights
    if is_diabetic_high and is_hypertensive:
        insight_components.append("Patient exhibiting compounded metabolic stress characterized by both increasing glycemic burden and elevated vascular resistance.")
        root_causes.append("Insulin resistance and high glycemic variability.")
        root_causes.append("Systemic vascular resistance indicating unmanaged essential hypertension or sympathetic drive.")
        actions.append("Initiate 4-hourly blood glucose (CBG) monitoring.")
        actions.append("Review continuous telemetry and antihypertensive schedule.")
    elif is_diabetic_high:
        insight_components.append(f"Patient exhibits uncontrolled glycemic variation, averaging {glucose_val} mg/dL.")
        root_causes.append("Postprandial glycemic spikes due to dietary load or reduced cellular insulin sensitivity.")
        actions.append("Initiate strict glycemic monitoring and review sliding scale insulin if applicable.")
    elif is_diabetic_low:
        insight_components.append(f"Patient exhibits severe hypoglycemic trends, dropping to {glucose_val} mg/dL.")
        root_causes.append("Excessive insulin dosage or delayed nutrient absorption (missed meals).")
        actions.append("Administer rapid-acting oral glucose immediately.")
        actions.append("Review recent timing of meals and insulin administration.")

    if is_hypertensive:
        insight_components.append(f"Patient presenting with sustained elevation in blood pressure, trending {bp_sys_dir.lower().replace('_', ' ')}.")
        root_causes.append("Vascular resistance and potentially high sodium retention.")
        actions.append("Limit sodium intake strictly to <2g/day and monitor vitals q6h.")
    elif is_hypotensive:
        insight_components.append(f"Significant drop in vascular pressure detected ({bp_sys_val} mmHg).")
        root_causes.append("Potential hypovolemia, dehydration, or adverse reaction to antihypertensive agents.")
        actions.append("Initiate aggressive IV fluid resuscitation (Normal Saline).")
        actions.append("Withhold next dose of BP-lowering medications pending physician clearance.")
    
    if is_hypoxic:
        insight_components.append("Notable desaturation trending, indicating potential respiratory compromise.")
        root_causes.append("Reduced pulmonary diffusion or developing pulmonary infiltrates.")
        actions.append("Initiate continuous SpO2 monitoring and supply supplemental O2 (target >94%).")
        actions.append("Encourage incentive spirometry and upright positioning.")
        
    if not insight_components:
        insight_components.append("Patient is clinically stable with vitals tracking closely to established baseline norms.")
        root_causes.append("Ongoing physiological recovery.")
        actions.append("Continue current standard-of-care hospital ward monitoring (q12h vitals).")
        actions.append("Promote early mobilization to prevent DVT.")

    clinical_insight = " ".join(insight_components)

    # 4. Integrate with USDA Diet Engine
    diet_input, fake_summary = _map_trends_to_diet_input(trends, risk_level)
    diet_engine_result = fallback_diet_engine(input_data=diet_input, raw_text=fake_summary)
    meal_plan = diet_engine_result.get("meal_plan", {})
    
    def format_meal(meal_key, fallback_items):
        items = meal_plan.get(meal_key, [])
        if not items:
            items = fallback_items
        return ", ".join(items)

    # 5. Assemble Final Text
    text_blocks = []
    text_blocks.append(f"Clinical Insight:\n{clinical_insight}")
    text_blocks.append(f"Risk Level:\n{risk_level} - {risk_justification}")
    
    text_blocks.append("Root Cause:\n" + "\n".join([f"* {cause}" for cause in root_causes]))
    text_blocks.append("Recommended Actions:\n" + "\n".join([f"* {act}" for act in actions]))
    
    text_blocks.append("Diet Plan:")
    text_blocks.append(f"Breakfast: {format_meal('breakfast', ['Oatmeal (Low GI)', 'Lemon Water'])}")
    text_blocks.append(f"Lunch: {format_meal('lunch', ['Brown Rice', 'Lentil Soup (Unsalted)'])}")
    text_blocks.append(f"Snacks: {format_meal('snack', ['Roasted Makhana', 'Buttermilk'])}")
    text_blocks.append(f"Dinner: {format_meal('dinner', ['Multigrain Roti', 'Vegetable Stew'])}")
    
    reasoning_base = "Chosen meals utilize precision USDA Foundation foods tailored to dynamically counter identified metabolic stressors."
    text_blocks.append(f"Reasoning:\n{reasoning_base}")

    return "\n\n".join(text_blocks)
