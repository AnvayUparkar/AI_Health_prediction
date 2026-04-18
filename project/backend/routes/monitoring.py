"""
Patient Monitoring API Routes — Admitted Patient Vitals & Diet Tracking.

These routes are exclusively for the Admitted Patient Monitoring System.
They do NOT modify any existing API or model behaviour.
"""
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from backend.models import db, Appointment, User, PatientMonitoring
from backend.trend_engine import run_full_analysis
from backend.db_service import DBService

monitoring_bp = Blueprint('monitoring', __name__)


class UserAdapter:
    """Simple adapter to make a dict look like a User object for the monitoring UI."""
    def __init__(self, data):
        self._data = data
        self.name = data.get('name', 'Unknown')
        self.email = data.get('email')
        self.age = data.get('age')
        self.sex = data.get('sex')
    
    def to_dict(self):
        return self._data

def _resolve_patient(raw_id):
    """
    Resolve a patient ID that might be:
      - A SQL integer ID  (e.g. '3')
      - A MongoDB ObjectId string  (e.g. '69de1e81158caae568fdbfd8')

    Returns (UserLike_or_None, canonical_pid_string)
    """
    user_data = DBService.get_user_by_id(raw_id)
    
    # If it's a dict from Mongo, wrap it
    if isinstance(user_data, dict):
        return UserAdapter(user_data), str(raw_id)
    
    # If it's a SQL object, return as is
    if user_data:
        return user_data, str(raw_id)

    # Fallback to appointment lookup if user not found directly
    appt = Appointment.query.filter_by(patient_id=str(raw_id), isAdmitted=True).first()
    if not appt:
        appt = Appointment.query.filter_by(patient_id=str(raw_id)).first()

    if appt and appt.patient_id:
        user_data = DBService.get_user_by_id(appt.patient_id)
        if isinstance(user_data, dict):
            return UserAdapter(user_data), str(raw_id)
        if user_data:
            return user_data, str(raw_id)

    return None, str(raw_id)


# ── GET Admitted Patients ─────────────────────────────────────────────────────

@monitoring_bp.route('/patients/admitted', methods=['GET', 'OPTIONS'])
def get_admitted_patients():
    """
    GET /api/patients/admitted
    Returns all patients whose appointment has isAdmitted == True,
    along with their ward info and basic profile.
    """
    if request.method == 'OPTIONS':
        return '', 204

    try:
        # Query appointments with isAdmitted=True, join with User for profile data
        # Use outerjoin because patient_id may be a Mongo ObjectId string that
        # doesn't match any SQL user.id
        admitted_appts = (
            Appointment.query
            .filter(Appointment.isAdmitted == True)
            .order_by(Appointment.ward_assigned_at.desc())
            .all()
        )

        results = []
        seen_patient_ids = set()
        for appt in admitted_appts:
            pid = appt.patient_id
            if pid in seen_patient_ids:
                continue
            seen_patient_ids.add(pid)

            # Try to resolve user profile
            user, canonical_pid = _resolve_patient(pid)

            # Compute a simple risk badge from latest monitoring data
            risk_level = "LOW"
            latest_records = (
                PatientMonitoring.query
                .filter_by(patient_id=canonical_pid)
                .order_by(PatientMonitoring.created_at.desc())
                .limit(6)
                .all()
            )
            if latest_records:
                analysis = run_full_analysis([r.to_dict() for r in reversed(latest_records)])
                critical_count = sum(1 for a in analysis['alerts'] if a['type'] == 'CRITICAL')
                warning_count = sum(1 for a in analysis['alerts'] if a['type'] == 'WARNING')
                if critical_count > 0:
                    risk_level = "CRITICAL"
                elif warning_count > 0:
                    risk_level = "WARNING"

            results.append({
                "patient_id": canonical_pid,
                "appointment_id": appt.id,
                "name": user.name if user else (f"Patient {canonical_pid[:8]}..." if len(str(canonical_pid)) > 8 else f"Patient {canonical_pid}"),
                "email": user.email if user else None,
                "age": user.age if user else None,
                "sex": user.sex if user else None,
                "ward_number": appt.ward_number,
                "doctor_id": appt.doctor_id,
                "admitted_at": appt.ward_assigned_at.isoformat() if appt.ward_assigned_at else None,
                "risk_level": risk_level,
            })

        return jsonify({"patients": results}), 200

    except Exception as e:
        print(f"[ERROR] get_admitted_patients: {e}")
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ── GET Patient Monitoring Data ───────────────────────────────────────────────

