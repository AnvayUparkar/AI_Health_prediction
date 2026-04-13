import os
import json
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, redirect, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from bson import ObjectId
from backend.models import db, User
from backend.db_service import DBService

logger = logging.getLogger(__name__)
google_auth_bp = Blueprint('google_auth', __name__)

# User's provided path (for local dev)
CLIENT_SECRET_PATH = r"C:\Users\Anvay Uparkar\Hackathon projects\AI_Health_prediction\project\client_secret_436743225854-418loq227rgki0rk8freubjmf2v8r5t9.apps.googleusercontent.com.json"
REDIRECT_URI = "http://localhost:5173"

# Scopes: User asked for contacts, but we likely need health for this app too.
SCOPES = [

    "https://www.googleapis.com/auth/contacts.readonly",
    "https://www.googleapis.com/auth/fitness.activity.read",
    "https://www.googleapis.com/auth/fitness.body.read",
]

@google_auth_bp.route('/auth/google/url', methods=['GET'])
def get_auth_url():
    """Generates the Google OAuth URL for the standard Web Flow."""
    try:
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRET_PATH,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        # prompt='consent' ensures we get a refresh token
        auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
        return jsonify({"success": True, "url": auth_url}), 200
    except Exception as e:
        logger.error(f"Failed to generate Google Auth URL: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@google_auth_bp.route('/auth/google/callback', methods=['POST'])
def google_callback():
    """Handles the redirect from Google, exchanges code for tokens, and saves them."""
    data = request.get_json() or {}
    code = data.get('code')
    
    if not code:
        return jsonify({"success": False, "error": "Auth code missing"}), 400
        
    try:
        # Get current identity if available (for linking while logged in)
        from flask_jwt_extended import get_jwt_request_config
        identity = None
        try:
            # Manually check for JWT without requiring it for the whole route
            from flask_jwt_extended import verify_jwt_in_request
            verify_jwt_in_request(optional=True)
            identity = get_jwt_identity()
        except:
            pass

        user_id = None
        if identity:
            user_id = identity.get('id') if isinstance(identity, dict) else identity
    
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRET_PATH,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        flow.fetch_token(code=code)
        
        creds = flow.credentials
        creds_json = creds.to_json()
        
        # Verify ID token to get Google Email
        info = id_token.verify_oauth2_token(creds.id_token, Request(), creds.client_id)
        google_email = info.get('email')

        user = None
        # Robust ID check: handle MongoDB strings (hex) vs SQL Integers
        if user_id:
            # If it's a numeric string, try SQL lookup first
            if isinstance(user_id, str) and user_id.isdigit():
                user = User.query.get(int(user_id))
            elif isinstance(user_id, int):
                user = User.query.get(user_id)
            
            # If still not found, check MongoDB via DBService (which handles ObjectID strings)
            if not user and isinstance(user_id, str):
                mongo_user = DBService.get_user_by_email(google_email) # Use email helper which is mode-aware
                if mongo_user:
                    user = mongo_user
        
        elif google_email:
            # Try to find user by email (Google Login)
            user = DBService.get_user_by_email(google_email)

        if user:
            # Save token
            if isinstance(user, User):
                # SQL User object
                user.google_token_json = creds_json
                user.google_last_auth_at = datetime.utcnow()
                db.session.commit()
            else:
                # MongoDB User dict
                DBService._async_mongo_write('users', 'update', {
                    "google_token_json": creds_json,
                    "google_last_auth_at": datetime.utcnow().isoformat()
                }, {"_id": ObjectId(user['id'])})

            # If they weren't logged in, log them in now
            access_token = None
            if not user_id:
                # Get the ID from either object or dict
                uid = str(user.id if isinstance(user, User) else user['id'])
                role = user.role if isinstance(user, User) else user.get('role', 'user')
                
                access_token = create_access_token(
                    identity=uid,
                    additional_claims={"role": role},
                    expires_delta=timedelta(days=7)
                )

            user_resp = user.to_dict() if isinstance(user, User) else user
            return jsonify({
                "success": True, 
                "message": "Google account linked successfully",
                "token": access_token,
                "user": user_resp
            }), 200
    except Exception as e:
        logger.error(f"Google Callback Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@google_auth_bp.route('/auth/google/logout', methods=['POST'])
@jwt_required()
def google_logout():
    """Removes the Google token from the user profile (Delete Token on Logout)."""
    identity = get_jwt_identity()
    user_id = identity.get('id') if isinstance(identity, dict) else identity
    
    # Handle DB Identity
    user = None
    if isinstance(user_id, str) and user_id.isdigit():
        user = User.query.get(int(user_id))
    elif isinstance(user_id, int):
        user = User.query.get(user_id)
    
    if user:
        user.google_token_json = None
        user.google_last_auth_at = None
        db.session.commit()
        return jsonify({"success": True, "message": "Google account unlinked (SQL)"}), 200
    else:
        # Check Mongo
        try:
            from bson import ObjectId
            mongodb = DBService.get_mongo_db()
            if mongodb is not None:
                mongodb.users.update_one(
                    {"_id": ObjectId(user_id)},
                    {"$set": {"google_token_json": None, "google_last_auth_at": None}}
                )
                return jsonify({"success": True, "message": "Google account unlinked (Mongo)"}), 200
        except Exception as e:
            logger.error(f"Mongo logout cleanup failed: {e}")
            
    return jsonify({"success": False, "error": "User not found or ID format invalid"}), 404

def get_user_google_creds(user):
    """
    Retrieves and refreshes Google credentials for a specific user.
    Adheres to the 365-day force re-auth logic from user's reference.
    """
    if not user.google_token_json:
        return None
        
    # Check 1-year force re-auth logic
    if user.google_last_auth_at:
        one_year_ago = datetime.utcnow() - timedelta(days=365)
        if user.google_last_auth_at < one_year_ago:
            logger.info(f"User {user.id} Google Token expired (1 year limit). Forcing re-auth.")
            user.google_token_json = None
            user.google_last_auth_at = None
            db.session.commit()
            return None

    try:
        creds_data = json.loads(user.google_token_json)
        creds = Credentials.from_authorized_user_info(creds_data, SCOPES)
        
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Save refreshed token back to DB
            user.google_token_json = creds.to_json()
            # We don't update google_last_auth_at on refresh, 
            # as it's meant to track the last FULL authentication per user's logic.
            db.session.commit()
            logger.info(f"Refreshed Google token for user {user.id}")
        
        return creds
    except Exception as e:
        logger.error(f"Error loading/refreshing Google creds for user {user.id}: {e}")
        return None
