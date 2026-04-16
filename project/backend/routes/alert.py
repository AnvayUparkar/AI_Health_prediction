from flask import Blueprint, request, jsonify
import json
from backend.alert_engine import generate_alert
from backend.db_service import DBService
from flask_jwt_extended import jwt_required, get_jwt_identity
import traceback
from backend.extensions import socketio

from backend.services.appointment_service import AppointmentService
from backend.models import User

alert_bp = Blueprint('alert', __name__)

@alert_bp.route('/alert/data', methods=['POST', 'OPTIONS'])
def process_alert_data():
    """
    Endpoint for receiving monitoring data and generating alerts.
    Ready for OpenCV input.
    """
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON data"}), 400
            
        # 1. Generate alert via engine
        alert_result = generate_alert(data)
        
        # 2. Add patient/room info to the result for storage
        alert_result['patient_id'] = data.get('patient_id', 'UNKNOWN')
        alert_result['room_number'] = data.get('room_number', 'N/A')
        
        # 3. Store in database
        # We only store if there's an active alert or warning, or we can store everything
        # Requirement says "Store alert", so we definitely store when alert=True
        # For a live system, we might store everything for historical trends, 
        # but let's stick to storing alerts specifically as requested.
        new_alert = DBService.create_alert(alert_result)
        
        # 4. Return the alert result
        response_data = new_alert.to_dict() if hasattr(new_alert, 'to_dict') else alert_result
        
        # 5. Emit real-time socket event if it's an alert
        if response_data.get('alert'):
            socketio.emit('new_alert', response_data)
            
        return jsonify(response_data), 201
        
    except Exception as e:
        print(f"[ERROR] Alert processing failed: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@alert_bp.route('/alerts', methods=['GET', 'OPTIONS'])
def get_alerts():
    """Fetch alerts with optional filters."""
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        filters = {
            "patient_id": request.args.get('patient_id'),
            "status": request.args.get('status'),
            "alert": request.args.get('alert', type=lambda v: v.lower() == 'true' if v else None)
        }
        
        # Remove None values
        filters = {k: v for k, v in filters.items() if v is not None}
        
        alerts = DBService.list_alerts(filters)
        
        # Convert to dict
        if isinstance(alerts, list):
            results = [a.to_dict() if hasattr(a, 'to_dict') else a for a in alerts]
        else:
            results = []
            
        return jsonify(results), 200
        
    except Exception as e:
        print(f"[ERROR] Fetching alerts failed: {e}")
        return jsonify({"error": str(e)}), 500

@alert_bp.route('/alerts/<alert_id>', methods=['PATCH', 'OPTIONS'])
def update_alert(alert_id):
    """Update alert acknowledged or resolved status."""
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON data"}), 400
            
        updates = {}
        if 'acknowledged' in data: updates['acknowledged'] = bool(data['acknowledged'])
        if 'resolved' in data: updates['resolved'] = bool(data['resolved'])
        
        if not updates:
            return jsonify({"error": "No valid fields to update"}), 400
            
        alert = DBService.update_alert_status(alert_id, updates)
        
        if not alert:
            return jsonify({"error": "Alert not found"}), 404
        
        response_data = alert.to_dict() if hasattr(alert, 'to_dict') else alert
        
        # Broadcast update to all connected clients for real-time sync
        socketio.emit('alert_updated', {
            'id': alert_id,
            **updates,
            'alert': response_data
        })
            
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"[ERROR] Updating alert failed: {e}")
        return jsonify({"error": str(e)}), 500
