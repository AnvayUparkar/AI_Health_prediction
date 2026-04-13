from flask import Blueprint, request, jsonify
import logging
from flask_jwt_extended import jwt_required, get_jwt_identity
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
    steps = data.get('steps', 0)
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404
    
    earned_points = calculate_points(steps, user.lastStepReward)
    
    if earned_points > 0:
        user.points += earned_points
        user.lastStepReward = steps
        db.session.commit()
        
        # Sync to Mongo
        DBService.update_user_gamification(user_id, user.points, user.lastStepReward, user.streak)
        
    next_milestone = ((steps // 3000) + 1) * 3000
    progress_percent = (steps % 3000) / 3000 * 100
    
    # Update streak (simple logic: if steps >= 3000, ensure streak is active)
    # Note: Real streak logic would check last update date, but sticking to requested logic.
    if steps >= 3000 and user.streak == 0:
        user.streak = 1
        db.session.commit()
    
    return jsonify({
        "success": True,
        "points": user.points,
        "earnedPoints": earned_points,
        "nextMilestone": next_milestone,
        "progressPercent": round(progress_percent, 1),
        "streak": user.streak
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
