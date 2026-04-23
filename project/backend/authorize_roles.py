from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import get_jwt, verify_jwt_in_request, get_jwt_identity

def authorize_roles(*roles):
    """
    Decorator to restrict access to specific roles.
    Expects 'role' to be present in the JWT claims.
    Skips verification for OPTIONS requests (CORS preflight).
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if request.method == 'OPTIONS':
                return fn(*args, **kwargs)
                
            verify_jwt_in_request()
            claims = get_jwt()
            user_role = claims.get("role", "user")
            
            if user_role not in roles:
                return jsonify({
                    "success": False, 
                    "error": "Forbidden: You do not have the required permissions"
                }), 403
                
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def require_medical_staff():
    """
    Decorator for medical staff.
    Checks if role is doctor or nurse. 
    If doctor, also checks if isApproved is True.
    Skips verification for OPTIONS requests (CORS preflight).
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if request.method == 'OPTIONS':
                return fn(*args, **kwargs)
                
            verify_jwt_in_request()
            claims = get_jwt()
            user_role = claims.get("role", "user")
            
            if user_role not in ["doctor", "nurse"]:
                return jsonify({"success": False, "error": "Medical staff only"}), 403
            
            # Additional check for doctors: must be approved
            if user_role == "doctor":
                from backend.db_service import DBService
                user_id = get_jwt_identity()
                user = DBService.get_user_by_id(user_id)
                
                # Handle both dict and object
                is_approved = False
                if isinstance(user, dict):
                    is_approved = user.get('isApproved', False)
                elif user:
                    is_approved = user.isApproved
                
                if not is_approved:
                    return jsonify({"success": False, "error": "Account pending approval"}), 403
                    
            return fn(*args, **kwargs)
        return wrapper
    return decorator
