# Modified by Cursor integration: 2025-11-07 — added auth blueprint (signup/login) using JWT
# Detected: no auth system existed previously. This blueprint provides /auth/signup and /auth/login.
# Uses flask_jwt_extended for tokens. Tokens expire in 7 days by default.

from flask import Blueprint, request, jsonify
from backend.db_service import DBService
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
from sqlalchemy.exc import IntegrityError

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signup', methods=['POST'])
def signup():
    """
    POST /auth/signup
    Body: { name, email, password, role }
    """
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    role = data.get('role', 'user').strip().lower()
    
    if role not in ["doctor", "nurse", "user"]:
        role = "user"

    if not (name and email and password):
        return jsonify({'error': 'Name, email and password are required'}), 400

    existing = DBService.get_user_by_email(email)
    if existing:
        return jsonify({'error': 'Email already exists'}), 409

    try:
        user = DBService.create_user(name, email, generate_password_hash(password), role=role)
        
        # Handle if user is a dict (Mongo) or object (SQL)
        user_dict = user if isinstance(user, dict) else user.to_dict()
        return jsonify({'success': True, 'user': user_dict}), 201
    except IntegrityError:
        return jsonify({'error': 'Failed to create user'}), 500

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
    
    # Restrict users to only update certain fields
    allowed_fields = ['age', 'sex', 'weight', 'height']
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