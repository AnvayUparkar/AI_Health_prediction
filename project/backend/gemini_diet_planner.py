"""
Gemini-Powered Medical Diet Planner
=====================================

Converts structured medical report parameters into a personalized,
AI-generated diet plan via the Google Gemini API.

Pipeline:
    report_data (dict)
        → build_diet_prompt()
        → Gemini API
        → parse_gemini_response()
        → structured DietPlanResult (dict)

Usage::

    from backend.gemini_diet_planner import generate_diet_plan_with_gemini

    report_data = {
        "Hemoglobin":  {"value": 10.2, "status": "Low",  "ref_range": "12-16"},
        "Vitamin D":   {"value": 14,   "status": "Low",  "ref_range": "30-100"},
        "Cholesterol": {"value": 240,  "status": "High", "ref_range": "0-200"},
    }

    result = generate_diet_plan_with_gemini(report_data)
    print(result["diet_plan"]["summary"])

No changes to existing diet.py / diet_plan.py routes.
"""

from __future__ import annotations

import json
import logging
import os
import re
import textwrap
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# GEMINI CLIENT SETUP
# ---------------------------------------------------------------------------

def _get_gemini_client():
    """
    Lazily initialise the Gemini client.

    Reads GEMINI_API_KEY from environment (loaded by python-dotenv in app.py
    or set directly on the OS). Raises RuntimeError if missing.
    """
    try:
        import google.generativeai as genai  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "google-generativeai package is not installed. "
            "Run: pip install google-generativeai"
        ) from exc

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Gemini API key not found. "
            "Set GEMINI_API_KEY in your .env file or environment."
        )

    genai.configure(api_key=api_key)
    return genai


# ---------------------------------------------------------------------------
# PARAMETER INTERPRETER  (adds clinical context to each lab value)
# ---------------------------------------------------------------------------

# Human-readable clinical interpretation for each parameter
_PARAM_CONTEXT: Dict[str, Dict] = {
    "Hemoglobin": {
        "low":  "Iron-deficiency anaemia or nutritional anaemia. Increases fatigue, reduces oxygen delivery.",
        "high": "Polycythaemia or dehydration. May increase blood viscosity.",
    },
    "RBC": {
        "low":  "Reduced red cell count — often accompanies anaemia.",
        "high": "Erythrocytosis — check for dehydration or chronic hypoxia.",
    },
    "WBC": {
        "high": "Leucocytosis — possible infection or inflammation.",
        "low":  "Leucopenia — immune suppression risk.",
    },
    "Platelets": {
        "low":  "Thrombocytopenia — increased bleeding risk.",
        "high": "Thrombocytosis — possible clotting risk.",
    },
    "Fasting Blood Sugar": {
        "high": "Pre-diabetes or diabetes. Poor glycaemic control damages organs long-term.",
        "low":  "Hypoglycaemia — energy crashes, brain fog.",
    },
    "Glucose": {
        "high": "Elevated blood glucose — indicates insulin resistance or diabetes risk.",
        "low":  "Low blood sugar — needs immediate dietary attention.",
    },
    "HbA1c": {
        "high": "Long-term blood sugar control is poor. Sustained dietary changes essential.",
    },
    "Total Cholesterol": {
        "high": "Hypercholesterolaemia — elevated cardiovascular risk.",
    },
    "HDL Cholesterol": {
        "low":  "Low 'good' cholesterol — increases cardiovascular disease risk.",
        "high": "Very high HDL — generally protective but monitor.",
    },
    "LDL Cholesterol": {
        "high": "Elevated 'bad' cholesterol — arterial plaque risk, heart disease.",
    },
    "Triglycerides": {
        "high": "Hypertriglyceridaemia — linked to metabolic syndrome, fatty liver, pancreatitis.",
    },
    "Vitamin D": {
        "low":  "Vitamin D deficiency — affects bone density, immunity, mood, and muscle strength.",
    },
    "Vitamin B12": {
        "low":  "B12 deficiency — causes neurological symptoms, megaloblastic anaemia, fatigue.",
    },
    "Iron": {
        "low":  "Iron deficiency — leading cause of anaemia, fatigue, and reduced immunity.",
    },
    "Ferritin": {
        "low":  "Depleted iron stores — early-stage iron deficiency before anaemia.",
    },
    "Calcium": {
        "low":  "Hypocalcaemia — affects bone health, muscle cramps, nerve function.",
        "high": "Hypercalcaemia — may indicate hyperparathyroidism or excess supplementation.",
    },
    "Uric Acid": {
        "high": "Hyperuricaemia — risk of gout, kidney stones. Requires purine restriction.",
    },
    "TSH": {
        "high": "Hypothyroidism — slows metabolism, causes weight gain, fatigue.",
        "low":  "Hyperthyroidism — accelerates metabolism, causes weight loss, palpitations.",
    },
    "T3": {
        "low":  "Low active thyroid hormone — may worsen hypothyroid symptoms.",
    },
    "T4": {
        "low":  "Low thyroxine — indicates hypothyroid state.",
    },
    "Creatinine": {
        "high": "Elevated creatinine — kidney stress. Protein and fluid intake must be managed carefully.",
    },
    "BUN": {
        "high": "High blood urea nitrogen — kidney or protein metabolism concern.",
    },
    "Urea": {
        "high": "Elevated blood urea — kidney function may be compromised.",
    },
    "SGPT": {
        "high": "Elevated ALT — liver stress or damage. Requires liver-friendly diet.",
    },
    "SGOT": {
        "high": "Elevated AST — liver or muscle stress. Reduce liver load.",
    },
    "Bilirubin Total": {
        "high": "Elevated bilirubin — possible liver or bile duct issue.",
    },
    "Alkaline Phosphatase": {
        "high": "Elevated ALP — may indicate liver disease or bone disorders.",
    },
    "Sodium": {
        "low":  "Hyponatraemia — electrolyte imbalance affecting fluid regulation.",
        "high": "Hypernatraemia — dehydration or excessive sodium intake.",
    },
    "Potassium": {
        "low":  "Hypokalaemia — muscle weakness, heart rhythm risk.",
        "high": "Hyperkalaemia — dangerous for heart rhythm, reduce high-K foods.",
    },
    "ESR": {
        "high": "Elevated ESR — systemic inflammation or infection marker.",
    },
}


