from flask_socketio import SocketIO

# Initialize SocketIO globally so it can be imported by blueprints 
# without causing circular imports with app.py
socketio = SocketIO(cors_allowed_origins="*")
