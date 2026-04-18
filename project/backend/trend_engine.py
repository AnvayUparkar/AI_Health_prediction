"""
Trend Analysis & Alert Generation Engine for Patient Monitoring.

Analyses time-series vitals data (glucose, BP, SpO2) to detect
concerning patterns and generate clinically-relevant alerts.
"""


# ── Clinical Thresholds ──────────────────────────────────────────────────────

THRESHOLDS = {
    "glucose": {"low": 70, "high": 180, "critical_high": 300, "critical_low": 54},
    "bp_systolic": {"low": 90, "high": 140, "critical_high": 180, "critical_low": 70},
    "bp_diastolic": {"low": 60, "high": 90, "critical_high": 120, "critical_low": 40},
    "spo2": {"low": 95, "critical_low": 90, "high": 999, "critical_high": 999},
}


# ── Core Trend Analysis ──────────────────────────────────────────────────────

def analyze_trend(data_array):
    """
    Analyse a numeric array and classify its trend.

    Steps:
      1. Compute average (smoothing proxy)
      2. Compute linear slope across data
      3. Count directional changes
      4. Classify into STRONGLY_INCREASING, INCREASING, STABLE,
         DECREASING, STRONGLY_DECREASING

    Returns dict with trend, slope, average, and direction_counts.
    """
    if not data_array or len(data_array) < 2:
        return {
            "trend": "INSUFFICIENT_DATA",
            "slope": 0,
            "average": data_array[0] if data_array else 0,
            "count_increase": 0,
            "count_decrease": 0,
        }

    # Step 1: Smoothing — simple mean
    avg = sum(data_array) / len(data_array)

    # Step 2: Slope (first-to-last linear estimate)
    slope = (data_array[-1] - data_array[0]) / (len(data_array) - 1)

    # Step 3: Directional counts
    count_increase = sum(
        1 for i in range(1, len(data_array)) if data_array[i] > data_array[i - 1]
    )
    count_decrease = sum(
        1 for i in range(1, len(data_array)) if data_array[i] < data_array[i - 1]
    )

    # Step 4: Classification
    if slope > 5:
        trend = "STRONGLY_INCREASING"
    elif slope > 0:
        trend = "INCREASING"
    elif slope < -5:
        trend = "STRONGLY_DECREASING"
    elif slope < 0:
        trend = "DECREASING"
    else:
        trend = "STABLE"

    return {
        "trend": trend,
        "slope": round(slope, 2),
        "average": round(avg, 2),
        "count_increase": count_increase,
        "count_decrease": count_decrease,
    }


# ── Alert Generation ─────────────────────────────────────────────────────────

def generate_monitoring_alert(trend_result, latest_value, metric_name):
    """
    Generate a clinical alert based on the trend classification and the
    most recent reading.

    Returns None if the situation is within acceptable bounds.
    Otherwise returns a dict:
      { type: CRITICAL | WARNING | INFO, message: str, metric: str }
    """
    trend = trend_result.get("trend", "STABLE")
    thresholds = THRESHOLDS.get(metric_name, {})

    critical_high = thresholds.get("critical_high", 999)
    critical_low = thresholds.get("critical_low", 0)
    high = thresholds.get("high", 999)
    low = thresholds.get("low", 0)

    # ── CRITICAL Alerts ───────────────────────────────────────────────────
    if latest_value >= critical_high:
        return {
            "type": "CRITICAL",
            "message": f"{_display_name(metric_name)} critically high at {latest_value}. Immediate attention required.",
            "metric": metric_name,
        }

    if latest_value <= critical_low:
        return {
            "type": "CRITICAL",
            "message": f"{_display_name(metric_name)} critically low at {latest_value}. Immediate attention required.",
            "metric": metric_name,
        }

    # SpO2 drops are always urgent
    if metric_name == "spo2" and latest_value < low:
        return {
            "type": "CRITICAL",
            "message": f"SpO2 dropped to {latest_value}%. Oxygen support may be needed.",
            "metric": metric_name,
        }

    # Strongly increasing with high value
    if trend == "STRONGLY_INCREASING" and latest_value > high:
        return {
            "type": "CRITICAL",
            "message": f"{_display_name(metric_name)} rising continuously — now {latest_value}. Trend is strongly upward.",
            "metric": metric_name,
        }

    # ── WARNING Alerts ────────────────────────────────────────────────────
    if trend in ("STRONGLY_INCREASING", "INCREASING") and latest_value > high:
        return {
            "type": "WARNING",
            "message": f"{_display_name(metric_name)} trending upward at {latest_value}. Monitor closely.",
            "metric": metric_name,
        }

    if trend in ("STRONGLY_DECREASING", "DECREASING") and latest_value < low:
        return {
            "type": "WARNING",
            "message": f"{_display_name(metric_name)} trending downward at {latest_value}. Monitor closely.",
            "metric": metric_name,
        }

    if latest_value > high:
        return {
            "type": "WARNING",
            "message": f"{_display_name(metric_name)} elevated at {latest_value}.",
            "metric": metric_name,
        }

    if latest_value < low:
        return {
            "type": "WARNING",
            "message": f"{_display_name(metric_name)} below normal at {latest_value}.",
            "metric": metric_name,
        }

    # ── INFO (Trend-only) ─────────────────────────────────────────────────
    if trend == "STRONGLY_INCREASING":
        return {
            "type": "INFO",
            "message": f"{_display_name(metric_name)} is rising steadily (slope {trend_result['slope']}/reading). Current: {latest_value}.",
            "metric": metric_name,
        }

    if trend == "STRONGLY_DECREASING":
        return {
            "type": "INFO",
            "message": f"{_display_name(metric_name)} is declining steadily (slope {trend_result['slope']}/reading). Current: {latest_value}.",
            "metric": metric_name,
        }

    return None


# ── Full Analysis Pipeline ───────────────────────────────────────────────────

def run_full_analysis(monitoring_records):
    """
    Given a list of PatientMonitoring dicts (already sorted chronologically),
    compute trends and alerts for all vitals.

    Returns:
    {
      "trends": { "glucose": {...}, "bp_systolic": {...}, ... },
      "alerts": [ { "type": ..., "message": ..., "metric": ... }, ... ]
    }
    """
    metrics = ["glucose", "bp_systolic", "bp_diastolic", "spo2"]
    trends = {}
    alerts = []

    for metric in metrics:
        values = [
            r[metric] for r in monitoring_records
            if r.get(metric) is not None
        ]

        trend_result = analyze_trend(values)
        trends[metric] = trend_result

        if values:
            alert = generate_monitoring_alert(trend_result, values[-1], metric)
            if alert:
                alerts.append(alert)

    return {"trends": trends, "alerts": alerts}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _display_name(metric_name):
    names = {
        "glucose": "Blood Glucose",
        "bp_systolic": "Systolic BP",
        "bp_diastolic": "Diastolic BP",
        "spo2": "SpO2",
    }
    return names.get(metric_name, metric_name)