def _interpret_parameter(name: str, status: str) -> str:
    """Return a clinical one-liner for the given parameter + status combo.

    Supports fuzzy prefix matching so long lab names like
    'Vitamin B12 / Cyanocobalamin' or 'Vitamin D 25 Hydroxy' still resolve
    to their canonical _PARAM_CONTEXT keys.
    """
    # 1. Exact match
    ctx = _PARAM_CONTEXT.get(name)

    # 2. Fuzzy match: find the longest key the incoming name starts with
    if ctx is None:
        name_lower = name.lower()
        best_key = None
        best_len = 0
        for key in _PARAM_CONTEXT:
            key_lower = key.lower()
            if name_lower.startswith(key_lower) and len(key_lower) > best_len:
                best_key = key
                best_len = len(key_lower)
        if best_key:
            ctx = _PARAM_CONTEXT[best_key]
            logger.debug("PARSER | Fuzzy-matched '%s' to '%s'", name, best_key)
        else:
            logger.warning("PARSER | No context found for parameter: '%s'", name)
            ctx = {}

    status_lower = status.lower()
    return (
        ctx.get(status_lower)
        or ctx.get("high" if "high" in status_lower else "low")
        or f"{name} is {status} — requires dietary attention."
    )


# ---------------------------------------------------------------------------
# PROMPT BUILDER
# ---------------------------------------------------------------------------

