# Modified by Cursor integration: 2025-11-07 — added auth blueprint (signup/login) using JWT
# Detected: no auth system existed previously. This blueprint provides /auth/signup and /auth/login.
# Uses flask_jwt_extended for tokens. Tokens expire in 7 days by default.

from flask import Blueprint, request, jsonify
from backend.db_service import DBService
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
from sqlalchemy.exc import IntegrityError
from backend.services.cloudinary_service import upload_certificate
from flask_jwt_extended import get_jwt
import os

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signup', methods=['POST'])
def signup():
    """
    POST /auth/signup
    Supports JSON or multipart/form-data (for doctor certificates)
    """
    if request.is_json:
        data = request.get_json() or {}
        files = {}
    else:
        data = request.form
        files = request.files

    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    role = data.get('role', 'user').strip().lower()
    
    if role not in ["doctor", "nurse", "user", "admin"]:
        role = "user"

    if not (name and email and password):
        return jsonify({'error': 'Name, email and password are required'}), 400

    existing = DBService.get_user_by_email(email)
    if existing:
        return jsonify({'error': 'Email already exists'}), 409

    # Handle doctor certificate
    cert_url = None
    cert_type = None
    is_approved = (role != 'doctor') # Admins, Nurses, Users are "approved" by default
    
    if role == 'doctor':
        cert_file = files.get('certificate')
        if cert_file:
            res = upload_certificate(cert_file)
            if res:
                cert_url = res['secure_url']
                cert_type = "pdf" if cert_url.endswith('.pdf') else "image"
            else:
                return jsonify({'error': 'Failed to upload certificate'}), 500
        else:
            # Doctors MUST upload a certificate at signup
            return jsonify({'error': 'Medical certificate is required for doctors'}), 400

    try:
        user = DBService.create_user(
            name, email, 
            generate_password_hash(password), 
            role=role,
            is_approved=is_approved,
            certificate_url=cert_url,
            certificate_type=cert_type
        )
        
        user_dict = user if isinstance(user, dict) else user.to_dict()
        return jsonify({'success': True, 'user': user_dict}), 201
    except IntegrityError:
        return jsonify({'error': 'Failed to create user'}), 500

