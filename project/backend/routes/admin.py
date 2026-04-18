from flask import Blueprint, request, jsonify
from backend.db_service import DBService
from backend.authorize_roles import authorize_roles, require_medical_staff
from flask_jwt_extended import jwt_required, get_jwt_identity

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/pending-doctors', methods=['GET'])
@authorize_roles('admin')
def get_pending_doctors():
    doctors = DBService.get_pending_doctors()
    # Handle both list of dicts (Mongo) and list of objects (SQL)
    results = [d if isinstance(d, dict) else d.to_dict() for d in doctors]
    return jsonify({"success": True, "doctors": results})

@admin_bp.route('/doctor/<user_id>', methods=['GET'])
@authorize_roles('admin')
def get_doctor_details(user_id):
    user = DBService.get_user_by_id(user_id)
    if not user:
        return jsonify({"success": False, "error": "Doctor not found"}), 404
    
    user_dict = user if isinstance(user, dict) else user.to_dict()
    return jsonify({"success": True, "doctor": user_dict})

@admin_bp.route('/approve/<user_id>', methods=['POST'])
@authorize_roles('admin')
def approve_doctor(user_id):
    success = DBService.approve_doctor(user_id)
    if success:
        return jsonify({"success": True, "message": "Doctor approved successfully"})
    return jsonify({"success": False, "error": "Failed to approve doctor"}), 500

@admin_bp.route('/reject/<user_id>', methods=['POST'])
@authorize_roles('admin')
def reject_doctor(user_id):
    data = request.get_json() or {}
    reason = data.get('reason', 'Requirements not met.')
    
    success = DBService.reject_doctor(user_id, reason)
    if success:
        return jsonify({"success": True, "message": "Doctor rejected successfully"})
    return jsonify({"success": False, "error": "Failed to reject doctor"}), 500
