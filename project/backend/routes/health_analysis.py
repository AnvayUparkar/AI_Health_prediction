from flask import Blueprint, request, jsonify
import logging
import json
from datetime import datetime, timedelta
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.health_analyzer import analyze_health_data
from backend.models import db, HealthAnalysis
from backend.db_service import DBService
import os

logger = logging.getLogger(__name__)

health_analysis_bp = Blueprint("health_analysis", __name__)

@health_analysis_bp.route("/health-analysis", methods=["POST"])
@jwt_required()
def health_analysis():
    print("[DEBUG] Entered POST /health-analysis")
    """
    POST /api/health-analysis
    Required: JWT Auth
    Body: { steps, avg_heart_rate, sleep_hours }
    
    Calls Gemini, saves to database, and returns results.
    """
    identity = get_jwt_identity()
    user_id = identity.get('id') if isinstance(identity, dict) else identity
    
    try:
        data = request.get_json()
        
        steps = data.get("steps")
        avg_heart_rate = data.get("avg_heart_rate")
        sleep_hours = data.get("sleep_hours")
        
        if steps is None or avg_heart_rate is None or sleep_hours is None:
            return jsonify({
                "success": False,
                "error": "Missing required fields: steps, avg_heart_rate, sleep_hours"
            }), 400
            
        # 1. Analyze with Gemini
        analysis_result = analyze_health_data(
            steps=int(steps),
            avg_heart_rate=float(avg_heart_rate),
            sleep_hours=float(sleep_hours)
        )
        
        # 2. Save to Database
        new_analysis = HealthAnalysis(
            user_id=user_id,
            health_score=analysis_result.get("health_score"),
            risk_level=analysis_result.get("risk_level"),
            health_status=analysis_result.get("health_status"),
            steps=int(steps),
            avg_heart_rate=float(avg_heart_rate),
            sleep_hours=float(sleep_hours),
            diet_plan=json.dumps(analysis_result.get("diet_plan", [])),
            recommendations=json.dumps(analysis_result.get("recommendations", []))
        )
        
        db.session.add(new_analysis)
        db.session.commit()
        
        # MongoDB Sync Integration
        DBService.sync_health_analysis_to_mongo(new_analysis)
        
        return jsonify({
            "success": True,
            "data": analysis_result
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error("Health analysis POST error: %s", str(e))
        return jsonify({
            "success": False,
            "error": f"An error occurred: {str(e)}"
        }), 500

@health_analysis_bp.route("/health-analysis", methods=["GET"])
@jwt_required()
def get_latest_health_analysis():
    """
    GET /api/health-analysis
    Required: JWT Auth
    
    Returns the latest health analysis for the current user.
    """
    identity = get_jwt_identity()
    current_user = get_jwt_identity()
    user_id = identity.get('id') if isinstance(identity, dict) else identity
    
    try:
        # MongoDB Read Integration
        mongo_data = DBService.get_latest_health_analysis(user_id)
        if mongo_data and isinstance(mongo_data, dict):
            return jsonify({"success": True, "data": mongo_data}), 200

        # Original SQL logic
        latest = HealthAnalysis.query.filter_by(user_id=user_id).order_by(HealthAnalysis.created_at.desc()).first()
        
        if not latest:
            return jsonify({
                "success": True,
                "data": None,
                "message": "No sync data found for this user."
            }), 200
            
        return jsonify({
            "success": True,
            "data": latest.to_dict()
        }), 200

    except Exception as e:
        logger.error("Health analysis GET error: %s", str(e))
        return jsonify({
            "success": False,
            "error": f"Failed to retrieve data: {str(e)}"
        }), 500

@health_analysis_bp.route("/health-report", methods=["GET"])
@jwt_required()
def get_health_report():
    """
    GET /api/health-report
    Required: JWT Auth
    
    Returns the last 7 health analysis records for the current user.
    """
    identity = get_jwt_identity()
    user_id = identity.get('id') if isinstance(identity, dict) else identity
    
    try:
        # 1. Fetch records from the last 14 days to ensures we have enough to choose from
        seven_days_ago = datetime.utcnow() - timedelta(days=14)
        
        # MongoDB Integration: Selective read based on configuration
        if os.environ.get('READ_FROM') == 'mongo':
            reports = DBService.get_health_report(user_id, days=14)
        else:
            reports = HealthAnalysis.query.filter(
                HealthAnalysis.user_id == user_id,
                HealthAnalysis.created_at >= seven_days_ago
            ).order_by(HealthAnalysis.created_at.desc()).all()
        
        # 2. Extract UNIQUE days to prevent the "Empty Bars" bug
        unique_days = {}
        for r in reports:
            # Handle both dict (Mongo) and Model (SQL)
            is_dict = isinstance(r, dict)
            r_dict = r if is_dict else r.to_dict()
            created_at = r['created_at'] if is_dict else r.created_at
            
            # We use the DATE part as the key to ensure only 1 record per day is shown
            if isinstance(created_at, str):
                date_key = created_at[:10]
            else:
                date_key = created_at.strftime('%Y-%m-%d')
                
            if date_key not in unique_days:
                unique_days[date_key] = r_dict
        
        # 3. Get the 7 most recent unique days and sort chronologically (Oldest to Newest)
        sorted_keys = sorted(unique_days.keys(), reverse=True)[:7]
        data = [unique_days[k] for k in sorted(sorted_keys)]
            
        return jsonify({
            "success": True,
            "count": len(data),
            "data": data
        }), 200

    except Exception as e:
        logger.error("Health report GET error: %s", str(e))
        return jsonify({
            "success": False,
            "error": f"Failed to generate report: {str(e)}"
        }), 500
