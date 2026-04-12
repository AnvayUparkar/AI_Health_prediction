"""
Health Analysis Engine
======================

Modular component to analyze user health data (steps, heart rate, sleep)
using the Gemini API.
"""

import os
import json
import logging
import textwrap
from typing import Any, Dict

# Try to reuse the existing Gemini logic if possible
try:
    from backend.gemini_diet_planner import _call_gemini, parse_gemini_response
except ImportError:
    # Fallback if the above isn't accessible or we want strict isolation
    # For robust modularity in this project, we'll implement a clean caller here
    import google.generativeai as genai

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a senior doctor and dietician with 30+ years of experience.

Analyze the user's health data:
Steps: {steps}
Heart Rate: {avg_heart_rate}
Sleep: {sleep_hours}

Return:
* Health score (0–100)
* Risk level (Low/Medium/High)
* Health status (Excellent/Good/Moderate/Poor)
* Indian diet plan (as a list of strings)
* Recommendations (as a list of strings)

Return ONLY JSON in this format:
{{
  "health_score": number,
  "risk_level": "Low/Medium/High",
  "health_status": "Excellent/Good/Moderate/Poor",
  "diet_plan": ["item1", "item2"],
  "recommendations": ["rec1", "rec2"]
}}
"""

def generate_fallback_analysis(day_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a simple, rule-based analysis when Gemini is unavailable.
    """
    steps = day_data.get('steps', 0)
    score = 70 # Baseline
    if steps > 5000: score = 85
    elif steps > 10000: score = 95
    elif steps < 2000: score = 60
    
    status = "Active" if steps > 5000 else "Sedentary"
    risk = "Low" if steps > 3000 else "Moderate"
    
    return {
        "date": day_data.get('date'),
        "health_score": score,
        "risk_level": risk,
        "health_status": f"{status} (Standard Analysis)",
        "diet_plan": ["Stay hydrated", "Focus on lean proteins", "Add more vegetables"],
        "recommendations": ["Try to reach 5,000 steps daily", "Maintain consistent sleep schedules"]
    }

def analyze_health_data(steps: int, avg_heart_rate: float, sleep_hours: float) -> Dict[str, Any]:
    """
    Call Gemini API to analyze health metrics and return structured insights.
    """
    prompt = SYSTEM_PROMPT.format(
        steps=steps,
        avg_heart_rate=avg_heart_rate,
        sleep_hours=sleep_hours
    )

    try:
        # Use the robust caller from gemini_diet_planner with fallback support
        raw_text = _call_gemini(prompt)
        logger.debug("Gemini Health Analysis Response: %s", raw_text)
        
        # Parse using the robust parser which handles markdown and truncation
        return parse_gemini_response(raw_text)

    except Exception as e:
        logger.warning("Gemini Health Analysis failed. Using fallback safety net.")
        # Return a safe fallback structure
        return generate_fallback_analysis({
            "steps": steps, 
            "avg_heart_rate": avg_heart_rate, 
            "sleep_hours": sleep_hours,
            "date": "Today"
        })

SYSTEM_WEEKLY_PROMPT = """
You are a senior doctor and dietician with 30+ years of experience.

Analyze the user's weekly health data:
{weekly_data_json}

For each day, return:
* Health score (0–100)
* Risk level (Low/Medium/High)
* Health status (Excellent/Good/Moderate/Poor)
* Indian diet plan (as a list of strings)
* Recommendations (as a list of strings)

Return ONLY a JSON array of objects, one for each date provided. 
Each object must also include the "date" field from the input.
Format:
[
  {{
    "date": "YYYY-MM-DD",
    "health_score": number,
    "risk_level": "Low/Medium/High",
    "health_status": "Excellent/Good/Moderate/Poor",
    "diet_plan": ["item1", "item2"],
    "recommendations": ["rec1", "rec2"]
  }},
  ...
]
"""

def analyze_weekly_data(daily_metrics: list) -> list:
    """
    Call Gemini API to analyze a batch of health metrics.
    """
    prompt = SYSTEM_WEEKLY_PROMPT.format(
        weekly_data_json=json.dumps(daily_metrics, indent=2)
    )

    try:
        # Use the robust caller from gemini_diet_planner with fallback support
        raw_text = _call_gemini(prompt)
        logger.debug("Gemini Weekly Analysis Response: %s", raw_text)
        
        # Parse using the robust parser which handles markdown and truncation
        data = parse_gemini_response(raw_text)
        
        # If the robust parser returned a dict, we extract the array we need.
        # But wait, our batch prompt expects an array. Let's handle both.
        if isinstance(data, list):
            return data
            
        # Gemini returned a dict instead of a list — activate safety net for all days
        logger.warning("[HealthAnalyzer] Gemini returned dict instead of list — using rule-based fallback for all days")
        return [generate_fallback_analysis(d) for d in daily_metrics]

    except Exception as e:
        logger.warning("Active Safety Net: Gemini AI unavailable. Using rule-based analysis for persistence.")
        # ALWAYS return safety net reports for every day to ensure data persistence
        return [generate_fallback_analysis(d) for d in daily_metrics]
