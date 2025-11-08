from flask import Blueprint, request, jsonify
from backend.models import db, Appointment
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
        
        # Create appointment
        appointment = Appointment(
            name=data['name'],
            email=data['email'],
            phone=data['phone'],
            mode=data['mode'],
            appointment_date=appointment_date,
            appointment_time=data['time'],
            reason=data['reason'],
            status='pending'
        )
        
        db.session.add(appointment)
        db.session.commit()
        
        return jsonify({
            'message': 'Appointment booked successfully',
            'appointment_id': appointment.id,
            'status': 'pending'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating appointment: {str(e)}")
        return jsonify({'error': 'Failed to create appointment'}), 500


@appointments_bp.route('/appointments/<int:appointment_id>', methods=['GET'])
def get_appointment(appointment_id):
    """Get appointment details by ID"""
    try:
        appointment = Appointment.query.get(appointment_id)
        if not appointment:
            return jsonify({'error': 'Appointment not found'}), 404
        
        return jsonify({
            'id': appointment.id,
            'name': appointment.name,
            'email': appointment.email,
            'phone': appointment.phone,
            'mode': appointment.mode,
            'date': appointment.appointment_date.strftime('%Y-%m-%d'),
            'time': appointment.appointment_time,
            'reason': appointment.reason,
            'status': appointment.status,
            'created_at': appointment.created_at.isoformat()
        }), 200
        
    except Exception as e:
        print(f"Error fetching appointment: {str(e)}")
        return jsonify({'error': 'Failed to fetch appointment'}), 500


@appointments_bp.route('/appointments', methods=['GET'])
def list_appointments():
    """List all appointments (with optional filters)"""
    try:
        # Get query parameters for filtering
        status = request.args.get('status')
        mode = request.args.get('mode')
        date = request.args.get('date')
        
        # Build query
        query = Appointment.query
        
        if status:
            query = query.filter_by(status=status)
        if mode:
            query = query.filter_by(mode=mode)
        if date:
            appointment_date = datetime.strptime(date, '%Y-%m-%d').date()
            query = query.filter_by(appointment_date=appointment_date)
        
        appointments = query.order_by(Appointment.created_at.desc()).all()
        
        return jsonify({
            'appointments': [{
                'id': apt.id,
                'name': apt.name,
                'email': apt.email,
                'phone': apt.phone,
                'mode': apt.mode,
                'date': apt.appointment_date.strftime('%Y-%m-%d'),
                'time': apt.appointment_time,
                'reason': apt.reason,
                'status': apt.status,
                'created_at': apt.created_at.isoformat()
            } for apt in appointments]
        }), 200
        
    except Exception as e:
        print(f"Error listing appointments: {str(e)}")
        return jsonify({'error': 'Failed to list appointments'}), 500


@appointments_bp.route('/appointments/<int:appointment_id>', methods=['PATCH'])
def update_appointment_status(appointment_id):
    """Update appointment status"""
    try:
        data = request.get_json()
        
        if 'status' not in data:
            return jsonify({'error': 'Missing status field'}), 400
        
        if data['status'] not in ['pending', 'confirmed', 'completed', 'cancelled']:
            return jsonify({'error': 'Invalid status'}), 400
        
        appointment = Appointment.query.get(appointment_id)
        if not appointment:
            return jsonify({'error': 'Appointment not found'}), 404
        
        appointment.status = data['status']
        db.session.commit()
        
        return jsonify({
            'message': 'Appointment status updated',
            'status': appointment.status
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error updating appointment: {str(e)}")
        return jsonify({'error': 'Failed to update appointment'}), 500


@appointments_bp.route('/appointments/<int:appointment_id>', methods=['DELETE'])
def delete_appointment(appointment_id):
    """Delete an appointment"""
    try:
        appointment = Appointment.query.get(appointment_id)
        if not appointment:
            return jsonify({'error': 'Appointment not found'}), 404
        
        db.session.delete(appointment)
        db.session.commit()
        
        return jsonify({'message': 'Appointment deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting appointment: {str(e)}")
        return jsonify({'error': 'Failed to delete appointment'}), 500