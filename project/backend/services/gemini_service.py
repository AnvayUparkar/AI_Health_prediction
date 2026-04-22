"""
Gemini AI Diet Recommendation Service.

Uses Google's Gemini API to generate clinically-informed diet plans
based on patient vitals trends and monitoring data.
"""
import os
import json
import requests
from typing import Optional, Dict, List
from functools import lru_cache

# Ensure env vars loaded
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'), override=False)
except ImportError:
    pass

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

# Model fallback chain — try each until one works
_MODEL_FALLBACK_CHAIN = [
    "gemini-3-pro-preview",
    # "gemini-3-pro-preview-09-2026",
    # "gemini-2.5-pro",
    # "gemini-2.5-flash-lite",
    # "gemini-2.5-flash",
    # "gemini-2.0-flash",
    # "gemini-flash-latest",
]

# In-memory cache: patient_id -> { result, timestamp }
_diet_cache: dict = {}
CACHE_TTL_SECONDS = 3600  # 1 hour


def generate_diet_recommendation(patient_data: dict, trends: dict, alerts: list, trend_raw: dict = None) -> dict:
    """
    Call Gemini API to generate a personalized diet recommendation.
    Tries multiple models in fallback chain if quota is exceeded.

    Args:
        patient_data: { name, age, sex, ward_number, ... }
        trends: { glucose: { trend, slope, average }, bp_systolic: {...}, ... }
        alerts: [ { type, message, metric }, ... ]
        trend_raw: { glucose_values, bp_values, spo2_values, ... }

    Returns:
        {
            breakfast: { items: [...], reasoning: str },
            lunch: { items: [...], reasoning: str },
            snacks: { items: [...], reasoning: str },
            dinner: { items: [...], reasoning: str },
            overall_reasoning: str,
            source: "gemini" | "fallback"
        }
    """
    api_key = os.environ.get('GEMINI_API_KEY', '')
    if not api_key:
        print("[GEMINI] No API key found. Using fallback.")
        return _fallback_diet(trends, trend_raw, patient_data)

    # Check cache
    pid = str(patient_data.get('patient_id', ''))
    cached = _diet_cache.get(pid)
    if cached:
        import time
        if time.time() - cached['timestamp'] < CACHE_TTL_SECONDS:
            print(f"[GEMINI] Returning cached diet for patient {pid}")
            return cached['result']

    # Build clinical prompt
    prompt = _build_prompt(patient_data, trends, alerts)

    # Try each model in the fallback chain
    for model_name in _MODEL_FALLBACK_CHAIN:
        url = f"{GEMINI_BASE_URL}/{model_name}:generateContent?key={api_key}"
        print(f"[GEMINI] Trying model: {model_name}...")

        try:
            response = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 2048,
                        "responseMimeType": "application/json",
                    }
                },
                timeout=30,
            )

            if response.status_code == 429:
                print(f"[GEMINI] Model {model_name} quota exceeded (429). Trying next...")
                continue

            if response.status_code != 200:
                print(f"[GEMINI] Model {model_name} error {response.status_code}: {response.text[:200]}")
                continue

            data = response.json()

            # Extract text from response — handle thinking models (2.5-flash)
            # which return multiple parts: [thinking_part, content_part]
            candidate = data['candidates'][0]['content']
            parts = candidate.get('parts', [])
            
            result = None
            
            # Strategy 1: Try each part in reverse order (content is usually last)
            for part in reversed(parts):
                part_text = part.get('text', '').strip()
                if not part_text:
                    continue
                try:
                    parsed = json.loads(part_text)
                    # Validate it has expected diet keys
                    if isinstance(parsed, dict) and 'breakfast' in parsed:
                        result = parsed
                        print(f"[GEMINI] ✅ Parsed JSON from part (model: {model_name})")
                        break
                except json.JSONDecodeError:
                    continue
            
            # Strategy 2: Concatenate all text parts and try to find JSON block
            if not result:
                all_text = ' '.join(p.get('text', '') for p in parts)
                # Find JSON block using regex
                import re
                json_match = re.search(r'\{[^{}]*"breakfast"[^{}]*\{.*?\}.*?\}', all_text, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group())
                        print(f"[GEMINI] ✅ Extracted JSON via regex (model: {model_name})")
                    except json.JSONDecodeError:
                        pass
            
            # Strategy 3: Try parsing the full raw text from the last part
            if not result:
                last_text = parts[-1].get('text', '') if parts else ''
                try:
                    result = json.loads(last_text)
                    print(f"[GEMINI] ✅ Parsed last part as JSON (model: {model_name})")
                except json.JSONDecodeError:
                    print(f"[GEMINI] ⚠️ Could not parse JSON from {model_name}: {last_text[:200]}")
                    continue  # Try next model

            if result and isinstance(result, dict) and 'breakfast' in result:
                result['source'] = 'gemini'
                result['model'] = model_name

                # Cache it
                import time
                _diet_cache[pid] = {'result': result, 'timestamp': time.time()}

                print(f"[GEMINI] ✅ Generated diet for patient {pid} using {model_name}")
                return result
            else:
                print(f"[GEMINI] ⚠️ Response from {model_name} missing expected keys, trying next model...")
                continue

        except json.JSONDecodeError as e:
            print(f"[GEMINI] JSON parse error from {model_name}: {e}")
            # Try to extract any useful text
            try:
                all_text = ' '.join(p.get('text', '') for p in data['candidates'][0]['content'].get('parts', []))
                return {
                    "breakfast": {"items": ["Balanced meal as recommended"], "reasoning": "AI recommendation pending"},
                    "lunch": {"items": ["Balanced meal as recommended"], "reasoning": "AI recommendation pending"},
                    "snacks": {"items": ["Light healthy snack"], "reasoning": "AI recommendation pending"},
                    "dinner": {"items": ["Light balanced dinner"], "reasoning": "AI recommendation pending"},
                    "overall_reasoning": all_text[:500] if all_text else "Unable to parse AI response",
                    "source": "gemini_partial",
                    "model": model_name
                }
            except Exception:
                continue

        except Exception as e:
            print(f"[GEMINI] Request to {model_name} failed: {e}")
            continue

    # All models exhausted — use fallback
    print("[GEMINI] All models exhausted. Using fallback diet.")
    return _fallback_diet(trends, trend_raw, patient_data)