def build_diet_prompt(
    report_data: Dict[str, Dict],
    *,
    diet_preference: str = "balanced",
    non_veg_preferences: List[str] = None,
    allergies: List[str] = None,
    cuisine_preference: str = "Indian",
    extra_context: str = "",
) -> str:
    """
    Convert structured medical report data into a high-quality Gemini prompt.

    Parameters
    ----------
    report_data : dict
        Keys = parameter names. Values = dicts with at least 'value' and
        'status'. Optional keys: 'ref_range', 'unit'.
    diet_preference : str
        e.g. "vegetarian", "non-vegetarian", "vegan", "balanced"
    cuisine_preference : str
        e.g. "Indian", "Mediterranean", "any"
    extra_context : str
        Any additional user context (age, weight, existing conditions).

    Returns
    -------
    str
        A complete, prompt-engineered string ready to send to Gemini.
    """
    # ---- Section 1: Role assignment ----
    role_block = textwrap.dedent("""\
        You are a Senior Doctor, Senior Clinical Diet Planner, Senior Nutrition Specialist,
        and Medical Diet Consultant with more than 30 years of clinical
        experience in:
          • Interpreting pathology and blood test reports
          • Creating personalised diet plans based on blood markers, deficiencies,
            cholesterol profiles, sugar levels, liver/kidney indicators, hormonal
            markers, and preventive health nutrition
          • Indian and South-Asian clinical nutrition
          • Functional medicine and integrative dietary therapy
          • Safe, realistic, and affordable dietary guidance

        You always produce evidence-based, practical, and culturally relevant
        recommendations. You never give generic advice — every recommendation
        is based on the specific lab values provided.
    """)

    # ---- Section 2: Patient report summary ----
    abnormal: List[str] = []
    normal:   List[str] = []

    for param_name, info in report_data.items():
        value  = info.get("value", "N/A")
        status = info.get("status", "Unknown")
        unit   = info.get("unit", "")
        ref    = info.get("ref_range", "")
        interp = _interpret_parameter(param_name, status)

        line = f"  • {param_name}: {value} {unit} — Status: {status}"
        if ref:
            line += f" (Ref: {ref})"
        line += f"\n    Clinical note: {interp}"

        if status.lower() in ("high", "low", "abnormal", "critical", "borderline"):
            abnormal.append(line)
        else:
            normal.append(line)

    report_section = "PATIENT BLOOD TEST REPORT:\n\n"
    if abnormal:
        report_section += "ABNORMAL / IMPORTANT PARAMETERS:\n"
        report_section += "\n".join(abnormal) + "\n\n"
    if normal:
        report_section += "NORMAL PARAMETERS (for context):\n"
        report_section += "\n".join(normal) + "\n"

    # ---- Section 3: Diet preferences ----
    pref_block = f"\nDiet preference: {diet_preference}\n"
    if diet_preference in ["non_veg", "both", "non-vegetarian"] and non_veg_preferences:
        pref_block += f"Non-Veg Preferences: {', '.join(non_veg_preferences)}\n"
    
    if allergies:
        pref_block += f"CRITICAL - ALLERGIES (STRICTLY AVOID): {', '.join(allergies)}\n"
        
    pref_block += f"Cuisine preference: {cuisine_preference}\n"
    if extra_context:
        pref_block += f"Additional context: {extra_context}\n"

    # ---- Section 4: Task instruction ----
    task_block = textwrap.dedent("""
        YOUR TASK:

        Based ONLY on the abnormal/important parameters above, generate a
        comprehensive, personalised diet plan. Follow these steps:

        STEP 1 — ANALYSE THE REPORT
        Identify the key health issues: deficiencies, metabolic disorders,
        organ stress, hormonal imbalances, etc. Be specific about which
        parameter is driving which concern.

        STEP 2 — BUILD THE DIET PLAN
        Create a practical, culturally relevant plan that:
          • Directly addresses each detected abnormality
          • Is realistic for daily Indian/home cooking
          • Does NOT contradict any other condition (e.g., if both diabetes
            and kidney stress are present, balance protein restriction with
            glycaemic control)
          • Prioritises whole foods over supplements where possible
          • Includes specific food items, not vague categories
          • STICK TO THE SAFETY WARNING: Always verify AI recommendations with a clinical professional.
          • ABSOLUTELY NO ingredients mentioned in the ALLERGIES list above.

        STEP 3 — PROVIDE REASONING
        Briefly explain WHY each major food recommendation is made, linking
        it back to the specific lab value.

        IMPORTANT CONSTRAINTS:
          • No contradictory advice across conditions
          • No extreme diets or unsafe restrictions
          • Flag any values that require urgent medical review
          • Kidney-safe if creatinine/urea elevated
          • Liver-safe if SGPT/SGOT elevated
          • Low-purine if uric acid elevated
          • Low-GI if glucose/HbA1c elevated
          • Low-sodium if sodium elevated or hypertension suspected
    """)

    # ---- Section 5: Output format instruction ----
    format_block = textwrap.dedent("""
        OUTPUT FORMAT — VERY IMPORTANT:

        Respond with ONLY a valid JSON object. No markdown, no explanation
        outside the JSON. Use this exact schema:

        {
          "issues_detected": [
            "Brief description of each health concern found in the report"
          ],
          "recommended_foods": [
            "Specific foods with brief reasoning, e.g. 'Spinach & methi — high iron for anaemia'"
          ],
          "foods_to_avoid": [
            "Specific foods/categories with brief reason"
          ],
          "meal_plan": {
            "breakfast": ["option1", "option2", "option3"],
            "mid_morning": ["light snack option"],
            "lunch": ["option1", "option2"],
            "evening_snack": ["option"],
            "dinner": ["option1", "option2"]
          },
          "hydration_tips": [
            "Specific hydration advice based on the report values"
          ],
          "lifestyle_tips": [
            "Practical lifestyle habits that complement the diet"
          ],
          "clinical_protocol": [
            "High-level clinical strategy (e.g., 'Metabolic optimization', 'Renal protection')"
          ],
          "synergy_pairing": [
            "Biochemical synergy pairs (e.g., 'Vitamin C + Iron for 3x absorption')"
          ],
          "conditions_profile": [
            "Clinical names of detected conditions"
          ],
          "status": "Overall health summary/title for the protocol",
          "parameter_reasoning": {
            "ParameterName": "Why specific foods were recommended for this value"
          },
          "urgent_flags": [
            "Any values that need IMMEDIATE medical attention (empty list if none)"
          ],
          "summary": "2-3 sentence overall summary of the diet approach and expected benefits.",
          "safety_note": "Professional wellness disclaimer in 1 sentence."
        }

        Be specific. Be practical. Be medically accurate.
        Assume the patient is Indian, middle-class, home-cooking.
        Do NOT hallucinate values — only use the data provided.
    """)

    # ---- Assemble full prompt ----
    full_prompt = "\n".join([
        role_block,
        "=" * 70,
        report_section,
        pref_block,
        "=" * 70,
        task_block,
        "=" * 70,
        format_block,
    ])

    return full_prompt


