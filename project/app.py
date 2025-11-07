from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import pandas as pd
import numpy as np
import os

app = Flask(__name__)
CORS(app)

# --- 1. Correctly Define Model Paths ---
# Get the absolute path of the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Define paths to the model files relative to this script's location
LUNG_CANCER_MODEL_PATH = os.path.join(BASE_DIR, 'models', 'lung_cancer_model.pkl')
LUNG_CANCER_LABEL_ENCODER_PATH = os.path.join(BASE_DIR, 'models', 'lung_cancer_label_encoder.pkl')
DIABETES_MODEL_PATH = os.path.join(BASE_DIR, 'models', 'diabetes_model.pkl')
DIABETES_LABEL_ENCODER_PATH = os.path.join(BASE_DIR, 'models', 'diabetes_label_encoder.pkl')

# Global variables to store loaded models
lung_cancer_model = None
lung_cancer_label_encoder = None
diabetes_model = None
diabetes_label_encoder = None

# --- 2. Align Features with Training Notebooks ---

# Features for Lung Cancer model (must match the training data order)
LUNG_CANCER_FEATURES = []  # will be populated from dataset at startup

# Path to lung cancer dataset used during training/feature discovery
LUNG_CANCER_DATA_PATH = os.path.join(BASE_DIR, 'cancer patient data sets.csv')

# Mapping from normalized column name -> actual dataset column name (after stripping)
LUNG_CANCER_COLUMN_MAP = {}

# Mapping from normalized model feature name -> actual model feature name
# Mapping from normalized model feature name -> actual model feature name
MODEL_FEATURE_MAP = {}
# Ordered list of model feature names (if available) to preserve training order
MODEL_FEATURE_ORDER = []

# Features for Diabetes model (must match the training data order)
DIABETES_FEATURES = [
    'Age', 'Gender', 'Polyuria', 'Polydipsia', 'sudden weight loss', 
    'weakness', 'Polyphagia', 'Genital thrush', 'visual blurring', 
    'Itching', 'Irritability', 'delayed healing', 'partial paresis', 
    'muscle stiffness', 'Alopecia', 'Obesity'
]

def load_models():
    """Load all pre-trained models and encoders from .pkl files."""
    global lung_cancer_model, lung_cancer_label_encoder, diabetes_model, diabetes_label_encoder
    global LUNG_CANCER_FEATURES, LUNG_CANCER_COLUMN_MAP
    
    try:
        # Load the lung cancer dataset columns so we can accept inputs that match the
        # dataset column names (this helps avoid mismatched feature names between
        # frontend keys and training data).
        if os.path.exists(LUNG_CANCER_DATA_PATH):
            try:
                df_lung = pd.read_csv(LUNG_CANCER_DATA_PATH)
                # Normalize headers by stripping whitespace
                df_lung.rename(columns=lambda c: c.strip(), inplace=True)
                # Exclude common target columns if present
                excluded = {'Level', 'Level_encoded', 'Level_encoded '}
                features = [c for c in df_lung.columns if c not in excluded]
                LUNG_CANCER_FEATURES = features

                # Build normalization map for incoming JSON keys
                def normalize(name: str) -> str:
                    return ''.join(name.lower().strip().split()).replace('_', '').replace('-', '')

                LUNG_CANCER_COLUMN_MAP = {normalize(col): col for col in LUNG_CANCER_FEATURES}
                print(f"Detected lung cancer features from dataset ({LUNG_CANCER_DATA_PATH}): {LUNG_CANCER_FEATURES}")
            except Exception as e:
                print(f"⚠️ Warning: Failed to read lung cancer dataset to infer features: {e}")
        else:
            print(f"⚠️ Warning: Lung cancer dataset not found at {LUNG_CANCER_DATA_PATH}; using fallback FEATURES list")

        print(f"Attempting to load Lung Cancer model from: {LUNG_CANCER_MODEL_PATH}")
        if os.path.exists(LUNG_CANCER_MODEL_PATH) and os.path.exists(LUNG_CANCER_LABEL_ENCODER_PATH):
            lung_cancer_model = joblib.load(LUNG_CANCER_MODEL_PATH)
            lung_cancer_label_encoder = joblib.load(LUNG_CANCER_LABEL_ENCODER_PATH)
            print("✅ Lung cancer model and label encoder loaded successfully.")

            # If the model exposes the feature names used during training, capture them
            try:
                if hasattr(lung_cancer_model, 'feature_names_in_'):
                    feature_names = list(getattr(lung_cancer_model, 'feature_names_in_'))
                    # normalize helper (same normalization used elsewhere)
                    def normalize(name: str) -> str:
                        return ''.join(name.lower().strip().split()).replace('_', '').replace('-', '')

                    MODEL_FEATURE_MAP = {normalize(n): n for n in feature_names}
                    MODEL_FEATURE_ORDER = feature_names
                    print(f"Detected model feature names: {feature_names}")
                else:
                    print("⚠️ Warning: lung_cancer_model has no 'feature_names_in_' attribute; fallback to dataset columns")
            except Exception as e:
                print(f"⚠️ Warning: Failed to inspect model feature names: {e}")
        else:
            print("❌ Lung cancer model or encoder file not found at the specified path.")
            return False

        print(f"Attempting to load Diabetes model from: {DIABETES_MODEL_PATH}")
        if os.path.exists(DIABETES_MODEL_PATH) and os.path.exists(DIABETES_LABEL_ENCODER_PATH):
            diabetes_model = joblib.load(DIABETES_MODEL_PATH)
            diabetes_label_encoder = joblib.load(DIABETES_LABEL_ENCODER_PATH)
            print("✅ Diabetes model and label encoder loaded successfully.")
        else:
            print("❌ Diabetes model or encoder file not found at the specified path.")
            return False

        print("✅ All models are ready!")
        return True

    except Exception as e:
        print(f"❌ An error occurred during model loading: {e}")
        return False

