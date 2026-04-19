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
        
        if updates.get('resolved'):
            socketio.emit('SOS_RESOLVED', {
                'id': alert_id,
                'patient_id': response_data.get('patient_id')
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
        ward_number = None
        
        # 0. Check if patient is already admitted in a ward
        ward_info = AppointmentService.get_patient_ward_info(patient_id)
        if ward_info and ward_info.get('ward_number'):
            location_type = 'WARD'
            ward_number = ward_info['ward_number']
            room_desc = f"Ward {ward_number}"
            
            # If they have an assigned doctor, notify them specifically
            if ward_info.get('doctor_id'):
                notified_docs = [ward_info['doctor_id']]
            
            print(f"[SOS ROUTING] Internal Ward SOS detected for Patient={patient_id} in Ward={ward_number}")
        
        # 1. Remote Trace (Only if not in a ward or as a safety fallback)
        if location_type == 'REMOTE':
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
            "ward_number": ward_number,
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

        # ── Strategy: DB first, then OSM live fallback ────────────────────
        DB_DISTANCE_THRESHOLD_KM = 50  # If nearest DB hospital > this, query OSM

        # 1) Check our registered hospitals (DB)
        hosp_data = AppointmentService.calculate_nearest_hospital(lat, lng)

        if hosp_data and hosp_data.get('distance', 999) <= DB_DISTANCE_THRESHOLD_KM:
            # Found a close registered hospital — use it
            return jsonify({
                "hospital_id": hosp_data.get('_id', ''),
                "name": hosp_data.get('name', 'Unknown Hospital'),
                "latitude": hosp_data.get('lat'),
                "longitude": hosp_data.get('lon'),
                "distance": hosp_data.get('distance'),
                "capacity": hosp_data.get('capacity', 0),
                "source": "database"
            }), 200

        # 2) DB hospital is too far or missing — search live via OpenStreetMap
        print(f"[SOS NAV] No DB hospital within {DB_DISTANCE_THRESHOLD_KM}km. Querying OSM Overpass...")
        from backend.utils.geocode import search_nearby_hospitals_osm
        osm_hospitals = search_nearby_hospitals_osm(lat, lng, radius_km=25)

        if osm_hospitals:
            nearest = osm_hospitals[0]
            return jsonify({
                "hospital_id": "",
                "name": nearest["name"],
                "latitude": nearest["latitude"],
                "longitude": nearest["longitude"],
                "distance": nearest["distance"],
                "capacity": 0,
                "source": "osm_live"
            }), 200

        # 3) OSM also found nothing within 25km — expand to 100km
        osm_hospitals = search_nearby_hospitals_osm(lat, lng, radius_km=100)
        if osm_hospitals:
            nearest = osm_hospitals[0]
            return jsonify({
                "hospital_id": "",
                "name": nearest["name"],
                "latitude": nearest["latitude"],
                "longitude": nearest["longitude"],
                "distance": nearest["distance"],
                "capacity": 0,
                "source": "osm_live"
            }), 200

        # 4) Last resort: return the DB result even if far
        if hosp_data:
            return jsonify({
                "hospital_id": hosp_data.get('_id', ''),
                "name": hosp_data.get('name', 'Unknown Hospital'),
                "latitude": hosp_data.get('lat'),
                "longitude": hosp_data.get('lon'),
                "distance": hosp_data.get('distance'),
                "capacity": hosp_data.get('capacity', 0),
                "source": "database_fallback"
            }), 200

        return jsonify({"error": "No hospitals found nearby"}), 404

    except Exception as e:
        print(f"[ERROR] Nearest hospital lookup failed: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ── Add Hospital with Auto-Geocoding ─────────────────────────────────────────

@alert_bp.route('/hospitals', methods=['GET', 'POST', 'OPTIONS'])
def manage_hospitals():
    """
    GET  /api/hospitals           — List all hospitals
    POST /api/hospitals           — Add a new hospital (auto-geocodes coordinates)
    Body: { "name": "Hospital Name", "capacity": 100 }
    Optional: { "latitude": ..., "longitude": ... } to override geocoding
    """
    if request.method == 'OPTIONS':
        return '', 204

    from backend.models import Hospital, db

    if request.method == 'GET':
        hospitals = Hospital.query.all()
        return jsonify([h.to_dict() for h in hospitals]), 200

    # POST — Add new hospital
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({"error": "Hospital name is required"}), 400

    name = data['name'].strip()
    capacity = data.get('capacity', 100)

    # Check for duplicates
    existing = Hospital.query.filter(Hospital.name.ilike(f"%{name}%")).first()
    if existing:
        return jsonify({"error": f"Hospital '{existing.name}' already exists", "hospital": existing.to_dict()}), 409

    # Auto-geocode if coordinates not provided
    lat = data.get('latitude')
    lon = data.get('longitude')

    if lat is None or lon is None:
        from backend.utils.geocode import geocode_hospital
        lat, lon = geocode_hospital(name)
        if lat is None or lon is None:
            return jsonify({"error": f"Could not geocode '{name}'. Provide latitude and longitude manually."}), 400

    hospital = Hospital(name=name, latitude=lat, longitude=lon, capacity=capacity)
    db.session.add(hospital)
    db.session.commit()

    print(f"[INFO] Added hospital: {name} at ({lat}, {lon})")
    return jsonify({"message": f"Hospital '{name}' added successfully", "hospital": hospital.to_dict()}), 201
