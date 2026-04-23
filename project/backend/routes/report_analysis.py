"""
Report Analysis API Route
==========================

Flask blueprint providing the ``POST /api/analyze-report`` endpoint.

This endpoint orchestrates the full medical-report diet recommendation pipeline:
    1. Accept file upload (image or PDF)
    2. OCR text extraction  (via ``backend.ocr_scanner``)
    3. Medical parameter parsing (via ``backend.report_parser``)
    4. Importance detection
    5. Diet recommendation  (via ``backend.report_diet_engine``)
    6. Return structured JSON response

This endpoint also supports **Manual Health Entry** by providing a ``health_data``
JSON string instead of (or in addition to) the ``report`` file.

This is a NEW endpoint that does NOT conflict with the existing
``POST /api/upload-report`` in ``diet.py``.
"""

import os
import tempfile
import logging
import json
from flask import Blueprint, request, jsonify

from backend.ocr_scanner import extract_text
from backend.report_diet_engine import (
    generate_report_diet,
    format_diet_plan_text,
)
from backend.report_parser import extract_parameters, detect_important_parameters, get_important_parameters, summarize_report, get_clinical_summary
from backend.gemini_diet_planner import generate_diet_plan_with_gemini
from backend.clinical_context_builder import build_context
from backend.nutrient_pipeline import calculate_diet_plan_confidence
from backend.fallback_diet_engine import fallback_diet_engine

logger = logging.getLogger(__name__)

