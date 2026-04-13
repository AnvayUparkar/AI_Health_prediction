from flask import Blueprint, request, jsonify
import logging
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from backend.models import db, User, ShopItem
from backend.db_service import DBService

logger = logging.getLogger(__name__)

gamification_bp = Blueprint('gamification', __name__)

def calculate_points(steps, last_step_reward):
    """
    ✔ 3000 steps → +10 points
    """
    new_milestones = int(steps // 3000)
    old_milestones = int(last_step_reward // 3000)
    
    earned = (new_milestones - old_milestones) * 10
    return max(0, earned)

@gamification_bp.route('/steps/update', methods=['POST'])
@jwt_required()
def update_steps():
    """
    POST /api/steps/update
    Body: { steps: number }
    """
    identity = get_jwt_identity()
    user_id = identity.get('id') if isinstance(identity, dict) else identity
    
    data = request.get_json() or {}
    # Fetch latest steps from DB (Cloud Sync)
    latest_analysis = DBService.get_latest_health_analysis(user_id)
    steps = 0
    if latest_analysis:
        # Handle dict from Mongo or model from SQL
        if isinstance(latest_analysis, dict):
            steps = latest_analysis.get('metrics', {}).get('steps', 0)
        else:
            steps = getattr(latest_analysis, 'steps', 0)
    
    # If frontend sent more recent steps, optionally use them (but following user request to use cloud sync)
    # We will stick to the latest database record to ensure 'cloud sync' is the source of truth.

    # Robust ID check: handle MongoDB strings (hex) vs SQL Integers
    user = None
    if isinstance(user_id, str) and user_id.isdigit():
        user = User.query.get(int(user_id))
    elif isinstance(user_id, int):
        user = User.query.get(user_id)
    
    # If not in SQL, check MongoDB
    if not user:
        try:
            mongodb = DBService.get_mongo_db()
            if mongodb is not None:
                # Find user in Mongo
                user_data = mongodb.users.find_one({"_id": ObjectId(user_id)})
                if user_data:
                    # Map Mongo dict to a pseudo-object for logic below
                    user_data['id'] = str(user_data['_id'])
                    user = user_data
        except Exception as e:
            logger.error(f"Mongo user lookup failed in gamification: {e}")

    if not user:
        logger.error(f"Gamification update failed: User {user_id} not found in any database.")
        return jsonify({"success": False, "error": "User not found"}), 404
    
    # Extract points/reward data from object or dict
    u_points = user.points if isinstance(user, User) else user.get('points', 0)
    u_last_reward = user.lastStepReward if isinstance(user, User) else user.get('lastStepReward', 0)
    u_streak = user.streak if isinstance(user, User) else user.get('streak', 0)

    earned_points = calculate_points(steps, u_last_reward)
    new_total_points = u_points + earned_points
    streak = u_streak
    
    # Update streak (simple logic: if steps >= 3000, ensure streak is active)
    if steps >= 3000 and streak == 0:
        streak = 1
    
    if isinstance(user, User):
        user.points = new_total_points
        user.lastStepReward = steps
        user.streak = streak
        db.session.commit()
    else:
        # Mongo Update
        DBService._async_mongo_write('users', 'update', {
            "points": new_total_points,
            "lastStepReward": steps,
            "streak": streak
        }, {"_id": ObjectId(user['id'])})

    return jsonify({
        "success": True,
        "currentSteps": steps,
        "earnedPoints": earned_points,
        "totalPoints": new_total_points,
        "streak": streak,
        "progressPercent": min(int((steps % 3000) / 3000 * 100), 100),
        "nextMilestone": ((steps // 3000) + 1) * 3000
    }), 200

@gamification_bp.route('/shop', methods=['GET'])
@jwt_required()
def get_shop():
    """
    GET /api/shop
    """
    items = DBService.get_shop_items()
    # Handle list of model objects or dicts from Mongo
    serialized = [item.to_dict() if hasattr(item, 'to_dict') else item for item in items]
    return jsonify({"success": True, "items": serialized}), 200

@gamification_bp.route('/shop/buy', methods=['POST'])
@jwt_required()
def buy_item():
    """
    POST /api/shop/buy
    Body: { itemId: number }
    """
    identity = get_jwt_identity()
    user_id = identity.get('id') if isinstance(identity, dict) else identity
    
    data = request.get_json() or {}
    item_id = data.get('itemId')
    
    if not item_id:
        return jsonify({"success": False, "error": "Item ID required"}), 400
        
    success, message = DBService.process_purchase(user_id, item_id)
    
    if not success:
        return jsonify({"success": False, "error": message}), 400
        
    user = User.query.get(user_id)
    return jsonify({
        "success": True, 
        "message": message,
        "newPoints": user.points
    }), 200
