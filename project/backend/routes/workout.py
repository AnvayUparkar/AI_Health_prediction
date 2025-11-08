# Modified by Cursor integration: 2025-11-07 — workout blueprint returning a weekly plan
# Detected: no workout endpoints. Simple planner based on optional query params goal/level

from flask import Blueprint, request, jsonify

workout_bp = Blueprint('workout', __name__)

DEFAULT_PLAN = [
    {'day': 'Monday', 'workout': '30 min Cardio + Mobility', 'duration_min': 30},
    {'day': 'Tuesday', 'workout': 'Upper Body Strength (45 min)', 'duration_min': 45},
    {'day': 'Wednesday', 'workout': 'Yoga / Active Recovery (30 min)', 'duration_min': 30},
    {'day': 'Thursday', 'workout': 'Lower Body Strength (45 min)', 'duration_min': 45},
    {'day': 'Friday', 'workout': 'HIIT (20 min)', 'duration_min': 20},
    {'day': 'Saturday', 'workout': 'Full Body Mobility / Walk (30 min)', 'duration_min': 30},
    {'day': 'Sunday', 'workout': 'Rest or light walk (30 min)', 'duration_min': 30},
]

@workout_bp.route('/workout-plan', methods=['GET'])
def workout_plan():
    """
    GET /api/workout-plan?goal=weight-loss|strength|maintain&level=beginner|intermediate|advanced
    Returns a simple weekly plan adjusted by goal/level.
    """
    goal = (request.args.get('goal') or '').lower()
    level = (request.args.get('level') or 'beginner').lower()

    plan = DEFAULT_PLAN.copy()

    # Adjust durations and intensity based on level
    level_multiplier = 1.0
    if level == 'beginner':
        level_multiplier = 0.8
    elif level == 'intermediate':
        level_multiplier = 1.0
    elif level == 'advanced':
        level_multiplier = 1.2

    adjusted = []
    for item in plan:
        duration = int(item['duration_min'] * level_multiplier)
        workout = item['workout']
        if goal == 'weight-loss':
            # add extra cardio
            if 'Cardio' in workout or 'HIIT' in workout:
                duration = int(duration * 1.2)
        if goal == 'strength':
            if 'Strength' in workout:
                duration = int(duration * 1.2)
        adjusted.append({**item, 'duration_min': duration})

    return jsonify({'week': adjusted, 'goal': goal or 'general', 'level': level})