@alert_bp.route('/alert/sos', methods=['POST', 'OPTIONS'])
@jwt_required(optional=True)
def trigger_sos():
    """
    Endpoint for triggering a manual SOS emergency alert.
    """
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        user_identity = get_jwt_identity()
        data = request.get_json() or {}
        
        # Determine patient name/ID
        patient_id = data.get('patient_id')
        if not patient_id and user_identity:
            patient_id = user_identity
        if not patient_id:
            patient_id = "EMERGENCY_USER"
            
        lat = data.get('latitude')
        lon = data.get('longitude')
        
        if lat is None or lon is None:
            return jsonify({"error": "Location access required for SOS"}), 400
        
        try:
            lat = float(lat)
            lon = float(lon)
        except ValueError:
            return jsonify({"error": "Invalid location coordinates"}), 400
        
        location_type = 'REMOTE'
        room_desc = 'REMOTE_LOCATION'
        nearest_hosp = None
        dist_km = None
        notified_docs = []
        
        # 1. Remote Trace - Calculate nearest hospital dynamically via DB and Haversine
        hosp_data = AppointmentService.calculate_nearest_hospital(lat, lon)
        if hosp_data:
            nearest_hosp = hosp_data['name']
            dist_km = hosp_data['distance']
            room_desc = f"Near {nearest_hosp} ({dist_km} km)"
            
            # Notify all doctors and nurses at this dynamically selected hospital
            hosp_staff = DBService.get_medical_staff_by_hospital(nearest_hosp)
            notified_docs = [d['id'] if isinstance(d, dict) else d.id for d in hosp_staff]
            
            # ── Debug Logging ──
            print(f"\n{'='*60}")
            print(f"[SOS ROUTING] Patient Location: Lat={lat}, Lon={lon}")
            print(f"[SOS ROUTING] Nearest Hospital: {nearest_hosp} ({dist_km} km)")
            print(f"[SOS DISPATCH] Found {len(hosp_staff)} staff at '{nearest_hosp}'")
            for s in hosp_staff:
                s_name = s.get('name') if isinstance(s, dict) else s.name
                s_role = s.get('role') if isinstance(s, dict) else s.role
                s_id = s.get('id') if isinstance(s, dict) else s.id
                print(f"  -> Will notify: {s_name} (role={s_role}, id={s_id})")
            print(f"[SOS DISPATCH] Notified IDs: {notified_docs}")
            print(f"{'='*60}\n")
        else:
            print(f"\n[SOS ROUTING] WARNING: No hospital found for Lat={lat}, Lon={lon}\n")

        alert_data = {
            "patient_id": patient_id,
            "room_number": room_desc,
            "status": "CRITICAL",
            "confidence": "100%",
            "reason": "S.O.S EMERGENCY SIGNAL",
            "detected_issues": ["Manual Intervention Required", "User Triggered SOS"],
            "recommended_action": "Immediate Medical Response Required",
            "alert": True,
            "latitude": lat,
            "longitude": lon,
            "location_type": location_type,
            "nearest_hospital": nearest_hosp,
            "distance_km": dist_km,
            "notified_doctor_ids": json.dumps(notified_docs)
        }
        
        # Store and notify
        new_alert = DBService.create_alert(alert_data)
        
        # Log to Audit
        AppointmentService.log_audit_action(
            action="SOS_TRIGGERED",
            patient_id=patient_id,
            ward_number=None,
            details={
                "location_type": location_type,
                "hospital": nearest_hosp,
                "distance": dist_km,
                "coords": [lat, lon]
            }
        )
        
        response_data = new_alert.to_dict() if hasattr(new_alert, 'to_dict') else alert_data
        
        # Ensure notified_doctors is always a parsed list (not a JSON string) in socket payload
        if isinstance(response_data, dict):
            raw = response_data.get('notified_doctors') or response_data.get('notified_doctor_ids', '[]')
            if isinstance(raw, str):
                try:
                    response_data = {**response_data, 'notified_doctors': json.loads(raw)}
                except Exception:
                    response_data = {**response_data, 'notified_doctors': []}
        
        # Real-time notification
        socketio.emit('new_alert', response_data)
        
        return jsonify({
            "success": True, 
            "message": "SOS alert sent successfully",
            "alert": response_data
        }), 201
        
    except Exception as e:
        print(f"[ERROR] SOS trigger failed: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ── Nearest Hospital API (for SOS Navigation Map) ────────────────────────────

@alert_bp.route('/nearest-hospital', methods=['GET', 'OPTIONS'])
def get_nearest_hospital():
    """
    GET /api/nearest-hospital?lat=...&lng=...
    Returns the nearest hospital to the given coordinates.
    Used by the SOS Navigation Modal to display route to hospital.
    """
    if request.method == 'OPTIONS':
        return '', 204

    try:
        lat = request.args.get('lat')
        lng = request.args.get('lng')

        if lat is None or lng is None:
            return jsonify({"error": "lat and lng query parameters are required"}), 400

        try:
            lat = float(lat)
            lng = float(lng)
        except ValueError:
            return jsonify({"error": "Invalid coordinate values"}), 400

        # Validate coordinate ranges
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            return jsonify({"error": "Coordinates out of valid range"}), 400

        # Reuse existing Haversine-based hospital finder
        hosp_data = AppointmentService.calculate_nearest_hospital(lat, lng)

        if not hosp_data:
            return jsonify({"error": "No hospitals found in database"}), 404

        return jsonify({
            "hospital_id": hosp_data.get('_id', ''),
            "name": hosp_data.get('name', 'Unknown Hospital'),
            "latitude": hosp_data.get('lat'),
            "longitude": hosp_data.get('lon'),
            "distance": hosp_data.get('distance'),
            "capacity": hosp_data.get('capacity', 0)
        }), 200

    except Exception as e:
        print(f"[ERROR] Nearest hospital lookup failed: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
