# Modified by Cursor integration: 2025-11-07 — added auth blueprint (signup/login) using JWT
# Detected: no auth system existed previously. This blueprint provides /auth/signup and /auth/login.
# Uses flask_jwt_extended for tokens. Tokens expire in 7 days by default.

from flask import Blueprint, request, jsonify
from backend.models import db, User
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
from sqlalchemy.exc import IntegrityError

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signup', methods=['POST'])
def signup():
    """
    POST /auth/signup
    Body: { name, email, password }
    """
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    if not (name and email and password):
        return jsonify({'error': 'Name, email and password are required'}), 400

    existing = User.query.filter_by(email=email).first()
    if existing:
        return jsonify({'error': 'Email already exists'}), 409

    user = User(name=name, email=email)
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Failed to create user'}), 500

    return jsonify({'success': True, 'user': user.to_dict()}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    POST /auth/login
    Body: { email, password }
    Returns: { access_token }
    """
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    if not (email and password):
        return jsonify({'error': 'Email and password required'}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid credentials'}), 401

    access_token = create_access_token(identity={'id': user.id, 'email': user.email}, expires_delta=timedelta(days=7))
    return jsonify({'access_token': access_token, 'user': user.to_dict()})