report_analysis_bp = Blueprint("report_analysis", __name__)

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "bmp", "tiff", "tif", "webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def _allowed_file(filename: str) -> bool:
    """Check if the file extension is supported."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in ALLOWED_EXTENSIONS


@report_analysis_bp.route("/analyze-report", methods=["POST"])
def analyze_report():
    """
    POST /api/analyze-report

    Accepts a multipart/form-data request with a ``report`` file field.

    Returns JSON::

        {
            "success": true,
            "extracted_text": "...",
            "all_parameters": { ... },
            "important_parameters": { ... },
            "report_summary": "...",
            "diet_recommendation": { ... },
            "diet_plan_text": "...",
            "mode": "file" | "manual"
        }
    """
    # ----------------------------------------------------------------
    # 1. Check for manual data vs file upload
    # ----------------------------------------------------------------
    health_data = None
    health_data_str = request.form.get("health_data") or request.form.get("healthData")
    if health_data_str:
        try:
            health_data = json.loads(health_data_str)
        except Exception:
            health_data = None

    if "report" not in request.files:
        if health_data:
            # Manual Mode: Proceed without OCR
            return _handle_manual_analysis(health_data)
        return jsonify({"success": False, "error": 'No file or health data provided.'}), 400

    file = request.files["report"]
    filename = getattr(file, "filename", "") or ""

    if filename == "":
        return jsonify({"success": False, "error": "Empty filename."}), 400

    if not _allowed_file(filename):
        return jsonify({
            "success": False,
            "error": f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        }), 400

    # Check size
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > MAX_FILE_SIZE:
        return jsonify({"success": False, "error": "File too large (max 10 MB)."}), 400

    # ----------------------------------------------------------------
    # 2. Save to temp file
    # ----------------------------------------------------------------
    tmpdir = tempfile.gettempdir()
    save_path = os.path.join(str(tmpdir), str(filename))
    try:
        file.save(save_path)
    except Exception as exc:
        logger.error("Failed to save uploaded file: %s", exc)
        return jsonify({"success": False, "error": "Failed to save uploaded file."}), 500

    # ----------------------------------------------------------------
    # 3. OCR text extraction
    # ----------------------------------------------------------------
    try:
        extracted_text = extract_text(save_path, medical_report_mode=True)
    except Exception as exc:
        logger.error("OCR extraction failed: %s", exc)
        return jsonify({
            "success": False,
            "error": f"OCR extraction failed: {str(exc)}",
        }), 500
    finally:
        # Clean up temp file (best-effort)
        try:
            os.remove(save_path)
        except OSError:
            pass

    if not extracted_text.strip():
        return jsonify({
            "success": False,
            "error": (
                "No text could be extracted from the report. "
                "Please ensure the image is clear, well-lit, and contains "
                "readable text. Supported formats: JPG, PNG, PDF."
            ),
        }), 422

    # ----------------------------------------------------------------
    # 4. Parse medical parameters
    # ----------------------------------------------------------------
    all_parameters = extract_parameters(extracted_text)

    # ----------------------------------------------------------------
    # 5. Detect important / abnormal parameters
    # ----------------------------------------------------------------
    detect_important_parameters(all_parameters)
    important_params = get_important_parameters(all_parameters)

    # 6. [NEW] Clinical Context Pipeline
    # ----------------------------------------------------------------
    # A. Build Clinical Summary (Standards Step 1)
    clinical_analysis = get_clinical_summary(all_parameters)
    
    # B. Build Scoring Context (Standards Step 2)
    clinical_context = build_context(clinical_analysis, health_data=health_data)
    
    # C. Generate Diet (Gemini Primary, Advanced Engine Fallback)
    diet_preference  = request.form.get("diet_preference") or (health_data.get("dietaryPreference") if health_data else "balanced")
    non_veg_prefs    = request.form.getlist("non_veg_preferences") or (health_data.get("nonVegPreferences") if health_data else [])
    allergies        = request.form.getlist("allergies") or (health_data.get("allergies") if health_data else [])
    cuisine_pref     = request.form.get("cuisine_preference", "Indian")
    extra_context    = request.form.get("extra_context", "")

    # If we have health data, enrich the context for Gemini
    if health_data:
        manual_context = (
            f"Patient Profile: Age {health_data.get('age')}, Weight {health_data.get('weight')}kg, "
            f"Height {health_data.get('height')}cm, Activity: {health_data.get('activityLevel')}. "
            f"Conditions: {health_data.get('healthConditions')}."
        )
        extra_context = f"{manual_context}\n{extra_context}"

    gemini_result = generate_diet_plan_with_gemini(
        all_parameters,
        diet_preference=diet_preference,
        non_veg_preferences=non_veg_prefs,
        allergies=allergies,
        cuisine_preference=cuisine_pref,
        extra_context=extra_context,
        fallback_to_rules=True,
        raw_text=extracted_text,
        context=clinical_context  # Puts context in the fallback engine
    )

    diet_recommendation = gemini_result["diet_plan"]
    diet_text           = gemini_result["diet_plan_text"]
    diet_source         = gemini_result["source"]
    diet_error          = gemini_result["error"]

    # ----------------------------------------------------------------
    # 7. Human-readable report summary
    # ----------------------------------------------------------------
    report_summary = summarize_report(all_parameters, health_data=health_data)

    # ----------------------------------------------------------------
    # 8. Build response
    # ----------------------------------------------------------------
    response = {
        "success": True,
        "extracted_text":     extracted_text[:5000],
        "all_parameters":     all_parameters,
        "important_parameters": important_params,
        "report_summary":     report_summary,
        "diet_recommendation": diet_recommendation,
        "diet_plan_text":     diet_text,
        "diet_source":        diet_source,   # tells frontend which engine was used
        "meta":               calculate_diet_plan_confidence(diet_recommendation["meal_plan"]),
    }
    if diet_error:
        response["diet_warning"] = diet_error

    response["mode"] = "file"

    logger.info(
        "Report analyzed: %d parameters found, %d important",
        len(all_parameters),
        len(important_params),
    )

    return jsonify(response), 200


def _handle_manual_analysis(health_data):
    """Internal helper to process manual health entry using the Gemini engine."""
    diet_preference = health_data.get("dietaryPreference", "balanced")
    
    # Calculate BMI for extra context
    bmi_str = ""
    try:
        w = float(health_data.get('weight', 0))
        h = float(health_data.get('height', 0)) / 100
        if h > 0:
            bmi = w / (h * h)
            bmi_str = f"BMI: {bmi:.1f}. "
    except:
        pass

    manual_context = (
        f"{bmi_str}Patient Profile: Age {health_data.get('age')}, Weight {health_data.get('weight')}kg, "
        f"Height {health_data.get('height')}cm, Activity: {health_data.get('activityLevel')}. "
        f"Pathology Context: {health_data.get('healthConditions')}."
    )

    diet_pref       = health_data.get("dietaryPreference", health_data.get("diet_preference", "balanced"))
    non_veg_prefs   = health_data.get("nonVegPreferences", health_data.get("non_veg_preferences", []))
    allergies       = health_data.get("allergies", [])

    gemini_result = generate_diet_plan_with_gemini(
        {}, # No lab parameters
        diet_preference=diet_pref,
        non_veg_preferences=non_veg_prefs,
        allergies=allergies,
        extra_context=manual_context,
        fallback_to_rules=True,
        raw_text=health_data.get('healthConditions', '')
    )

    response = {
        "success": True,
        "extracted_text": "No report uploaded (Manual Entry mode).",
        "all_parameters": {},
        "important_parameters": {},
        "report_summary": f"Manual Profile: {health_data.get('age')}yr old, {health_data.get('weight')}kg.",
        "diet_recommendation": gemini_result["diet_plan"],
        "diet_plan_text": gemini_result["diet_plan_text"],
        "diet_source": gemini_result["source"],
        "meta": calculate_diet_plan_confidence(gemini_result["diet_plan"]["meal_plan"]),
        "mode": "manual"
    }
    if gemini_result["error"]:
        response["diet_warning"] = gemini_result["error"]

    return jsonify(response), 200