def _build_prompt(patient_data: dict, trends: dict, alerts: list) -> str:
    """Build a detailed clinical nutrition prompt for Gemini."""
    
    diet_pref = patient_data.get('diet_preference', 'balanced')
    non_veg_prefs = patient_data.get('non_veg_preferences', [])
    allergies = patient_data.get('allergies', [])

    # Extract trend summaries
    glucose_trend = trends.get('glucose', {})
    bp_sys_trend = trends.get('bp_systolic', {})
    bp_dia_trend = trends.get('bp_diastolic', {})
    spo2_trend = trends.get('spo2', {})

    alert_summary = ""
    if alerts:
        alert_lines = [f"- [{a['type']}] {a['message']}" for a in alerts[:5]]
        alert_summary = "Active Clinical Alerts:\n" + "\n".join(alert_lines)

    prompt = f"""Act as an expert clinical nutritionist with 20 years of experience in hospital dietary management.

Patient Profile:
- Name: {patient_data.get('name', 'Unknown')}
- Age: {patient_data.get('age', 'Unknown')}
- Sex: {patient_data.get('sex', 'Unknown')}
- Ward: {patient_data.get('ward_number', 'General')}
- Diet Preference: {diet_pref}
{f"- Non-Veg Preferences: {', '.join(non_veg_prefs)}" if non_veg_prefs else ""}
{f"- CRITICAL ALLERGIES (STRICTLY AVOID): {', '.join(allergies)}" if allergies else ""}

Vitals Trend Summary (Last 2 Days):
- Blood Glucose: Trend={glucose_trend.get('trend', 'N/A')}, Average={glucose_trend.get('average', 'N/A')} mg/dL, Slope={glucose_trend.get('slope', 'N/A')}
- Systolic BP: Trend={bp_sys_trend.get('trend', 'N/A')}, Average={bp_sys_trend.get('average', 'N/A')} mmHg
- Diastolic BP: Trend={bp_dia_trend.get('trend', 'N/A')}, Average={bp_dia_trend.get('average', 'N/A')} mmHg
- SpO2: Trend={spo2_trend.get('trend', 'N/A')}, Average={spo2_trend.get('average', 'N/A')}%

{alert_summary}

Based on these clinical indicators and dietary preferences, generate a personalized daily diet plan.
Consider Indian dietary preferences and hospital food availability.

IMPORTANT SAFETY CONSTRAINTS:
1. ABSOLUTELY NO {", ".join(allergies) if allergies else "allergens mentioned above"}. Double check every meal.
2. STICK TO THE SAFETY WARNING: Always verify AI recommendations with a clinical professional.
3. If diet preference is vegetarian, do not suggest any meat/egg products.

Respond ONLY with valid JSON in this exact format:
{{
  "breakfast": {{
    "items": ["item1", "item2", "item3"],
    "reasoning": "clinical reasoning for this meal"
  }},
  "lunch": {{
    "items": ["item1", "item2", "item3"],
    "reasoning": "clinical reasoning for this meal"
  }},
  "snacks": {{
    "items": ["item1", "item2"],
    "reasoning": "clinical reasoning for this snack"
  }},
  "dinner": {{
    "items": ["item1", "item2", "item3"],
    "reasoning": "clinical reasoning for this meal"
  }},
  "overall_reasoning": "summary of dietary strategy based on patient trends"
}}"""

    return prompt


