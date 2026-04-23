from flask import Blueprint, request, jsonify
from backend.db_service import DBService
from datetime import datetime

appointment_booking_bp = Blueprint('appointment_booking', __name__)

@appointment_booking_bp.route('/appointment/book', methods=['POST'])
def book_appointment():
    data = request.get_json()
    doctor_id = data.get('doctorId')
    date = data.get('date')
    slot = data.get('slot') # { "start": "09:00", "end": "09:15" }
    user_id = data.get('userId')

    if not all([doctor_id, date, slot, user_id]):
        return jsonify({"error": "Missing required fields"}), 400

    mongodb = DBService.get_mongo_db()
    if mongodb is None:
        return jsonify({"error": "Database connection failed"}), 500

    # Atomic update to prevent double booking
    # We find the document where the specific sub-slot is NOT booked
    # and update it to be booked by this user.
    
    result = mongodb.doctor_availability.find_one_and_update(
        {
            "doctorId": doctor_id,
            "date": date,
            "slots.subSlots": {
                "$elemMatch": {
                    "start": slot['start'],
                    "end": slot['end'],
                    "isBooked": False
                }
            }
        },
        {
            "$set": {
                "slots.$[].subSlots.$[elem].isBooked": True,
                "slots.$[].subSlots.$[elem].bookedBy": user_id,
                "slots.$[].subSlots.$[elem].bookedAt": datetime.utcnow()
            }
        },
        array_filters=[
            {
                "elem.start": slot['start'],
                "elem.end": slot['end'],
                "elem.isBooked": False
            }
        ],
        return_document=True
    )

    if not result:
        # Check if the slot exists but is already booked
        # or if the slot doesn't exist at all.
        existing_doc = mongodb.doctor_availability.find_one({"doctorId": doctor_id, "date": date})
        if not existing_doc:
            return jsonify({"error": "No availability found for this doctor on this date"}), 404
        
        return jsonify({"error": "Slot is already booked or unavailable"}), 409

    return jsonify({
        "message": "Appointment booked successfully",
        "booking": {
            "doctorId": doctor_id,
            "date": date,
            "slot": slot,
            "userId": user_id
        }
    }), 200