# ---------------------------------------------------------------------------
# GEMINI API CALLER
# ---------------------------------------------------------------------------

# Ordered list of fallback models to try when a model hits quota/rate-limit
# Using currently available models to avoid 404 errors
_MODEL_FALLBACK_CHAIN = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-flash-latest",
]


def _is_quota_error(exc: Exception) -> bool:
    """Return True when *exc* is a 429 / quota-exceeded Gemini error."""
    err_str = str(exc).lower()
    return (
        "429" in err_str
        or "quota" in err_str
        or "rate limit" in err_str
        or "resource_exhausted" in err_str
        or "rate_limit" in err_str
    )


def _is_model_unavailable(exc: Exception) -> bool:
    """Return True when the model name is wrong / not accessible (404).

    These errors should cause the chain to skip to the next candidate model
    rather than aborting completely.
    """
    err_str = str(exc).lower()
    return (
        "404" in err_str
        or "not found" in err_str
        or "is not supported" in err_str
        or "listmodels" in err_str
    )


def _call_gemini_single(genai, model_name: str, prompt: str) -> str:
    """
    Attempt one model with response_mime_type first, then without.
    Raises RuntimeError on non-quota failures.
    Returns raw text on success.
    Returns None if this model should be skipped (mime rejection) — caller retries.
    """
    base_config = {
        "temperature": 0.3,
        "top_p": 0.85,
        "top_k": 40,
        "max_output_tokens": 8192,
    }
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT",        "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH",       "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]

    # Attempt A — with response_mime_type (clean JSON)
    try:
        config_a = {**base_config, "response_mime_type": "application/json"}
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=config_a,
            safety_settings=safety_settings,
        )
        response = model.generate_content(prompt)
        logger.debug("[%s] response length: %d chars", model_name, len(response.text))
        return response.text
    except Exception as exc:
        err_str = str(exc).lower()
        if _is_quota_error(exc):
            raise  # bubble up so the outer loop can try the next model
        if "mime" in err_str or "unsupported" in err_str or "invalid" in err_str or "400" in err_str:
            logger.warning("[%s] response_mime_type rejected — retrying without it.", model_name)
        else:
            raise RuntimeError(f"Gemini API error: {exc}") from exc

    # Attempt B — without response_mime_type
    try:
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=base_config,
            safety_settings=safety_settings,
        )
        response = model.generate_content(prompt)
        logger.debug("[%s] response (no mime) length: %d chars", model_name, len(response.text))
        return response.text
    except Exception as exc2:
        if _is_quota_error(exc2):
            raise  # bubble up for fallback
        raise RuntimeError(f"Gemini API error: {exc2}") from exc2


