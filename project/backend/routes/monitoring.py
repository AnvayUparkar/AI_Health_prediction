"""
Patient Monitoring API Routes — Admitted Patient Vitals & Diet Tracking.

These routes are exclusively for the Admitted Patient Monitoring System.
They do NOT modify any existing API or model behaviour.
"""
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from backend.models import db, Appointment, User, PatientMonitoring
from backend.trend_engine import run_full_analysis

monitoring_bp = Blueprint('monitoring', __name__)


def _resolve_patient(raw_id):
    """
    Resolve a patient ID that might be:
      - A SQL integer ID  (e.g. '3')
      - A MongoDB ObjectId string  (e.g. '69de1e81158caae568fdbfd8')

    Returns (sql_user_or_None, canonical_pid_string)
    The canonical_pid_string is what the Appointment table stores in patient_id.
    """
    # Try SQL integer lookup first
    try:
        sql_id = int(raw_id)
        user = User.query.get(sql_id)
        if user:
            return user, str(sql_id)
    except (ValueError, TypeError):
        pass

    # It's a Mongo-style string — look up the appointment that stores this ID
    appt = Appointment.query.filter_by(patient_id=str(raw_id), isAdmitted=True).first()
    if not appt:
        appt = Appointment.query.filter_by(patient_id=str(raw_id)).first()

    # Try to resolve the user via SQL join if patient_id is numeric
    user = None
    if appt and appt.patient_id:
        try:
            user = User.query.get(int(appt.patient_id))
        except (ValueError, TypeError):
            pass

    return user, str(raw_id)


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