@app.route('/predict_lung_cancer', methods=['POST'])
def predict_lung_cancer():
    """Predict lung cancer risk based on user input."""
    if not all([lung_cancer_model, lung_cancer_label_encoder]):
        return jsonify({"error": "Lung cancer model is not loaded."}), 500

    # Add assertions to inform Pylance that models are not None
    assert lung_cancer_model is not None
    assert lung_cancer_label_encoder is not None

    try:
        # Get and validate input data
        user_data = request.get_json()
        print("Received data:", user_data)  # Debug print
        
        if not user_data:
            return jsonify({"error": "No input data provided."}), 400
        # Ensure we have inferred features from the dataset
        if not LUNG_CANCER_FEATURES:
            return jsonify({"error": "Lung cancer feature list is not available on the server."}), 500

        # Normalize helper (should match how we built LUNG_CANCER_COLUMN_MAP)
        def normalize(name: str) -> str:
            return ''.join(name.lower().strip().split()).replace('_', '').replace('-', '')

        # Build normalized input map for tolerant key matching
        normalized_input = {normalize(k): v for k, v in user_data.items()}

        # Map incoming values to the model's expected feature names using normalized matching.
        mapped = {}

        # Decide which feature order to use: prefer model's feature names when available
        if MODEL_FEATURE_ORDER:
            expected_features = MODEL_FEATURE_ORDER
        elif MODEL_FEATURE_MAP:
            expected_features = [MODEL_FEATURE_MAP[norm] for norm in MODEL_FEATURE_MAP]
        else:
            expected_features = LUNG_CANCER_FEATURES

        # Build normalized maps for matching
        def normalize_feature_name(name: str) -> str:
            return ''.join(name.lower().strip().split()).replace('_', '').replace('-', '')

        # normalized input already computed; normalized_input maps normalized_key -> value

        # Attempt to fill each expected feature from normalized input or exact user key
        for feat in expected_features:
            norm_feat = normalize_feature_name(feat)
            if norm_feat in normalized_input:
                mapped[feat] = normalized_input[norm_feat]
            elif feat in user_data:
                mapped[feat] = user_data[feat]
            else:
                # try to find any user input key that normalizes to this feature
                found = False
                for user_k, user_v in user_data.items():
                    if normalize_feature_name(user_k) == norm_feat:
                        mapped[feat] = user_v
                        found = True
                        break
                if not found:
                    mapped[feat] = None

        # Detect missing features
        missing_features = [col for col, val in mapped.items() if val is None]
        if missing_features:
            return jsonify({"error": f"Missing features: {missing_features}"}), 400

        # Create DataFrame in the model/training order
        input_df = pd.DataFrame([mapped], columns=expected_features)
        print("Mapped Input DataFrame before conversion:", input_df)

        # Convert all values to numeric
        for col in input_df.columns:
            input_df[col] = pd.to_numeric(input_df[col], errors='coerce')

        # Verify no null values after conversion
        if input_df.isnull().values.any():
            null_columns = input_df.columns[input_df.isnull().any()].tolist()
            return jsonify({"error": f"Invalid or non-numeric values in columns: {null_columns}"}), 400

        # Make prediction
        prediction_encoded = lung_cancer_model.predict(input_df)
        prediction_label = lung_cancer_label_encoder.inverse_transform(prediction_encoded)[0]
        
        # Calculate confidence
        probabilities = lung_cancer_model.predict_proba(input_df)[0]
        confidence = round(float(np.max(probabilities)) * 100, 2)

        return jsonify({
            "prediction": prediction_label,
            "confidence": confidence
        })

    except Exception as e:
        print(f"Error during prediction: {str(e)}")  # Debug print
        return jsonify({"error": f"Prediction failed: {str(e)}"}), 500