def _call_gemini(prompt: str, model_name: str = "gemini-3-flash-preview") -> str:
    """
    Send *prompt* to Gemini and return the raw text response.

    Tries *model_name* first. If it hits a quota/rate-limit (HTTP 429),
    automatically falls through the ``_MODEL_FALLBACK_CHAIN``
    (gemini-2.0-flash → gemini-2.5-flash → gemini-1.5-flash) before giving up.

    Raises RuntimeError only when ALL fallback models are exhausted or a
    non-quota error occurs.
    """
    import time

    genai = _get_gemini_client()

    # Build the model sequence: requested model first, then remaining fallbacks
    fallback_sequence = [model_name] + [
        m for m in _MODEL_FALLBACK_CHAIN if m != model_name
    ]

    last_exc: Exception = RuntimeError("No models attempted")

    for candidate in fallback_sequence:
        try:
            result = _call_gemini_single(genai, candidate, prompt)
            if candidate != model_name:
                logger.info("Used fallback model %s (primary %s hit quota)", candidate, model_name)
            return result
        except Exception as exc:
            last_exc = exc
            if _is_quota_error(exc):
                logger.warning(
                    "Model %s hit quota/rate-limit — trying next fallback. Error: %s",
                    candidate, exc
                )
                # Brief pause before trying next model to avoid hammering the API
                time.sleep(1)
                continue
            if _is_model_unavailable(exc):
                logger.warning(
                    "Model %s not available (404) — trying next fallback.",
                    candidate
                )
                continue
            
            # FAIL-FAST: If the API Key itself is invalid/blocked, trying other models won't help
            err_str = str(exc).lower()
            if "api_key_invalid" in err_str or "400" in err_str or "not found" in err_str:
                logger.error("Gemini API Key blocked or invalid. Switching to Safety Net.")
                raise RuntimeError(f"API_KEY_INVALID: {exc}")

            # Any other error — propagate immediately
            raise RuntimeError(f"Gemini API error: {exc}") from exc

    # All models exhausted
    raise RuntimeError(
        f"All Gemini models ({', '.join(fallback_sequence)}) hit quota/rate limits. "
        f"Last error: {last_exc}"
    ) from last_exc


# ---------------------------------------------------------------------------
# RESPONSE PARSER
# ---------------------------------------------------------------------------

def _repair_truncated_json(text: str) -> str:
    """
    Attempt to repair a truncated JSON string.

    When Gemini hits a token limit mid-response, the JSON is cut off.
    This function tries to close unclosed strings, arrays, and objects
    so json.loads() can succeed.
    """
    text = text.rstrip()

    # If the last char is a comma, remove it (dangling comma)
    if text.endswith(","):
        text = text[:-1]

    # Count unclosed brackets/braces
    depth_brace  = text.count("{") - text.count("}")
    depth_bracket = text.count("[") - text.count("]")

    # Check if we're inside an unclosed string (odd number of unescaped quotes)
    # Simple heuristic: count raw quote chars in last 200 chars
    tail = text[-200:]
    # Try to detect if we're mid-string by checking if last char isn't a delimiter
    if not text[-1:] in ('"', ']', '}', 'e', 'l'):
        # Likely truncated mid-string — close the string
        text += '"'

    # Close open arrays
    text += "]" * max(0, depth_bracket)
    # Close open objects
    text += "}" * max(0, depth_brace)

    return text


def parse_gemini_response(raw_text: str) -> Dict[str, Any]:
    """
    Parse the raw Gemini response into a validated Python dict.

    Handles:
    - Pure JSON response
    - JSON wrapped in markdown code fences (```json ... ```)
    - Truncated JSON (hits token limit mid-response) — repairs and retries
    - Partial JSON with missing optional fields

    Returns a dict guaranteed to have all required keys, even if empty.
    """
    # Log raw response length for debugging
    logger.debug("parse_gemini_response: raw length=%d", len(raw_text))

    text = raw_text.strip()

    # Strip markdown code fences if present
    fence_match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if fence_match:
        text = fence_match.group(1).strip()

    # Try to find JSON object/array if there's surrounding text
    if not text.startswith("{") and not text.startswith("["):
        obj_match = re.search(r"[\{\[]\s*[\d\w\s\S]+", text)
        if obj_match:
            text = obj_match.group(0)

    # Attempt 1: parse as-is
    try:
        data = json.loads(text)
        logger.debug("JSON parsed successfully on first attempt")
        if isinstance(data, dict):
            return _fill_defaults(data)
        return data
    except json.JSONDecodeError:
        pass

    # Attempt 2: repair + parse (handles truncation)
    repaired = _repair_truncated_json(text)
    try:
        data = json.loads(repaired)
        logger.info("JSON repaired and parsed successfully (response was likely truncated)")
        if isinstance(data, dict):
            return _fill_defaults(data)
        return data
    except json.JSONDecodeError as exc:
        logger.error(
            "JSON parse failed after repair. Error: %s\nRaw (first 500): %s",
            exc, raw_text[:500]
        )
        # Return a safe default so the API never crashes
        return _empty_diet_plan(
            summary="Diet plan could not be fully parsed (response truncated). Please try again."
        )


