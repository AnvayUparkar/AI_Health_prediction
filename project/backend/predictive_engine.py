"""
Predictive Intelligence Layer for Clinical Decision Support.
Detects approaching critical states before they occur based on vital trends.
"""

def detect_approaching_critical(vitals, trends):
    """
    Analyzes trends and current vitals to identify patients at risk 
    of crossing into critical thresholds.
    """
    flags = []

    # Map trend names from trend_engine.py to the detection logic
    # trend_engine uses: STRONGLY_INCREASING, INCREASING, STABLE, DECREASING, STRONGLY_DECREASING
    
    # Glucose risk: High and rising
    glucose_trend = trends.get("glucose", {}).get("trend", "STABLE")
    if glucose_trend in ["INCREASING", "STRONGLY_INCREASING"] and vitals.get("glucose", 0) > 150:
        flags.append("glucose_risk")

    # SpO2 risk: Low and falling
    spo2_trend = trends.get("spo2", {}).get("trend", "STABLE")
    if spo2_trend in ["DECREASING", "STRONGLY_DECREASING"] and vitals.get("spo2", 100) < 96:
        flags.append("spo2_risk")

    # BP risk: High and rising
    bp_sys_trend = trends.get("bp_systolic", {}).get("trend", "STABLE")
    if bp_sys_trend in ["INCREASING", "STRONGLY_INCREASING"] and vitals.get("bp_systolic", 0) > 140:
        flags.append("bp_risk")

    return flags

def generate_predictive_insight(vitals, trends):
    """
    Generates a structured predictive insight object if risks are detected.
    """
    if not vitals or not trends:
        return None

    flags = detect_approaching_critical(vitals, trends)

    if not flags:
        return None

    messages = []

    if "glucose_risk" in flags:
        messages.append("Glucose is rising and may cross critical range (>180 mg/dL)")

    if "spo2_risk" in flags:
        messages.append("Oxygen level is declining and may worsen (<90%)")

    if "bp_risk" in flags:
        messages.append("Blood pressure instability detected; systolic rising above 140")

    # Risk classification based on number of flags
    if len(flags) >= 2:
        risk_level = "HIGH"
        timeframe = "12–24 hours"
    else:
        risk_level = "MODERATE"
        timeframe = "24 hours"

    return {
        "type": "predictive_insight",
        "risk_level": risk_level,
        "timeframe": timeframe,
        "messages": messages,
        "recommended_actions": [
            "Increase monitoring frequency to every 2 hours",
            "Review current diet and medication efficacy",
            "Alert senior consultant if trend continues"
        ]
    }
