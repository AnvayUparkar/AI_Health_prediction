import os
import sys
from typing import Optional
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
    JWTManager(app)

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(predict_bp, url_prefix='/api')
    app.register_blueprint(diet_bp, url_prefix='/api')
    app.register_blueprint(workout_bp, url_prefix='/api')
    app.register_blueprint(appointments_bp, url_prefix='/api')
    app.register_blueprint(diet_plan_bp, url_prefix='/api')

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
            print(f"✓ Initialized SQLite DB at {app.config['SQLALCHEMY_DATABASE_URI']}")
        except Exception as e:
            print(f"✗ DB init failed: {e}")

        # Load ML models (non-blocking)
        try:
            from backend.routes.predict import load_models_once
            load_models_once()
        except Exception as e:
            print(f"⚠ Model loading encountered errors: {e}")
            print("  Server will continue - some predictions may not be available")

    return app

if __name__ == '__main__':
    app = create_app()
    print("=" * 70)
    print("🚀 Starting Flask server...")
    print("🏥 Health Prediction API Server")
    print("=" * 70)
    print("📍 Server URL: http://localhost:5000")
    print("🏥 Health check: http://localhost:5000/health")
    print("")
    print("🔮 Prediction endpoints:")
    print("   - POST /api/predict")
    print("   - POST /predict_diabetes (legacy)")
    print("   - POST /predict_lung_cancer (legacy)")
    print("")
    print("📅 Appointment endpoints:")
    print("   - POST /api/appointments")
    print("   - GET /api/appointments")
    print("   - GET /api/appointments/<id>")
    print("   - PATCH /api/appointments/<id>")
    print("   - DELETE /api/appointments/<id>")
    print("")
    print("🥗 Diet Plan endpoints:")
    print("   - POST /api/diet-plan")
    print("   - POST /api/diet-plan/validate")
    print("")
    print("💪 Workout endpoints:")
    print("   - GET /api/workouts")
    print("   - POST /api/workouts/generate")
    print("")
    print("🍽️ Diet endpoints:")
    print("   - GET /api/diet")
    print("   - POST /api/diet/generate")
    print("")
    print("🔐 Auth endpoints:")
    print("   - POST /auth/register")
    print("   - POST /auth/login")
    print("=" * 70)
    app.run(host='0.0.0.0', port=5000, debug=True)