@monitoring_bp.route('/patient/<path:patient_id>/monitoring', methods=['GET', 'OPTIONS'])
def get_patient_monitoring(patient_id):
    """
    GET /api/patient/<id>/monitoring?days=7
    Returns monitoring records, computed trends, and active alerts.
    Accepts both integer SQL IDs and MongoDB ObjectId strings.
    """
    if request.method == 'OPTIONS':
        return '', 204

    try:
        days = request.args.get('days', 7, type=int)
        cutoff = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')

        user, canonical_pid = _resolve_patient(patient_id)

        records = (
            PatientMonitoring.query
            .filter(PatientMonitoring.patient_id == canonical_pid)
            .filter(PatientMonitoring.date >= cutoff)
            .order_by(PatientMonitoring.date.asc(), PatientMonitoring.created_at.asc())
            .all()
        )

        record_dicts = [r.to_dict() for r in records]

        # Run trend analysis
        analysis = run_full_analysis(record_dicts)

        # Get ward info from appointment
        appt = Appointment.query.filter_by(patient_id=canonical_pid, isAdmitted=True).first()

        patient_info = {
            "patient_id": canonical_pid,
            "name": user.name if user else f"Patient {canonical_pid[:8]}..." if len(str(canonical_pid)) > 8 else f"Patient {canonical_pid}",
            "age": user.age if user else None,
            "sex": user.sex if user else None,
            "ward_number": appt.ward_number if appt else None,
        }

        return jsonify({
            "patient": patient_info,
            "records": record_dicts,
            "trends": analysis["trends"],
            "alerts": analysis["alerts"],
        }), 200

    except Exception as e:
        print(f"[ERROR] get_patient_monitoring: {e}")
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ── POST Vitals + Diet Update ─────────────────────────────────────────────────

@monitoring_bp.route('/patient/<path:patient_id>/update-monitoring', methods=['POST', 'OPTIONS'])
def update_monitoring(patient_id):
    """
    POST /api/patient/<id>/update-monitoring
    Upsert vitals and diet data for a given patient/date/time_slot.
    Accepts both integer SQL IDs and MongoDB ObjectId strings.

    Payload:
    {
      "time_slot": "morning",
      "glucose": 140,
      "bp_systolic": 120,
      "bp_diastolic": 80,
      "spo2": 98,
      "breakfast_done": true,
      "lunch_done": false,
      "snacks_done": false,
      "dinner_done": false
    }
    """
    if request.method == 'OPTIONS':
        return '', 204

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON payload"}), 400

        time_slot = data.get('time_slot', 'morning')
        if time_slot not in ('morning', 'afternoon', 'evening'):
            return jsonify({"error": "Invalid time_slot. Use: morning, afternoon, evening"}), 400

        _, canonical_pid = _resolve_patient(patient_id)

        today = datetime.utcnow().strftime('%Y-%m-%d')
        target_date = data.get('date', today)

        # Upsert: check if a record already exists for this patient/date/slot
        existing = PatientMonitoring.query.filter_by(
            patient_id=canonical_pid,
            date=target_date,
            time_slot=time_slot,
        ).first()

        if existing:
            record = existing
        else:
            record = PatientMonitoring(
                patient_id=canonical_pid,
                date=target_date,
                time_slot=time_slot,
            )
            db.session.add(record)

        # Update fields
        if 'glucose' in data:
            record.glucose = data['glucose']
        if 'bp_systolic' in data:
            record.bp_systolic = data['bp_systolic']
        if 'bp_diastolic' in data:
            record.bp_diastolic = data['bp_diastolic']
        if 'spo2' in data:
            record.spo2 = data['spo2']
        if 'breakfast_done' in data:
            record.breakfast_done = bool(data['breakfast_done'])
        if 'lunch_done' in data:
            record.lunch_done = bool(data['lunch_done'])
        if 'snacks_done' in data:
            record.snacks_done = bool(data['snacks_done'])
        if 'dinner_done' in data:
            record.dinner_done = bool(data['dinner_done'])

        db.session.commit()

        # After saving, re-run analysis to return fresh trends + alerts
        all_records = (
            PatientMonitoring.query
            .filter(PatientMonitoring.patient_id == canonical_pid)
            .order_by(PatientMonitoring.date.asc(), PatientMonitoring.created_at.asc())
            .all()
        )
        analysis = run_full_analysis([r.to_dict() for r in all_records])

        return jsonify({
            "message": "Monitoring data saved",
            "record": record.to_dict(),
            "trends": analysis["trends"],
            "alerts": analysis["alerts"],
        }), 201

    except Exception as e:
        print(f"[ERROR] update_monitoring: {e}")
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ── GET Chart-Ready Time-Series ───────────────────────────────────────────────

