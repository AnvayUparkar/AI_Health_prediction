"""
Health Connect Sync Route
=========================

Accepts 7-day health metrics from Android Health Connect (on-device data store)
and processes them through the same Gemini analysis pipeline used by Google Fit.

This serves as a FALLBACK when the Google Fit REST API is unavailable:
  - No internet during initial OAuth handshake
  - Google Fit token expired or user revoked access
  - User only has Health Connect data (Samsung Health, Fitbit, etc.)

Data shape mirrors the Google Fit pipeline exactly so the frontend is agnostic
to the data source. The `data_source` column distinguishes provenance.
"""

from flask import Blueprint, request, jsonify
import logging
import json
from datetime import datetime, timedelta
from flask_jwt_extended import jwt_required, get_jwt_identity

from backend.models import db, HealthAnalysis
from backend.db_service import DBService
from backend.health_analyzer import analyze_weekly_data, generate_fallback_analysis

logger = logging.getLogger(__name__)

health_connect_sync_bp = Blueprint('health_connect_sync', __name__)


def _validate_day(day: dict, index: int) -> tuple:
    """Validate a single day record. Returns (cleaned_dict, error_string)."""
    date_str = day.get('date')
    if not date_str:
        return None, f"day[{index}]: missing 'date' field"
    
    # Coerce types defensively — mobile clients send whatever they want
    try:
        steps = int(day.get('steps', 0) or 0)
    except (ValueError, TypeError):
        steps = 0

    try:
        hr = float(day.get('avg_heart_rate', 70.0) or 70.0)
        if hr < 30 or hr > 220:
            hr = 70.0  # implausible — use safe default
    except (ValueError, TypeError):
        hr = 70.0

    try:
        sleep = float(day.get('sleep_hours', 7.0) or 7.0)
        if sleep < 0 or sleep > 24:
            sleep = 7.0
    except (ValueError, TypeError):
        sleep = 7.0

    return {
        "date": date_str,
        "steps": steps,
        "avg_heart_rate": hr,
        "sleep_hours": sleep
    }, None


@health_connect_sync_bp.route('/health-connect-sync', methods=['POST'])
@jwt_required()
def sync_health_connect():
    """
    POST /api/health-connect-sync
    
    Accepts:
    {
        "daily_metrics": [
            { "date": "2026-04-06", "steps": 4500, "avg_heart_rate": 72.3, "sleep_hours": 6.5 },
            ...
        ],
        "timezone_offset": -330    // optional, minutes from UTC
    }
    
    This endpoint is called by the Android HealthDataSyncWorker when Health Connect
    data is available. It mirrors the Google Fit sync pipeline exactly.
    """
    user_identity = get_jwt_identity()
    user_id = user_identity.get('id') if isinstance(user_identity, dict) else user_identity

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "error": "Request body must be valid JSON"}), 400

    raw_metrics = data.get('daily_metrics')
    if not raw_metrics or not isinstance(raw_metrics, list):
        return jsonify({
            "success": False,
            "error": "Missing or invalid 'daily_metrics' array. Expected 1-7 day records."
        }), 400

    if len(raw_metrics) > 14:
        return jsonify({
            "success": False,
            "error": f"Too many records ({len(raw_metrics)}). Maximum 14 days allowed."
        }), 400

    # ── Validate each day record ──────────────────────────────────────────
    daily_metrics = []
    for i, day in enumerate(raw_metrics):
        cleaned, err = _validate_day(day, i)
        if err:
            logger.warning("[HealthConnect] Skipping bad record: %s", err)
            continue
        daily_metrics.append(cleaned)

    if not daily_metrics:
        return jsonify({
            "success": False,
            "error": "No valid day records found after validation."
        }), 400

    logger.info("[HealthConnect] Received %d valid day(s) from user %s", len(daily_metrics), user_id)

    try:
        # ── Batch analyze with Gemini (same pipeline as Google Fit) ────────
        weekly_analysis = analyze_weekly_data(daily_metrics)

        saved_records = []
        for day_data in daily_metrics:
            date_str = day_data['date']

            # Match analysis result to this date
            analysis = next((a for a in weekly_analysis if a.get('date') == date_str), None)
            if not analysis:
                # Safety net: generate rule-based analysis if Gemini didn't return this date
                analysis = generate_fallback_analysis(day_data)

            # ── Upsert: find existing record for this date ────────────────
            day_start = datetime.strptime(date_str, '%Y-%m-%d')
            day_end = day_start + timedelta(days=1)

            existing = HealthAnalysis.query.filter(
                HealthAnalysis.user_id == user_id,
                HealthAnalysis.created_at >= day_start,
                HealthAnalysis.created_at < day_end
            ).order_by(HealthAnalysis.created_at.desc()).first()

            if existing:
                # Only overwrite if Health Connect has MORE steps than existing record
                # (prevents downgrading a good Google Fit sync with a partial HC read)
                if day_data['steps'] >= (existing.steps or 0):
                    existing.health_score = analysis.get('health_score', 0)
                    existing.risk_level = analysis.get('risk_level', 'Low')
                    existing.health_status = analysis.get('health_status', 'N/A')
                    existing.steps = day_data['steps']
                    existing.avg_heart_rate = day_data['avg_heart_rate']
                    existing.sleep_hours = day_data['sleep_hours']
                    existing.diet_plan = json.dumps(analysis.get('diet_plan', []))
                    existing.recommendations = json.dumps(analysis.get('recommendations', []))
                    existing.data_source = 'health_connect'
                    
                    # MongoDB Sync Integration
                    DBService.sync_health_analysis_to_mongo(existing)
                    
                    saved_records.append(existing.to_dict())
                    logger.info("[HealthConnect] Updated %s (steps: %d)", date_str, day_data['steps'])
                else:
                    logger.info("[HealthConnect] Kept existing %s (existing steps %d >= HC %d)",
                                date_str, existing.steps or 0, day_data['steps'])
                    saved_records.append(existing.to_dict())
            else:
                # Create new record
                new_record = HealthAnalysis(
                    user_id=user_id,
                    health_score=analysis.get('health_score', 0),
                    risk_level=analysis.get('risk_level', 'Low'),
                    health_status=analysis.get('health_status', 'N/A'),
                    steps=day_data['steps'],
                    avg_heart_rate=day_data['avg_heart_rate'],
                    sleep_hours=day_data['sleep_hours'],
                    diet_plan=json.dumps(analysis.get('diet_plan', [])),
                    recommendations=json.dumps(analysis.get('recommendations', [])),
                    data_source='health_connect',
                    created_at=day_start + timedelta(hours=12)
                )
                db.session.add(new_record)
                db.session.flush()
                
                # MongoDB Sync Integration
                DBService.sync_health_analysis_to_mongo(new_record)
                
                saved_records.append(new_record.to_dict())
                logger.info("[HealthConnect] Created %s (steps: %d)", date_str, day_data['steps'])

        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Health Connect: synced {len(saved_records)} day(s)",
            "source": "health_connect",
            "data": saved_records[-1] if saved_records else None
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.exception("[HealthConnect] Sync error: %s", str(e))
        return jsonify({"success": False, "error": str(e)}), 500