def _fill_defaults(data: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure all required keys exist in the parsed diet plan dict."""
    defaults = _empty_diet_plan()
    for key, default_val in defaults.items():
        if key not in data:
            data[key] = default_val
    return data


def _empty_diet_plan(summary: str = "") -> Dict[str, Any]:
    """Return a safe empty diet plan structure."""
    return {
        "issues_detected": [],
        "recommended_foods": [],
        "foods_to_avoid": [],
        "meal_plan": {
            "breakfast": [],
            "mid_morning": [],
            "lunch": [],
            "evening_snack": [],
            "dinner": [],
        },
        "hydration_tips": [],
        "lifestyle_tips": [],
        "clinical_protocol": [],
        "synergy_pairing": [],
        "conditions_profile": [],
        "status": "Balanced Nutrition Protocol",
        "parameter_reasoning": {},
        "urgent_flags": [],
        "summary": summary,
        "safety_note": (
            "This is a wellness and nutrition guidance plan. "
            "It is not a substitute for professional medical diagnosis or treatment. "
            "Please consult a qualified doctor or registered dietitian for severe abnormalities."
        ),
    }


# ---------------------------------------------------------------------------
# OUTPUT FORMATTER
# ---------------------------------------------------------------------------

def format_diet_output(diet_plan: Dict[str, Any], mode: str = "text") -> str:
    """
    Format the structured diet plan dict into human-readable text.

    Parameters
    ----------
    diet_plan : dict
        Output of :func:`parse_gemini_response`.
    mode : str
        "text"  — plain text (terminal / log)
        "html"  — minimal HTML for web display
        "brief" — one-paragraph summary only

    Returns
    -------
    str
        Formatted string.
    """
    if mode == "brief":
        return diet_plan.get("summary", "No summary available.")

    lines: List[str] = []

    def section(title: str, items: List[str]) -> None:
        if not items:
            return
        lines.append(f"\n{'='*60}")
        lines.append(f"  {title.upper()}")
        lines.append("="*60)
        for item in items:
            lines.append(f"  • {item}")

    def meal_section(meal_plan: Dict) -> None:
        if not any(meal_plan.values()):
            return
        lines.append(f"\n{'='*60}")
        lines.append("  MEAL PLAN")
        lines.append("="*60)
        labels = {
            "breakfast":    "Breakfast",
            "mid_morning":  "Mid-Morning Snack",
            "lunch":        "Lunch",
            "evening_snack":"Evening Snack",
            "dinner":       "Dinner",
        }
        for key, label in labels.items():
            options = meal_plan.get(key, [])
            if options:
                lines.append(f"\n  {label}:")
                for opt in options:
                    lines.append(f"    - {opt}")

    # Header
    lines.append("\n" + "="*60)
    lines.append("  AI-POWERED PERSONALISED DIET PLAN")
    lines.append("  Generated by Gemini Clinical Nutrition Engine")
    lines.append("="*60)

    # Summary
    summary = diet_plan.get("summary", "")
    if summary:
        lines.append(f"\n  {summary}")

    # Urgent flags
    flags = diet_plan.get("urgent_flags", [])
    if flags:
        lines.append(f"\n{'!'*60}")
        lines.append("  !! URGENT — SEEK MEDICAL ATTENTION FOR:")
        for f in flags:
            lines.append(f"  !! {f}")
        lines.append("!"*60)

    section("Issues Detected", diet_plan.get("issues_detected", []))
    section("Recommended Foods", diet_plan.get("recommended_foods", []))
    section("Foods to Avoid", diet_plan.get("foods_to_avoid", []))
    meal_section(diet_plan.get("meal_plan", {}))
    section("Hydration Tips", diet_plan.get("hydration_tips", []))
    section("Lifestyle Tips", diet_plan.get("lifestyle_tips", []))

    # Parameter reasoning
    reasoning = diet_plan.get("parameter_reasoning", {})
    if reasoning:
        lines.append(f"\n{'='*60}")
        lines.append("  WHY THESE RECOMMENDATIONS")
        lines.append("="*60)
        for param, reason in reasoning.items():
            lines.append(f"  [{param}]: {reason}")

    # Safety note
    note = diet_plan.get("safety_note", "")
    if note:
        lines.append(f"\n  Note: {note}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# MAIN PUBLIC API
# ---------------------------------------------------------------------------

def generate_diet_plan_with_gemini(
    report_data: Dict[str, Dict],
    *,
    diet_preference: str = "balanced",
    non_veg_preferences: List[str] = None,
    allergies: List[str] = None,
    cuisine_preference: str = "Indian",
    extra_context: str = "",
    model_name: str = "gemini-3-flash-preview",
    fallback_to_rules: bool = True,
    raw_text: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Full pipeline: report_data → Gemini prompt → API → structured diet plan.

    Parameters
    ----------
    report_data : dict
        Structured medical parameter data from ``extract_parameters()``.
        Example::

            {
                "Hemoglobin": {"value": "10.2", "status": "Low", "unit": "g/dL"},
                "HbA1c":      {"value": "7.2",  "status": "High", "unit": "%"},
            }

    diet_preference : str
        "vegetarian" | "non-vegetarian" | "vegan" | "balanced"
    cuisine_preference : str
        "Indian" | "Mediterranean" | "any"
    extra_context : str
        Free-text additional context (age, weight, existing meds, etc.)
    model_name : str
        Gemini model identifier.
    fallback_to_rules : bool
        If True and Gemini fails, fall back to the rule-based engine.

    Returns
    -------
    dict
        Keys:
        ``diet_plan``      — structured Gemini output (parsed dict)
        ``diet_plan_text`` — human-readable formatted string
        ``prompt``         — the exact prompt sent (for debugging)
        ``source``         — "gemini" | "rules_fallback" | "error"
        ``error``          — error message if any (else None)
    """
    prompt = build_diet_prompt(
        report_data,
        diet_preference=diet_preference,
        non_veg_preferences=non_veg_preferences,
        allergies=allergies,
        cuisine_preference=cuisine_preference,
        extra_context=extra_context,
    )

    source = "gemini"
    diet_plan: Dict[str, Any] = {}
    error_msg: Optional[str] = None

    try:
        raw = _call_gemini(prompt, model_name=model_name)
        diet_plan = parse_gemini_response(raw)
        logger.info(
            "Gemini diet plan generated: %d issues, %d foods",
            len(diet_plan.get("issues_detected", [])),
            len(diet_plan.get("recommended_foods", [])),
        )

    except Exception as exc:
        error_msg = str(exc)
        logger.error("Gemini diet generation failed: %s", exc)

        if fallback_to_rules:
            logger.warning("Gemini AI failed. Falling back to ADVANCED rule-based engine.")
            source = "rules_fallback"
            try:
                # Import the new advanced fallback engine
                from backend.fallback_diet_engine import fallback_diet_engine
                
                # Use the full clinical result to satisfy UI requirements
                diet_plan = fallback_diet_engine(report_data, raw_text=raw_text, context=context)
                
                # Add source notification to the summary field
                diet_plan["summary"] = (
                    "Diet plan generated using advanced rule-based clinical engine "
                    "(Gemini API fallback triggered)."
                )
                
                logger.info(
                    "Advanced fallback succeeded: %d issues, %d foods",
                    len(diet_plan.get("issues_detected", [])),
                    len(diet_plan.get("recommended_foods", [])),
                )
            except Exception as fb_exc:
                logger.error("Advanced fallback also failed: %s", fb_exc)
                source = "error"
                diet_plan = _empty_diet_plan(
                    summary="Diet plan generation failed. Please try again."
                )
        else:
            source = "error"
            diet_plan = _empty_diet_plan()

    diet_plan_text = format_diet_output(diet_plan)

    return {
        "diet_plan":      diet_plan,
        "diet_plan_text": diet_plan_text,
        "prompt":         prompt,        # for debugging / transparency
        "source":         source,
        "error":          error_msg,
    }