@auth_bp.route('/doctor/upload-certificate', methods=['POST'])
@jwt_required()
def doctor_upload_certificate():
    """Allows existing doctors to upload/re-upload certificates (e.g. after rejection)"""
    user_id = get_jwt_identity()
    claims = get_jwt()
    if claims.get('role') != 'doctor':
        return jsonify({'error': 'Only doctors can upload certificates'}), 403
        
    if 'certificate' not in request.files:
        return jsonify({'error': 'No certificate file provided'}), 400
        
    cert_file = request.files['certificate']
    res = upload_certificate(cert_file)
    if not res:
        return jsonify({'error': 'Failed to upload certificate'}), 500
        
    cert_url = res['secure_url']
    cert_type = "pdf" if cert_url.endswith('.pdf') else "image"
    
    # Update user properties - reset approval on re-upload
    from backend.db_service import DBService
    user = DBService.get_user_by_id(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    # Standardize update logic for both SQL and Mongo
    update_data = {
        "certificate_url": cert_url,
        "certificate_type": cert_type,
        "isApproved": False,
        "verification_attempts": ((user.get('verification_attempts') or 0) if isinstance(user, dict) else (user.verification_attempts or 0)) + 1
    }

    if not isinstance(user, dict):
        user.certificate_url = update_data["certificate_url"]
        user.certificate_type = update_data["certificate_type"]
        user.isApproved = update_data["isApproved"]
        user.verification_attempts = update_data["verification_attempts"]
        from backend.models import db
        db.session.commit()
    
    # Sync to Mongo
    mongo_filter = {"sql_id": int(user_id)} if (isinstance(user_id, str) and user_id.isdigit()) or isinstance(user_id, int) else {"_id": DBService.get_mongo_obj_id(user_id)}
    
    mongo_update = {
        "certificate_url": cert_url,
        "certificate_type": cert_type,
        "isApproved": False,
        "verification.certificate_url": cert_url,
        "verification.certificate_type": cert_type,
        "verification.attempts": update_data["verification_attempts"]
    }
    DBService._async_mongo_write('users', 'update', mongo_update, mongo_filter)
        
    return jsonify({
        'success': True, 
        'message': 'Certificate uploaded. Pending admin review.',
        'certificate_url': cert_url
    })

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    POST /auth/login
    Body: { email, password }
    Returns: { access_token, user }
    """
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    if not (email and password):
        return jsonify({'error': 'Email and password required'}), 400

    user = DBService.get_user_by_email(email)
    
    # helper for checking password regardless of user type
    def verify(u, p):
        if isinstance(u, dict):
            return check_password_hash(u['password_hash'], p)
        return u.check_password(p)

    if not user or not verify(user, password):
        return jsonify({'error': 'Invalid credentials'}), 401

    user_id = user['id'] if isinstance(user, dict) else str(user.id)
    user_role = user['role'] if isinstance(user, dict) else user.role
    user_dict = user if isinstance(user, dict) else user.to_dict()
    
    # Include role in JWT claims for easy middleware verification
    access_token = create_access_token(
        identity=user_id, 
        additional_claims={"role": user_role},
        expires_delta=timedelta(days=7)
    )
    return jsonify({'access_token': access_token, 'user': user_dict})

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    user_id = get_jwt_identity()
    user = DBService.get_user_by_id(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(user.to_dict() if hasattr(user, 'to_dict') else user)

@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    
    from flask_jwt_extended import get_jwt
    claims = get_jwt()
    role = claims.get('role', 'user')
    
    # Restrict users to only update certain fields
    allowed_fields = ['age', 'sex', 'weight', 'height']
    
    # Allow medical staff to edit their assigned hospitals list
    if role in ['doctor', 'nurse']:
        allowed_fields.append('hospitals')
        
    profile_data = {k: v for k, v in data.items() if k in allowed_fields}
    
    user = DBService.update_user_profile(user_id, profile_data)
    if not user:
        return jsonify({'error': 'Failed to update profile'}), 500
        
    return jsonify({'success': True, 'user': user.to_dict() if hasattr(user, 'to_dict') else user})

@auth_bp.route('/users/search', methods=['GET'])
@jwt_required()
def search_users():
    # Role check
    from flask_jwt_extended import get_jwt
    claims = get_jwt()
    if claims.get('role') not in ['doctor', 'nurse']:
        return jsonify({'error': 'Unauthorized'}), 403
        
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
        
    results = DBService.search_users(query)
    # Convert to dict if they are objects
    results_list = [r.to_dict() if hasattr(r, 'to_dict') else r for r in results]
    return jsonify(results_list)

@auth_bp.route('/users/<user_id>/profile', methods=['PUT'])
@jwt_required()
def update_patient_profile(user_id):
    # Role check
    from flask_jwt_extended import get_jwt
    claims = get_jwt()
    if claims.get('role') not in ['doctor', 'nurse']:
        return jsonify({'error': 'Unauthorized'}), 403
        
    data = request.get_json() or {}
    # Doctors/Nurses can update hospitals
    allowed_fields = ['hospitals']
    profile_data = {k: v for k, v in data.items() if k in allowed_fields}
    
    user = DBService.update_user_profile(user_id, profile_data)
    if not user:
        return jsonify({'error': 'Failed to update user profile'}), 500
        
    return jsonify({'success': True, 'user': user.to_dict() if hasattr(user, 'to_dict') else user})

@auth_bp.route('/doctors/by-hospital', methods=['GET'])
def get_doctors_by_hospital():
    query = request.args.get('hospital', '')
    if not query:
        return jsonify([])
        
    doctors = DBService.get_doctors_by_hospital(query)
    results_list = [r.to_dict() if hasattr(r, 'to_dict') else r for r in doctors]
    return jsonify(results_list)