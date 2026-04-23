from flask import Blueprint, request, jsonify
from backend.db_service import DBService
from datetime import datetime, timedelta

doctor_availability_bp = Blueprint('doctor_availability', __name__)

def generate_sub_slots(hour_str, avg_time):
    """
    hour_str: "09:00"
    avg_time: int (minutes)
    """
    sub_slots = []
    try:
        start_time = datetime.strptime(hour_str, "%H:%M")
        end_hour = start_time + timedelta(hours=1)
        
        current = start_time
        while current < end_hour:
            slot_end = current + timedelta(minutes=avg_time)
            # If the slot ends after the hour, we can still include it as a shorter slot
            # or cap it at the end of the hour.
            actual_end = min(slot_end, end_hour)
            
            sub_slots.append({
                "start": current.strftime("%H:%M"),
                "end": actual_end.strftime("%H:%M"),
                "isBooked": False,
                "bookedBy": None
            })
            current = slot_end
    except Exception as e:
        print(f"Error generating sub-slots: {e}")
        
    return sub_slots

@doctor_availability_bp.route('/doctor/availability', methods=['POST'])
def save_availability():
    data = request.get_json()
    doctor_id = data.get('doctorId')
    date_str = data.get('date')
    hours = data.get('hours', [])
    avg_consultation_time = data.get('avgConsultationTime')
    apply_to_all = data.get('applyToAll', False)

    if not all([doctor_id, date_str, avg_consultation_time]):
        return jsonify({"error": "Missing required fields"}), 400

    if not (0 < avg_consultation_time <= 60):
        return jsonify({"error": "Average consultation time must be between 1 and 60 minutes"}), 400

    mongodb = DBService.get_mongo_db()
    if mongodb is None:
        return jsonify({"error": "Database connection failed"}), 500

    slots = []
    for hour in hours:
        slots.append({
            "hour": hour,
            "subSlots": generate_sub_slots(hour, avg_consultation_time)
        })

    # Prepare list of dates to update
    dates_to_update = [date_str]
    if apply_to_all:
        start_date = datetime.strptime(date_str, "%Y-%m-%d")
        for i in range(1, 31): # Next 30 days
            future_date = start_date + timedelta(days=i)
            dates_to_update.append(future_date.strftime("%Y-%m-%d"))

    for d in dates_to_update:
        # Upsert: Replace availability for the specific doctor and date
        mongodb.doctor_availability.update_one(
            {"doctorId": doctor_id, "date": d},
            {
                "$set": {
                    "avgConsultationTime": avg_consultation_time,
                    "slots": slots,
                    "updatedAt": datetime.utcnow()
                }
            },
            upsert=True
        )

    return jsonify({"message": f"Availability saved successfully for {len(dates_to_update)} days"}), 200


@doctor_availability_bp.route('/doctor/availability/<string:doctor_id>', methods=['GET'])
def get_availability(doctor_id):
    date = request.args.get('date')
    if not date:
        return jsonify({"error": "Date parameter is required"}), 400

    mongodb = DBService.get_mongo_db()
    if mongodb is None:
        return jsonify({"error": "Database connection failed"}), 500

    availability = mongodb.doctor_availability.find_one({"doctorId": doctor_id, "date": date})
    
    if not availability:
        return jsonify({"slots": []}), 200

    # Format response with remaining counts
    formatted_slots = []
    for slot in availability.get('slots', []):
        sub_slots = slot.get('subSlots', [])
        total = len(sub_slots)
        remaining = len([s for s in sub_slots if not s.get('isBooked')])
        
        formatted_slots.append({
            "hour": slot.get('hour'),
            "total": total,
            "remaining": remaining,
            "subSlots": sub_slots
        })

    return jsonify({"slots": formatted_slots}), 200