@app.route('/predict_diabetes', methods=['POST'])
def predict_diabetes():
    """Predict diabetes risk based on user input."""
    if not all([diabetes_model, diabetes_label_encoder]):
        return jsonify({"error": "Diabetes model is not loaded."}), 500

    # Add assertions to inform Pylance that models are not None
    assert diabetes_model is not None
    assert diabetes_label_encoder is not None

    try:
        user_data = request.get_json()
        if not user_data:
            return jsonify({"error": "No input data provided."}), 400

        # Create a copy to modify
        processed_data = user_data.copy()

        # Manual encoding for categorical features
        encoding_map = {'Yes': 1, 'No': 0, 'Male': 1, 'Female': 0}
        for feature, value in processed_data.items():
            if value in encoding_map:
                processed_data[feature] = encoding_map[value]

        # Create a DataFrame, ensuring correct feature order
        input_df = pd.DataFrame([processed_data])
        input_df = input_df[DIABETES_FEATURES] # Reorder/select columns to match model

        # Make prediction
        prediction_encoded = diabetes_model.predict(input_df)[0]
        prediction_label = "Positive" if prediction_encoded == 1 else "Negative"
        
        # Get confidence score
        probabilities = diabetes_model.predict_proba(input_df)[0]
        confidence = round(np.max(probabilities) * 100, 2)

        return jsonify({
            "prediction": prediction_label,
            "confidence": confidence
        })

    except KeyError as e:
        return jsonify({"error": f"Missing required feature in input data: {e}"}), 400
    except Exception as e:
        return jsonify({"error": f"Prediction failed: {str(e)}"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify model loading status."""
    return jsonify({
        'status': 'healthy',
        'lung_cancer_model_loaded': lung_cancer_model is not None,
        'diabetes_model_loaded': diabetes_model is not None
    })


@app.route('/model-info', methods=['GET'])
def model_info():
    """Return loaded model feature names and mappings for debugging."""
    return jsonify({
        'lung_cancer_features_from_dataset': LUNG_CANCER_FEATURES,
        'lung_cancer_column_map': LUNG_CANCER_COLUMN_MAP,
        'model_feature_order': MODEL_FEATURE_ORDER,
        'model_feature_map_normalized_to_actual': MODEL_FEATURE_MAP,
        'lung_cancer_model_loaded': lung_cancer_model is not None
    })

if __name__ == '__main__':
    print("🚀 Starting AI Health Predictor Backend...")
    
    if load_models():
        print("\n🌐 Starting Flask development server...")
        print("📡 API endpoints available at http://localhost:5000:")
        print("   - POST /predict_lung_cancer")
        print("   - POST /predict_diabetes")
        print("   - GET  /health")
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        print("\n❌ Critical error: Failed to load one or more models. Server will not start.")