def _fallback_diet(trends: dict, trend_raw: dict = None, patient_data: dict = None) -> dict:
    """
    Deterministic fallback diet when Gemini is unavailable.
    Upgraded to generate narrative clinical recommendations.
    """
    try:
        from backend.services.clinical_diet_engine import generate_clinical_diet
        
        # Use provided raw trends or simulate from existing metrics
        if not trend_raw:
            trend_raw = {
                "glucose_values": [trends.get('glucose', {}).get('average', 120)],
                "bp_values": [trends.get('bp_systolic', {}).get('average', 120)],
                "spo2_values": [trends.get('spo2', {}).get('average', 98)],
                "meals_missed": False,
                "activity_level": "moderate"
            }
        
        # Call the new clinical engine
        result = generate_clinical_diet(patient_data or {}, trend_raw)
        
        # Map back to old UI structure to avoid breaking frontend
        meals = result.get('meals', {})
        return {
            "breakfast": {
                "items": meals.get('breakfast', {}).get('items', []),
                "reasoning": meals.get('breakfast', {}).get('reason', '')
            },
            "lunch": {
                "items": meals.get('lunch', {}).get('items', []),
                "reasoning": meals.get('lunch', {}).get('reason', '')
            },
            "snacks": {
                "items": meals.get('snacks', {}).get('items', []),
                "reasoning": meals.get('snacks', {}).get('reason', '')
            },
            "dinner": {
                "items": meals.get('dinner', {}).get('items', []),
                "reasoning": meals.get('dinner', {}).get('reason', '')
            },
            "overall_reasoning": result.get('strategy', ''),
            "source": "fallback"
        }
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Clinical fallback diet failed: {e}")
        # Secondary fallback to hardcoded if everything fails
        return {
            "breakfast": {"items": ["Idli", "Milk"], "reasoning": "Standard support."},
            "lunch": {"items": ["Rice", "Dal"], "reasoning": "Standard support."},
            "snacks": {"items": ["Fruit"], "reasoning": "Standard support."},
            "dinner": {"items": ["Chapati", "Soup"], "reasoning": "Standard support."},
            "overall_reasoning": "Standard hospital diet deployed due to engine limits.",
            "source": "fallback"
        }

