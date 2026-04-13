from flask import Blueprint, request, jsonify
from backend.db_service import DBService
from datetime import datetime

appointments_bp = Blueprint('appointments', __name__)

@appointments_bp.route('/appointments', methods=['POST'])
def create_appointment():
    """Create a new appointment booking"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'email', 'phone', 'mode', 'date', 'time', 'reason']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate mode
        if data['mode'] not in ['online', 'offline']:
            return jsonify({'error': 'Invalid mode. Must be "online" or "offline"'}), 400
        
        # Parse date
        try:
            appointment_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Create appointment using DBService
        appointment_data = {
            'name': data['name'],
            'email': data['email'],
            'phone': data['phone'],
            'mode': data['mode'],
            'appointment_date': appointment_date,
            'appointment_time': data['time'],
            'reason': data['reason'],
            'status': 'pending'
        }
        
        appointment = DBService.create_appointment(appointment_data)
        
        # Determine ID to return (SQL int or Mongo string)
        apt_id = appointment['id'] if isinstance(appointment, dict) else appointment.id
        
        return jsonify({
            'message': 'Appointment booked successfully',
            'appointment_id': apt_id,
            'status': 'pending'
        }), 201
        
    except Exception as e:
        print(f"Error creating appointment: {str(e)}")
        return jsonify({'error': 'Failed to create appointment'}), 500


@appointments_bp.route('/appointments/<string:appointment_id>', methods=['GET'])
def get_appointment(appointment_id):
    """Get appointment details by ID (string to support Mongo ObjectId)"""
    try:
        appointment = DBService.get_appointment(appointment_id)
        if not appointment:
            return jsonify({'error': 'Appointment not found'}), 404
        
        # Handle both dict and model object
        is_dict = isinstance(appointment, dict)
        
        def get_val(obj, key, model_key=None):
            if is_dict: return obj.get(key)
            return getattr(obj, model_key or key)

        created_at = get_val(appointment, 'created_at')
        if not isinstance(created_at, str) and created_at:
            created_at = created_at.isoformat()

        apt_date = get_val(appointment, 'appointment_date')
        if not isinstance(apt_date, str) and apt_date:
            apt_date = apt_date.strftime('%Y-%m-%d')

        return jsonify({
            'id': get_val(appointment, 'id'),
            'name': get_val(appointment, 'name'),
            'email': get_val(appointment, 'email'),
            'phone': get_val(appointment, 'phone'),
            'mode': get_val(appointment, 'mode'),
            'date': apt_date,
            'time': get_val(appointment, 'appointment_time'),
            'reason': get_val(appointment, 'reason'),
            'status': get_val(appointment, 'status'),
            'created_at': created_at
        }), 200
        
    except Exception as e:
        print(f"Error fetching appointment: {str(e)}")
        return jsonify({'error': 'Failed to fetch appointment'}), 500


@appointments_bp.route('/appointments', methods=['GET'])
def list_appointments():
    """List all appointments (with optional filters)"""
    try:
        # Get query parameters for filtering
        filters = {
            'status': request.args.get('status'),
            'mode': request.args.get('mode'),
            'date': request.args.get('date')
        }
        
        appointments = DBService.list_appointments(filters)
        
        result_list = []
        for apt in appointments:
            is_dict = isinstance(apt, dict)
            def gv(obj, k, mk=None):
                if is_dict: return obj.get(k)
                return getattr(obj, mk or k)

            ca = gv(apt, 'created_at')
            if ca and not isinstance(ca, str): ca = ca.isoformat()
            
            ad = gv(apt, 'appointment_date')
            if ad and not isinstance(ad, str): ad = ad.strftime('%Y-%m-%d')

            result_list.append({
                'id': gv(apt, 'id'),
                'name': gv(apt, 'name'),
                'email': gv(apt, 'email'),
                'phone': gv(apt, 'phone'),
                'mode': gv(apt, 'mode'),
                'date': ad,
                'time': gv(apt, 'appointment_time'),
                'reason': gv(apt, 'reason'),
                'status': gv(apt, 'status'),
                'created_at': ca
            })

        return jsonify({
            'appointments': result_list
        }), 200
        
    except Exception as e:
        print(f"Error listing appointments: {str(e)}")
        return jsonify({'error': 'Failed to list appointments'}), 500


@appointments_bp.route('/appointments/<string:appointment_id>', methods=['PATCH'])
def update_appointment_status(appointment_id):
    """Update appointment status"""
    try:
        data = request.get_json()
        
        if 'status' not in data:
            return jsonify({'error': 'Missing status field'}), 400
        
        if data['status'] not in ['pending', 'confirmed', 'completed', 'cancelled']:
            return jsonify({'error': 'Invalid status'}), 400
        
        appointment = DBService.update_appointment_status(appointment_id, data['status'])
        if not appointment:
            return jsonify({'error': 'Appointment not found'}), 404
        
        status = appointment['status'] if isinstance(appointment, dict) else appointment.status
        
        return jsonify({
            'message': 'Appointment status updated',
            'status': status
        }), 200
        
    except Exception as e:
        print(f"Error updating appointment: {str(e)}")
        return jsonify({'error': 'Failed to update appointment'}), 500


@appointments_bp.route('/appointments/<string:appointment_id>', methods=['DELETE'])
def delete_appointment(appointment_id):
    """Delete an appointment"""
    try:
        success = DBService.delete_appointment(appointment_id)
        if not success:
            return jsonify({'error': 'Appointment not found'}), 404
        
        return jsonify({'message': 'Appointment deleted successfully'}), 200
        
    except Exception as e:
        print(f"Error deleting appointment: {str(e)}")
        return jsonify({'error': 'Failed to delete appointment'}), 500