from flask import Blueprint, request, jsonify
from backend.services.appointment_service import AppointmentService
from backend.db_service import DBService
from backend.services.email_service import EmailService

doctor_appointments_bp = Blueprint('doctor_appointments', __name__)

@doctor_appointments_bp.route('/doctor_appointments/doctor/<string:doctor_id>', methods=['GET'])
def get_doctor_appointments(doctor_id):
    """Returns all appointments assigned to doctor"""
    try:
        status_filter = request.args.get('status')
        appointments = AppointmentService.get_doctor_appointments(doctor_id, status_filter)
        return jsonify({"appointments": appointments}), 200
    except Exception as e:
        print(f"Error fetching doctor appointments: {e}")
        return jsonify({"error": "Failed to fetch appointments"}), 500

@doctor_appointments_bp.route('/doctor_appointments/<string:appointment_id>/approve', methods=['POST'])
def approve_appointment(appointment_id):
    """Approve an appointment and notify both parties"""
    try:
        result = AppointmentService.approve_appointment(appointment_id)
        
        # Trigger Notifications
        try:
            full_apt = DBService.get_appointment(appointment_id)
            if full_apt:
                patient_email = full_apt.get('email')
                patient_name = full_apt.get('name', 'Patient')
                meeting_link = full_apt.get('meeting_link')
                mode = full_apt.get('mode', 'online')
                doctor_id = full_apt.get('doctor_id')
                
                # Format time for doctor email
                apt_date = full_apt.get('appointment_date') or full_apt.get('requested_date')
                apt_time = full_apt.get('appointment_time') or full_apt.get('requested_time')
                full_time_str = f"{apt_date} at {apt_time}"

                # 1. Notify Patient (if online)
                if patient_email and mode == 'online' and meeting_link:
                    EmailService.send_appointment_email(patient_email, meeting_link)
                
                # 2. Notify Doctor
                if doctor_id:
                    doctor_email = DBService.get_doctor_email(doctor_id)
                    if doctor_email:
                        EmailService.send_doctor_notification(
                            doctor_email,
                            patient_name,
                            full_time_str,
                            mode,
                            meeting_link if mode == 'online' else None
                        )
        except Exception as notify_err:
            print(f"[DoctorAppointments] Notification error: {notify_err}")

        return jsonify({"message": "Appointment approved", "appointment": result}), 200
    except Exception as e:
        print(f"Error approving appointment: {e}")
        return jsonify({"error": str(e)}), 500

@doctor_appointments_bp.route('/doctor_appointments/<string:appointment_id>/reject', methods=['POST'])
def reject_appointment(appointment_id):
    """Reject an appointment with suggested dates"""
    try:
        data = request.get_json() or {}
        suggested_dates = data.get('suggested_dates', [])
        suggested_times = data.get('suggested_times', [])
        
        result = AppointmentService.reject_appointment(appointment_id, suggested_dates, suggested_times)
        return jsonify({"message": "Appointment rejected", "appointment": result}), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        print(f"Error rejecting appointment: {e}")
        return jsonify({"error": "Failed to reject appointment"}), 500

@doctor_appointments_bp.route('/doctor_appointments/<string:appointment_id>/update-status', methods=['PATCH'])
def update_clinical_status(appointment_id):
    """Update isChecked and isAdmitted toggles"""
    try:
        data = request.get_json() or {}
        is_checked = data.get('isChecked')
        is_admitted = data.get('isAdmitted')
        
        result = AppointmentService.update_appointment_clinical_status(
            appointment_id, 
            is_checked=is_checked, 
            is_admitted=is_admitted
        )
        return jsonify({"message": "Clinical status updated", "appointment": result}), 200
    except Exception as e:
        print(f"Error updating clinical status: {e}")
        return jsonify({"error": "Failed to update status"}), 500

@doctor_appointments_bp.route('/doctor_appointments/<string:appointment_id>/assign-ward', methods=['POST'])
def assign_ward(appointment_id):
    """Assign a ward number to an admitted patient"""
    try:
        data = request.get_json() or {}
        ward_number = data.get('ward_number')
        if not ward_number:
            return jsonify({"error": "Ward number is required"}), 400
            
        result = AppointmentService.assign_ward(appointment_id, ward_number)
        return jsonify({"message": "Ward assigned successfully", "appointment": result}), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        print(f"Error assigning ward: {e}")
        return jsonify({"error": "Failed to assign ward"}), 500

@doctor_appointments_bp.route('/patients/<string:patient_id>/ward-info', methods=['GET'])
def get_patient_ward_info(patient_id):
    """Fetch ward info specifically for SOS tracing"""
    try:
        info = AppointmentService.get_patient_ward_info(patient_id)
        if not info:
            return jsonify({"status": "NOT_ADMITTED"}), 200
        return jsonify(info), 200
    except Exception as e:
        print(f"Error fetching ward info: {e}")
        return jsonify({"error": "Failed to fetch ward info"}), 500

@doctor_appointments_bp.route('/doctor_appointments/<string:appointment_id>/delete', methods=['DELETE'])
def delete_appointment(appointment_id):
    """Hard delete an appointment"""
    try:
        result = AppointmentService.delete_appointment(appointment_id)
        return jsonify({"message": "Appointment deleted", "result": result}), 200
    except Exception as e:
        print(f"Error deleting appointment: {e}")
        return jsonify({"error": "Failed to delete appointment"}), 500