def generate_clinical_consult(patient_data: dict, trends: dict, alerts: list) -> str:
    """
    Call Gemini API to generate a clinical consultant recommendation
    matching the requested peer-to-peer prompt.
    """
    from backend.fallback_monitoring_engine import generate_fallback_monitoring_text
    
    api_key = os.environ.get('GEMINI_API_KEY', '')
    if not api_key:
        print("[GEMINI] No API key found. Using fallback clinical copilot engine.")
        return generate_fallback_monitoring_text(patient_data, trends, alerts)
    
    glucose_trend = trends.get('glucose', {})
    bp_sys_trend = trends.get('bp_systolic', {})
    bp_dia_trend = trends.get('bp_diastolic', {})
    spo2_trend = trends.get('spo2', {})
    
    alert_summary = ""
    if alerts:
        alert_lines = [f"- [{a['type']}] {a['message']}" for a in alerts[:5]]
        alert_summary = "Active Clinical Alerts:\n" + "\n".join(alert_lines)

    patient_context = f"""
Patient Profile:
- Name: {patient_data.get('name', 'Unknown')}
- Age: {patient_data.get('age', 'Unknown')}
- Sex: {patient_data.get('sex', 'Unknown')}
- Ward: {patient_data.get('ward_number', 'General')}

Vitals Trend Summary (Last 2 Days):
- Blood Glucose: Trend={glucose_trend.get('trend', 'N/A')}, Average={glucose_trend.get('average', 'N/A')} mg/dL
- Systolic BP: Trend={bp_sys_trend.get('trend', 'N/A')}, Average={bp_sys_trend.get('average', 'N/A')} mmHg
- Diastolic BP: Trend={bp_dia_trend.get('trend', 'N/A')}, Average={bp_dia_trend.get('average', 'N/A')} mmHg
- SpO2: Trend={spo2_trend.get('trend', 'N/A')}, Average={spo2_trend.get('average', 'N/A')}%

{alert_summary}
"""

    prompt = f"""You are a Peer-to-Peer Clinical Co-Pilot and Senior Medical Consultant with over 30 years of clinical experience in internal medicine, critical care, and evidence-based practice.

Your role is to assist a licensed healthcare professional in interpreting clinical data, lab reports, imaging summaries, and patient symptoms.

You must operate at an expert level with the following principles:

CLINICAL THINKING APPROACH:
- Use structured clinical reasoning (problem representation → differential diagnosis → prioritization → management plan).
- Interpret abnormal values in clinical context, not isolation.
- Identify red flags, severity markers, and urgent risks.
- Apply evidence-based guidelines (WHO, NICE, ICMR, UpToDate-style reasoning).

OUTPUT FORMAT (STRICT):

1. **CLINICAL SUMMARY**
- Brief synthesis of patient condition (1–3 lines)

2. **KEY ABNORMAL FINDINGS**
- Highlight important abnormal labs/vitals with interpretation

3. **DIFFERENTIAL DIAGNOSIS (Ranked)**
- Most likely → Less likely
- Provide reasoning for each

4. **CLINICAL INTERPRETATION**
- Pathophysiology-based explanation
- Correlate symptoms + labs

5. **MANAGEMENT PLAN (For Physician Consideration Only)**
- Suggested investigations
- Treatment approach (drug classes + standard dosage ranges, NOT exact prescriptions)
- Supportive care
- Monitoring parameters

6. **RED FLAGS / ESCALATION CRITERIA**
- What requires immediate attention

7. **FOLLOW-UP STRATEGY**
- What to reassess and when

RULES:
- Do NOT act as a primary decision-maker.
- Do NOT give direct prescriptions.
- Suggest only standard dosage ranges where appropriate.
- Always maintain a professional peer-to-peer tone.
- Be concise but clinically dense.

MANDATORY DISCLAIMER:
"This is a clinical suggestion based on standard protocols. Please exercise your own medical judgement before prescribing."

Here is the current patient data to analyze:
{patient_context}
"""

    # Try each model
    for model_name in _MODEL_FALLBACK_CHAIN:
        url = f"{GEMINI_BASE_URL}/{model_name}:generateContent?key={api_key}"
        try:
            response = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.4,
                        "maxOutputTokens": 2048,
                    }
                },
                timeout=30,
            )
            if response.status_code == 429:
                continue
            if response.status_code != 200:
                continue
            
            data = response.json()
            parts = data['candidates'][0]['content'].get('parts', [])
            all_text = ''.join(p.get('text', '') for p in parts)
            if all_text:
                return all_text
                
        except Exception as e:
            print(f"[GEMINI] Consult failed for model {model_name}: {e}")
            continue
            
    print("[GEMINI] All models exhausted for Clinical Consult. Using Fallback Engine.")
    from backend.fallback_monitoring_engine import generate_fallback_monitoring_text
    return generate_fallback_monitoring_text(patient_data, trends, alerts)


def get_gemini_response(prompt: str) -> Optional[str]:
    """
    Generic helper to get a text response from Gemini.
    Used for inference, reasoning, and non-structured tasks.
    """
    api_key = os.environ.get('GEMINI_API_KEY', '')
    if not api_key:
        return None

    for model_name in _MODEL_FALLBACK_CHAIN:
        url = f"{GEMINI_BASE_URL}/{model_name}:generateContent?key={api_key}"
        try:
            response = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.3,
                        "maxOutputTokens": 500,
                    }
                },
                timeout=15,
            )
            if response.status_code != 200:
                continue

            data = response.json()
            parts = data['candidates'][0]['content'].get('parts', [])
            return ''.join(p.get('text', '') for p in parts).strip()
        except Exception:
            continue
    return None

