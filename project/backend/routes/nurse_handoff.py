from flask import Blueprint, request, jsonify
from backend.models import db, User, Medication, MedicationLog, HandoffReport
from datetime import datetime
import json
from backend.extensions import socketio

nurse_handoff_bp = Blueprint('nurse_handoff', __name__)

@nurse_handoff_bp.route('/add-medicine', methods=['POST'])
def add_medicine():
    data = request.json
    patient_id = data.get('patient_id')
    name = data.get('name')
    dosage = data.get('dosage')
    times = data.get('times', []) # List of times like ["08:00", "20:00"]

    if not all([patient_id, name, dosage, times]):
        return jsonify({"error": "Missing required fields"}), 400

    med = Medication(
        patient_id=patient_id,
        name=name,
        dosage=dosage,
        times=json.dumps(times)
    )
    db.session.add(med)
    db.session.commit()

    # Seed logs for today for these times
    today = datetime.now().strftime('%Y-%m-%d')
    for t in times:
        log = MedicationLog(
            medication_id=med.id,
            patient_id=patient_id,
            scheduled_time=t,
            date=today,
            status='PENDING'
        )
        db.session.add(log)
    db.session.commit()

    return jsonify({"message": "Medicine added successfully", "id": med.id}), 201

@nurse_handoff_bp.route('/patient-medicines', methods=['GET'])
def get_patient_medicines():
    patient_id = request.args.get('patient_id')
    if not patient_id:
        return jsonify({"error": "Patient ID is required"}), 400

    today = datetime.now().strftime('%Y-%m-%d')
    
    # Get all medications for patient
    meds = Medication.query.filter_by(patient_id=patient_id).all()
    
    # Get all logs for today for these medications
    logs = MedicationLog.query.filter_by(patient_id=patient_id, date=today).all()
    
    # Ensure logs exist for today for all meds (Auto-seed if missing)
    existing_log_med_ids = {l.medication_id for l in logs}
    needed_seeding = False
    for med in meds:
        if med.id not in existing_log_med_ids:
            needed_seeding = True
            try:
                times = json.loads(med.times)
                for t in times:
                    new_log = MedicationLog(
                        medication_id=med.id,
                        patient_id=patient_id,
                        scheduled_time=t,
                        date=today,
                        status='PENDING'
                    )
                    db.session.add(new_log)
            except:
                pass
    
    if needed_seeding:
        db.session.commit()
        # Re-fetch logs after seeding
        logs = MedicationLog.query.filter_by(patient_id=patient_id, date=today).all()

    logs_dict = {(l.medication_id, l.scheduled_time): l for l in logs}

    result = []
    for med in meds:
        med_dict = med.to_dict()
        med_dict['daily_status'] = []
        for t in med_dict['times']:
            log = logs_dict.get((med.id, t))
            med_dict['daily_status'].append({
                "time": t,
                "status": log.status if log else 'PENDING',
                "log_id": log.id if log else None
            })
        result.append(med_dict)

    return jsonify({"medicines": result})

@nurse_handoff_bp.route('/mark-given', methods=['PATCH'])
def mark_given():
    data = request.json
    log_id = data.get('log_id')
    
    if not log_id:
        return jsonify({"error": "Log ID is required"}), 400

    log = MedicationLog.query.get(log_id)
    if not log:
        return jsonify({"error": "Log entry not found"}), 404

    log.status = 'GIVEN'
    log.given_at = datetime.utcnow()
    db.session.commit()

    # Notify via Socket.IO that a medicine was given (to update other nurse dashboards)
    socketio.emit('medicine_updated', {"patient_id": log.patient_id, "log_id": log.id, "status": "GIVEN"})

    return jsonify({"message": "Medication marked as given"})

from flask_jwt_extended import jwt_required, get_jwt_identity

@nurse_handoff_bp.route('/pending-notifications', methods=['GET'])
@jwt_required()
def get_pending_notifications():
    user_id = get_jwt_identity()
    current_user = User.query.get(user_id)
    if not current_user:
        return jsonify({"notifications": []}), 404

    # Determine visibility scope
    user_hospitals = []
    try:
        user_hospitals = json.loads(current_user.hospitals) if current_user.hospitals else []
    except:
        user_hospitals = []

    is_medical = current_user.role in ['doctor', 'nurse']

    today = datetime.now().strftime('%Y-%m-%d')
    now_time = datetime.now().strftime('%H:%M')
    
    pending = db.session.query(MedicationLog, Medication).join(
        Medication, MedicationLog.medication_id == Medication.id
    ).filter(
        MedicationLog.date == today,
        MedicationLog.status == 'PENDING',
        MedicationLog.scheduled_time <= now_time
    ).all()

    from backend.routes.monitoring import _resolve_patient

    result = []
    for log, med in pending:
        # Check permission
        show = False
        if str(med.patient_id) == str(user_id):
            show = True
        elif is_medical:
            # Check if patient is in one of the doctor's hospitals
            patient_user, _ = _resolve_patient(med.patient_id)
            if patient_user:
                try:
                    ph = patient_user.hospitals
                    patient_hospitals = json.loads(ph) if isinstance(ph, str) else (ph or [])
                    
                    # Check for overlap
                    if any(h in user_hospitals for h in patient_hospitals):
                        show = True
                except:
                    pass

        
        if show:
            patient_user, _ = _resolve_patient(med.patient_id)
            user_name = patient_user.name if patient_user else "Patient"
            result.append({
                "log_id": log.id,
                "patient_name": user_name,
                "patient_id": med.patient_id,
                "medicine_name": med.name,
                "dosage": med.dosage,
                "time": log.scheduled_time,
                "is_overdue": log.scheduled_time < now_time
            })

    return jsonify({"notifications": result})


@nurse_handoff_bp.route('/delete-medicine/<int:med_id>', methods=['DELETE'])
def delete_medicine(med_id):
    med = Medication.query.get(med_id)
    if not med:
        return jsonify({"error": "Medication not found"}), 404
    
    # Delete associated logs first
    MedicationLog.query.filter_by(medication_id=med_id).delete()
    
    db.session.delete(med)
    db.session.commit()
    
    return jsonify({"message": "Medication deleted successfully"})

@nurse_handoff_bp.route('/handoff-report', methods=['GET', 'POST'])
def handle_handoff():
    if request.method == 'POST':
        data = request.json
        patient_id = data.get('patient_id')
        
        report = HandoffReport.query.filter_by(patient_id=patient_id).first()
        if not report:
            report = HandoffReport(patient_id=patient_id)
            db.session.add(report)
        
        report.diagnosis = data.get('diagnosis', report.diagnosis)
        report.current_condition = data.get('current_condition', report.current_condition)
        report.vitals_summary = data.get('vitals_summary', report.vitals_summary)
        report.ongoing_treatments = data.get('ongoing_treatments', report.ongoing_treatments)
        report.previous_nurse_notes = data.get('previous_nurse_notes', report.previous_nurse_notes)
        
        db.session.commit()
        return jsonify({"message": "Report updated successfully", "report": report.to_dict()})

    else:
        patient_id = request.args.get('patient_id')
        report = HandoffReport.query.filter_by(patient_id=patient_id).first()
        if not report:
            # Return empty structure if not found
            return jsonify({"report": {
                "patient_id": patient_id,
                "diagnosis": "",
                "current_condition": "",
                "vitals_summary": "",
                "ongoing_treatments": "",
                "previous_nurse_notes": ""
            }})
        return jsonify({"report": report.to_dict()})
