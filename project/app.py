import os
import sys
from typing import Optional

# Load .env before any module reads os.environ (e.g. GEMINI_API_KEY)
try:
    from dotenv import load_dotenv
    # Use explicit path so it works regardless of the CWD at launch time
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    load_dotenv(dotenv_path=_env_path, override=True)
except ImportError:
    pass  # python-dotenv optional; env vars can be set on the OS directly

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager

# Ensure repo root is on sys.path
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

# Now safe imports
from backend.models import db, init_db
from backend.routes.auth import auth_bp
from backend.routes.predict import predict_bp
from backend.routes.diet import diet_bp
from backend.routes.workout import workout_bp
from backend.routes.appointments import appointments_bp
from backend.routes.diet_plan import diet_plan_bp
from backend.routes.report_analysis import report_analysis_bp
from backend.routes.health_analysis import health_analysis_bp
from backend.routes.google_fit_sync import google_fit_sync_bp
from backend.routes.google_fit_debug import google_fit_debug_bp
from backend.routes.health_connect_sync import health_connect_sync_bp
from backend.routes.gamification import gamification_bp
from backend.routes.google_auth import google_auth_bp
from backend.routes.chat import chat_bp
from backend.routes.alert import alert_bp
from backend.db_service import DBService
from backend.extensions import socketio

def create_app(config_overrides: Optional[dict] = None):
    app = Flask(__name__, static_folder=None)

    # CRITICAL FIX: Configure CORS properly
    CORS(app, 
         resources={r"/*": {
             "origins": "*",
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
             "allow_headers": ["Content-Type", "Authorization"],
             "expose_headers": ["Authorization"],
             "supports_credentials": False
         }})

    # Config
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(backend_dir, 'app.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'change-this-secret')
    app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB upload limit

    if config_overrides:
        app.config.update(config_overrides)

    db.init_app(app)
    socketio.init_app(app)
    JWTManager(app)

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(predict_bp, url_prefix='/api')
    app.register_blueprint(diet_bp, url_prefix='/api')
    app.register_blueprint(workout_bp, url_prefix='/api')
    app.register_blueprint(appointments_bp, url_prefix='/api')
    app.register_blueprint(diet_plan_bp, url_prefix='/api')
    app.register_blueprint(report_analysis_bp, url_prefix='/api')
    app.register_blueprint(health_analysis_bp, url_prefix='/api')
    app.register_blueprint(google_fit_sync_bp, url_prefix='/api')
    app.register_blueprint(google_fit_debug_bp, url_prefix='/api')
    app.register_blueprint(health_connect_sync_bp, url_prefix='/api')
    app.register_blueprint(gamification_bp, url_prefix='/api')
    app.register_blueprint(google_auth_bp, url_prefix='/api')
    app.register_blueprint(chat_bp, url_prefix='/api')
    app.register_blueprint(alert_bp, url_prefix='/api')

    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({'status': 'ok', 'message': 'Server is running'})

    # Add explicit OPTIONS handler for all routes
    @app.route('/<path:path>', methods=['OPTIONS'])
    def handle_options(path):
        return '', 204

    # Legacy endpoints for backward compatibility
    @app.route('/predict_diabetes', methods=['OPTIONS', 'POST'])
    def legacy_predict_diabetes():
        if request.method == 'OPTIONS':
            return '', 204
        data = request.get_json(silent=True) or {}
        features = data if isinstance(data, dict) else {}
        from backend.routes.predict import predict_with_type
        resp, status = predict_with_type('diabetes', features)
        return jsonify(resp), status

    @app.route('/predict_lung_cancer', methods=['OPTIONS', 'POST'])
    def legacy_predict_lung_cancer():
        if request.method == 'OPTIONS':
            return '', 204
        data = request.get_json(silent=True) or {}
        features = data if isinstance(data, dict) else {}
        from backend.routes.predict import predict_with_type
        resp, status = predict_with_type('lung_cancer', features)
        return jsonify(resp), status

    # Initialize DB
    with app.app_context():
        try:
            init_db(app)
            print(f"[OK] Initialized SQLite DB at {app.config['SQLALCHEMY_DATABASE_URI']}")
            
            # Log Migration Settings
            db_mode = os.environ.get('DB_MODE', 'sql')
            read_from = os.environ.get('READ_FROM', 'sql')
            print(f"[INFO] Migration Mode: {db_mode.upper()}")
            print(f"[INFO] Reading From: {read_from.upper()}")
            
            # Try Mongo init if not strictly SQL
            if db_mode != 'sql' or read_from == 'mongo':
                mongo_db = DBService.get_mongo_db()
                if mongo_db is not None:
                    print(f"[OK] Connected to MongoDB Atlas")
                else:
                    print(f"[WARN] Failed to connect to MongoDB - falling back to SQL only")
        except Exception as e:
            print(f"[ERROR] DB init failed: {e}")

        # Load ML models (non-blocking)
        try:
            from backend.routes.predict import load_models_once
            load_models_once()
        except Exception as e:
            print(f"[WARN] Model loading encountered errors: {e}")
            print("  Server will continue - some predictions may not be available")

    @socketio.on('gesture_frame')
    def handle_gesture(data):
        """
        Receives frame from frontend and processes it via GestureService.
        """
        try:
            from backend.gesture_service import gesture_detector
            frame_data = data.get('frame')
            patient_info = data.get('info', {})
            
            if not frame_data:
                return
                
            result = gesture_detector.process_frame(frame_data, patient_info)
            socketio.emit('gesture_result', result)
            
        except Exception as e:
            print(f"[SOCKET ERROR] Gesture processing failed: {e}")

    return app


if __name__ == '__main__':
    app = create_app()
    print("=" * 70)
    print("Starting Flask server...")
    print("Health Prediction API Server")
    print("=" * 70)
    print("Server URL: http://localhost:5000")
    print("Health check: http://localhost:5000/health")
    print("")
    print("Prediction endpoints:")
    print("   - POST /api/predict")
    print("   - POST /predict_diabetes (legacy)")
    print("   - POST /predict_lung_cancer (legacy)")
    print("")
    print("Appointment endpoints:")
    print("   - POST /api/appointments")
    print("   - GET /api/appointments")
    print("   - GET /api/appointments/<id>")
    print("   - PATCH /api/appointments/<id>")
    print("   - DELETE /api/appointments/<id>")
    print("")
    print("Diet Plan endpoints:")
    print("   - POST /api/diet-plan")
    print("   - POST /api/diet-plan/validate")
    print("")
    print("Workout endpoints:")
    print("   - GET /api/workouts")
    print("   - POST /api/workouts/generate")
    print("")
    print("Diet endpoints:")
    print("   - GET /api/diet")
    print("   - POST /api/diet/generate")
    print("")
    print("Report Analysis endpoints:")
    print("   - POST /api/analyze-report")
    print("")
    print("Auth endpoints:")
    print("   - POST /auth/register")
    print("   - POST /auth/login")
    print("=" * 70)
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
