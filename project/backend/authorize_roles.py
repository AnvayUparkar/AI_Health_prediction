from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt, verify_jwt_in_request

def authorize_roles(*roles):
    """
    Decorator to restrict access to specific roles.
    Expects 'role' to be present in the JWT claims.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
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