@monitoring_bp.route('/patient/<path:patient_id>/timeseries', methods=['GET', 'OPTIONS'])
def get_timeseries(patient_id):
    """
    GET /api/patient/<id>/timeseries?days=7
    Returns chart-ready arrays for each metric + trend analysis.
    
    Response:
    {
      "labels": ["D1-M", "D1-A", "D1-E", "D2-M", ...],
      "glucose": [120, 130, 135, 140, 150, 160],
      "bp_systolic": [...],
      "bp_diastolic": [...],
      "spo2": [...],
      "trends": { "glucose": { "trend": "INCREASING", ... }, ... }
    }
    """
    if request.method == 'OPTIONS':
        return '', 204

    try:
        days = request.args.get('days', 7, type=int)
        cutoff = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
        _, canonical_pid = _resolve_patient(patient_id)

        # Fetch sorted records
        slot_order = {'morning': 0, 'afternoon': 1, 'evening': 2}
        records = (
            PatientMonitoring.query
            .filter(PatientMonitoring.patient_id == canonical_pid)
            .filter(PatientMonitoring.date >= cutoff)
            .order_by(PatientMonitoring.date.asc(), PatientMonitoring.created_at.asc())
            .all()
        )

        # Sort by date then slot order
        records.sort(key=lambda r: (r.date, slot_order.get(r.time_slot, 9)))

        # Build chart-ready arrays
        labels = []
        glucose_arr = []
        bp_sys_arr = []
        bp_dia_arr = []
        spo2_arr = []

        # Track unique days for label formatting
        unique_days = sorted(set(r.date for r in records))
        day_map = {d: f"D{i+1}" for i, d in enumerate(unique_days)}
        slot_abbrev = {'morning': 'M', 'afternoon': 'A', 'evening': 'E'}

        for rec in records:
            day_label = day_map.get(rec.date, rec.date)
            slot_label = slot_abbrev.get(rec.time_slot, rec.time_slot[0].upper())
            labels.append(f"{day_label}-{slot_label}")

            glucose_arr.append(rec.glucose)
            bp_sys_arr.append(rec.bp_systolic)
            bp_dia_arr.append(rec.bp_diastolic)
            spo2_arr.append(rec.spo2)

        # Run trend analysis
        record_dicts = [r.to_dict() for r in records]
        analysis = run_full_analysis(record_dicts)

        return jsonify({
            "labels": labels,
            "glucose": glucose_arr,
            "bp_systolic": bp_sys_arr,
            "bp_diastolic": bp_dia_arr,
            "spo2": spo2_arr,
            "trends": analysis["trends"],
            "alerts": analysis["alerts"],
        }), 200

    except Exception as e:
        print(f"[ERROR] get_timeseries: {e}")
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ── POST AI Diet Recommendation (Gemini) ──────────────────────────────────────

@monitoring_bp.route('/patient/<path:patient_id>/diet-ai', methods=['POST', 'OPTIONS'])
def get_diet_ai(patient_id):
    """
    POST /api/patient/<id>/diet-ai
    Generate personalized diet recommendation using Gemini AI.
    Automatically runs trend analysis first, then calls Gemini.
    """
    if request.method == 'OPTIONS':
        return '', 204

    try:
        from backend.services.gemini_service import generate_diet_recommendation

        user, canonical_pid = _resolve_patient(patient_id)

        # Fetch all monitoring records
        records = (
            PatientMonitoring.query
            .filter(PatientMonitoring.patient_id == canonical_pid)
            .order_by(PatientMonitoring.date.asc(), PatientMonitoring.created_at.asc())
            .all()
        )

        record_dicts = [r.to_dict() for r in records]
        analysis = run_full_analysis(record_dicts)

        # Get patient info
        appt = Appointment.query.filter_by(patient_id=canonical_pid, isAdmitted=True).first()

        patient_data = {
            "patient_id": canonical_pid,
            "name": user.name if user else f"Patient {canonical_pid[:8]}",
            "age": user.age if user else None,
            "sex": user.sex if user else None,
            "ward_number": appt.ward_number if appt else None,
        }

        # Call Gemini
        diet = generate_diet_recommendation(patient_data, analysis["trends"], analysis["alerts"])

        return jsonify({
            "diet": diet,
            "trends": analysis["trends"],
            "alerts": analysis["alerts"],
        }), 200

    except Exception as e:
        print(f"[ERROR] get_diet_ai: {e}")
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ── POST Seed Monitoring Data ─────────────────────────────────────────────────

@monitoring_bp.route('/monitoring/seed', methods=['POST', 'OPTIONS'])
def seed_monitoring():
    """
    POST /api/monitoring/seed
    Seed 2 days of realistic monitoring data for all admitted patients.
    Idempotent — skips patients who already have data.
    """
    if request.method == 'OPTIONS':
        return '', 204

    try:
        from backend.seed_monitoring import seed_patient_monitoring
        result = seed_patient_monitoring()
        return jsonify({"message": "Seeding complete", **result}), 201
    except Exception as e:
        print(f"[ERROR] seed_monitoring: {e}")
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500
