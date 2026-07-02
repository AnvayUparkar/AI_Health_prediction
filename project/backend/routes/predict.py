import os
import sys
import types
import traceback
from typing import Tuple, Any, Dict
from flask import Blueprint, request, jsonify, current_app
from backend.authorize_roles import authorize_roles
import joblib
import numpy as np
import pandas as pd
import pickle
import json

try:
    import xgboost as xgb
except ImportError:
    xgb = None

predict_bp = Blueprint('predict', __name__)

# Resolve repo root (two levels up from this file)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
LUNG_CANCER_MODEL_PATH = os.path.join(BASE_DIR, 'models', 'lung_cancer_model.pkl')
LUNG_CANCER_LABEL_ENCODER_PATH = os.path.join(BASE_DIR, 'models', 'lung_cancer_label_encoder.pkl')
DIABETES_MODEL_PATH = os.path.join(BASE_DIR, 'models', 'diabetes_model.pkl')
DIABETES_LABEL_ENCODER_PATH = os.path.join(BASE_DIR, 'models', 'diabetes_label_encoder.pkl')

HEART_XGB_PATH = os.path.join(BASE_DIR, 'models', 'saved_models', 'xgb_heart.json')
HEART_SCALER_PATH = os.path.join(BASE_DIR, 'models', 'saved_models', 'scaler.pkl')
HEART_CONFIG_PATH = os.path.join(BASE_DIR, 'models', 'saved_models', 'feature_columns.json')

lung_cancer_model = None
lung_cancer_label_encoder = None
lung_cancer_feature_names = None  # Store actual feature names from model
diabetes_model = None
diabetes_label_encoder = None

heart_xgb = None
heart_scaler = None
heart_threshold = 0.5
heart_features = []

# Define expected features for each model (fallback defaults)
DIABETES_FEATURES = [
    'HighBP', 'HighChol', 'CholCheck', 'BMI', 'Smoker', 'Stroke', 
    'HeartDiseaseorAttack', 'PhysActivity', 'Fruits', 'Veggies', 
    'HvyAlcoholConsump', 'AnyHealthcare', 'GenHlth', 'MentHlth', 
    'PhysHlth', 'DiffWalk', 'Sex', 'Age'
]

LUNG_CANCER_FEATURES = [
    'Gender', 'Age', 'Smoking', 'Yellow fingers', 'Anxiety',
    'Peer_pressure', 'Chronic Disease', 'Fatigue', 'Allergy',
    'Wheezing', 'Alcohol', 'Coughing', 'Shortness of Breath',
    'Swallowing Difficulty', 'Chest Pain'
]

def _inject_shim_for_module(module_name: str):
    """
    If a module required during unpickling is missing (e.g. '_loss'),
    inject a shim module into sys.modules.
    """
    if module_name in sys.modules:
        return
    shim = types.ModuleType(module_name)
    try:
        import tensorflow as _tf  # type: ignore
        from tensorflow.keras import losses as _k_losses  # type: ignore
        for name in ('binary_crossentropy', 'categorical_crossentropy', 'mean_squared_error', 'mse', 'mae'):
            if hasattr(_k_losses, name):
                setattr(shim, name, getattr(_k_losses, name))
        if hasattr(_k_losses, 'Loss'):
            setattr(shim, 'Loss', getattr(_k_losses, 'Loss'))
    except (ImportError, ModuleNotFoundError):
        # TensorFlow not installed - create dummy functions
        def _dummy(*args, **kwargs):
            raise RuntimeError(f"Dummy placeholder called from shim module '{module_name}'. Install TensorFlow if needed.")
        for name in ('binary_crossentropy', 'categorical_crossentropy', 'mean_squared_error', 'mse', 'mae', 'Loss'):
            setattr(shim, name, _dummy)
    sys.modules[module_name] = shim

def _safe_joblib_load(path: str):
    """
    Attempt joblib.load(path) with fallback for missing modules.
    """
    try:
        return joblib.load(path)
    except ModuleNotFoundError as mnfe:
        missing = getattr(mnfe, 'name', None)
        if not missing:
            msg = str(mnfe)
            if "No module named" in msg:
                missing = msg.split("No module named")[-1].strip().strip(" '\"")
        if missing and missing.startswith('_'):
            try:
                _inject_shim_for_module(missing)
                return joblib.load(path)
            except Exception:
                pass
        raise

def load_model_for_type(model_type: str):
    """
    Load models lazily based on requested type to save RAM on free tier (512MB limit).
    Unloads other models to prevent Out of Memory errors.
    """
    global lung_cancer_model, lung_cancer_label_encoder, lung_cancer_feature_names
    global diabetes_model, diabetes_label_encoder
    global heart_xgb, heart_scaler, heart_threshold, heart_features
    
    import gc
    
    print(f"Loading model for type: {model_type}...")
    
    if model_type == 'lung_cancer':
        # Unload others
        diabetes_model = None
        diabetes_label_encoder = None
        heart_xgb = None
        heart_scaler = None
        gc.collect()
        
        if lung_cancer_model is None:
            try:
                if os.path.exists(LUNG_CANCER_MODEL_PATH):
                    print(f"  Loading lung cancer model from {LUNG_CANCER_MODEL_PATH}")
                    lung_cancer_model = _safe_joblib_load(LUNG_CANCER_MODEL_PATH)
                    
                    if hasattr(lung_cancer_model, 'feature_names_in_'):
                        lung_cancer_feature_names = list(lung_cancer_model.feature_names_in_)
                    else:
                        lung_cancer_feature_names = LUNG_CANCER_FEATURES
                    
                    if lung_cancer_label_encoder is None and os.path.exists(LUNG_CANCER_LABEL_ENCODER_PATH):
                        lung_cancer_label_encoder = _safe_joblib_load(LUNG_CANCER_LABEL_ENCODER_PATH)
                        
                    print("  [OK] Lung cancer model loaded")
                else:
                    print(f"  [WARN] Lung cancer model not found: {LUNG_CANCER_MODEL_PATH}")
            except Exception as e:
                print(f"  [FAIL] Failed to load lung cancer model: {e}")
                
    elif model_type == 'diabetes':
        # Unload others
        lung_cancer_model = None
        lung_cancer_label_encoder = None
        heart_xgb = None
        heart_scaler = None
        gc.collect()
        
        if diabetes_model is None:
            try:
                if os.path.exists(DIABETES_MODEL_PATH):
                    print(f"  Loading diabetes model from {DIABETES_MODEL_PATH}")
                    diabetes_model = _safe_joblib_load(DIABETES_MODEL_PATH)
                    
                    if diabetes_label_encoder is None and os.path.exists(DIABETES_LABEL_ENCODER_PATH):
                        diabetes_label_encoder = _safe_joblib_load(DIABETES_LABEL_ENCODER_PATH)
                        
                    print("  [OK] Diabetes model loaded")
                else:
                    print(f"  [FAIL] Diabetes model not found: {DIABETES_MODEL_PATH}")
            except Exception as e:
                print(f"  [FAIL] Failed to load diabetes model: {e}")
                traceback.print_exc()
                
    elif model_type == 'heart_disease':
        # Unload others
        lung_cancer_model = None
        lung_cancer_label_encoder = None
        diabetes_model = None
        diabetes_label_encoder = None
        gc.collect()
        
        if heart_xgb is None and xgb is not None:
            try:
                required_files = [HEART_XGB_PATH, HEART_SCALER_PATH, HEART_CONFIG_PATH]
                if all(os.path.exists(p) for p in required_files):
                    print(f"  Loading heart disease models from {os.path.dirname(HEART_XGB_PATH)}")
                    heart_xgb = xgb.XGBClassifier()
                    heart_xgb.load_model(HEART_XGB_PATH)
                    heart_scaler = _safe_joblib_load(HEART_SCALER_PATH)
                    
                    with open(HEART_CONFIG_PATH, "r") as f:
                        config = json.load(f)
                        heart_threshold = config.get("threshold", 0.5)
                        heart_features = config.get("features", [])
                    
                    print(f"  [OK] Heart disease XGBoost model loaded")
                else:
                    print(f"  [FAIL] Heart disease models not found")
            except Exception as e:
                print(f"  [FAIL] Failed to load heart disease models: {e}")
                traceback.print_exc()

def _safe_predict(model, data):
    try:
        import eventlet
        from eventlet import tpool
        return tpool.execute(model.predict, data)
    except Exception:
        return model.predict(data)

def _safe_predict_proba(model, data):
    try:
        import eventlet
        from eventlet import tpool
        return tpool.execute(model.predict_proba, data)
    except Exception:
        return model.predict_proba(data)

def predict_with_type(prediction_type: str, features: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """
    Main prediction function that handles both diabetes and lung cancer predictions.
    """
    load_model_for_type(prediction_type)

    if prediction_type == 'lung_cancer':
        if not lung_cancer_model:
            return ({'error': 'Lung cancer model not available'}, 500)
        try:
            print(f"\n{'='*60}")
            print("LUNG CANCER PREDICTION REQUEST")
            print(f"{'='*60}")
            print(f"Received features: {features}")
            
            # Use actual feature names from model
            expected_features = lung_cancer_feature_names or LUNG_CANCER_FEATURES
            print(f"Expected features: {expected_features}")
            
            # Process the features
            processed = {}
            
            # Map received features to expected features (handle case and whitespace)
            for expected_feat in expected_features:
                # Try exact match first
                if expected_feat in features:
                    val = features[expected_feat]
                else:
                    # Try case-insensitive match
                    found = False
                    for k, v in features.items():
                        if k.strip().lower() == expected_feat.strip().lower():
                            val = v
                            found = True
                            break
                    if not found:
                        print(f"[WARN] Feature '{expected_feat}' not found in input, skipping")
                        continue
                
                # Convert to numeric
                if isinstance(val, str):
                    s = val.strip()
                    if s != '':
                        try:
                            processed[expected_feat] = float(s)
                        except Exception:
                            processed[expected_feat] = val
                else:
                    processed[expected_feat] = val
            
            print(f"Processed features: {processed}")
            
            # Create DataFrame with features
            input_df = pd.DataFrame([processed])
            
            # Check for missing features
            missing_features = [f for f in expected_features if f not in input_df.columns]
            if missing_features:
                print(f"[FAIL] Missing features: {missing_features}")
                return ({'error': f'Missing required features: {missing_features}'}, 400)
            
            # Reorder columns to match model training order
            input_df = input_df[expected_features]
            print(f"Input DataFrame shape: {input_df.shape}")
            print(f"Input DataFrame columns: {list(input_df.columns)}")
            print(f"Input DataFrame:\n{input_df}")
            
            # Make prediction
            pred_enc = _safe_predict(lung_cancer_model, input_df)
            
            # Decode prediction if encoder is available
            if lung_cancer_label_encoder is not None:
                try:
                    pred_label = lung_cancer_label_encoder.inverse_transform(pred_enc)[0]
                except Exception:
                    pred_label = str(pred_enc[0])
            else:
                pred_label = str(pred_enc[0])

            # Get confidence
            confidence = None
            if hasattr(lung_cancer_model, 'predict_proba'):
                try:
                    probs = _safe_predict_proba(lung_cancer_model, input_df)[0]
                    confidence = round(float(np.max(probs)) * 100, 2)
                except Exception as e:
                    print(f"Warning: Could not get confidence: {e}")
                    confidence = None

            result = {'prediction': pred_label, 'confidence': confidence}
            print(f"[OK] Prediction result: {result}")
            print(f"{'='*60}\n")
            
            return (result, 200)
        except Exception as e:
            print(f"[FAIL] Prediction error: {str(e)}")
            traceback.print_exc()
            return ({'error': f'Prediction error: {str(e)}'}, 500)

    elif prediction_type == 'heart_disease':
        if not heart_xgb:
            return ({'error': 'Heart disease model not available'}, 500)
        try:
            print(f"\n{'='*60}")
            print("HEART DISEASE PREDICTION REQUEST")
            print(f"{'='*60}")
            print(f"Received features: {features}")
            
            # 1. Processing and mapping (BRFSS standard)
            processed = {}
            for feat in heart_features:
                val = features.get(feat)
                if val is None:
                    # Try case-insensitive mapping
                    for k, v in features.items():
                        if k.strip().lower() == feat.lower():
                            val = v
                            break
                
                if val is not None:
                    try:
                        processed[feat] = float(val)
                    except (ValueError, TypeError):
                        # Mapping for common string values
                        mapping = {'Yes': 1.0, 'No': 0.0, 'Male': 1.0, 'Female': 0.0}
                        processed[feat] = mapping.get(val, 0.0)
                else:
                    processed[feat] = 0.0 # Default fallback
            
            print(f"Processed features: {processed}")
            
            # Create input array in correct order
            row_data = [processed.get(c, 0.0) for c in heart_features]
            row = np.array([row_data], dtype=np.float32)
            
            # Apply scaling
            if heart_scaler:
                row = heart_scaler.transform(row)
            
            # 2. Model inference
            probs = _safe_predict_proba(heart_xgb, row)
            prob = float(probs[0, 1])

            # 3. Decision
            pred_label = "Higher Risk" if prob >= heart_threshold else "Lower Risk"

            # Confidence calculation
            distance = abs(prob - heart_threshold)
            confidence = min(100.0, distance / max(float(heart_threshold), 1 - float(heart_threshold)) * 100)

            result = {
                'prediction': pred_label,
                'confidence': round(float(confidence), 1),
                'risk_score': round(float(prob) * 100, 1),
                'threshold': round(float(heart_threshold) * 100, 1)
            }
            print(f"[OK] Prediction result: {result}")
            print(f"{'='*60}\n")

            return (result, 200)
        except Exception as e:
            print(f"[FAIL] Prediction error: {str(e)}")
            traceback.print_exc()
            return ({'error': f'Prediction error: {str(e)}'}, 500)

    elif prediction_type == 'diabetes':
        if not diabetes_model:
            return ({'error': 'Diabetes model not available'}, 500)
        try:
            print(f"\n{'='*60}")
            print("DIABETES PREDICTION REQUEST (BRFSS 2015)")
            print(f"{'='*60}")
            print(f"Received features: {features}")
            
            # Process the features
            processed = {}
            for feat in DIABETES_FEATURES:
                val = features.get(feat)
                if val is None:
                    # Try case-insensitive mapping
                    for k, v in features.items():
                        if k.strip().lower() == feat.lower():
                            val = v
                            break
                
                if val is not None:
                    try:
                        processed[feat] = float(val)
                    except (ValueError, TypeError):
                        # Mapping for common string values if any
                        mapping = {'Yes': 1.0, 'No': 0.0, 'Male': 1.0, 'Female': 0.0}
                        processed[feat] = mapping.get(val, 0.0)
                else:
                    processed[feat] = 0.0 # Default fallback
            
            print(f"Processed features: {processed}")
            
            # Create DataFrame
            input_df = pd.DataFrame([processed])
            
            # Reorder columns to match DIABETES_FEATURES
            input_df = input_df[DIABETES_FEATURES]
            print(f"Input DataFrame shape: {input_df.shape}")
            
            # Make prediction
            pred_enc = _safe_predict(diabetes_model, input_df)
            pred_label = "Positive" if int(pred_enc[0]) == 1 else "Negative"
            
            # Get probability/confidence
            confidence = None
            risk_score = None
            if hasattr(diabetes_model, 'predict_proba'):
                try:
                    probs = _safe_predict_proba(diabetes_model, input_df)[0]
                    # Index 1 is usually the 'Positive' class in binary classification
                    risk_score = round(float(probs[1]) * 100, 2)
                    confidence = round(float(np.max(probs)) * 100, 2)
                except Exception as e:
                    print(f"Warning: Could not get probability: {e}")
            
            result = {
                'prediction': pred_label, 
                'confidence': confidence,
                'probability': risk_score if risk_score is not None else (100.0 if pred_label == 'Positive' else 0.0)
            }
            print(f"[OK] Prediction result: {result}")
            print(f"{'='*60}\n")
            
            return (result, 200)
        except Exception as e:
            print(f"[FAIL] Prediction error: {str(e)}")
            traceback.print_exc()
            return ({'error': f'Prediction error: {str(e)}'}, 500)

    else:
        return ({'error': f'Invalid prediction type: {prediction_type}'}, 400)


@predict_bp.route('/predict', methods=['OPTIONS', 'POST'])
@authorize_roles('doctor', 'nurse', 'user')
def predict():
    """
    Main prediction endpoint that handles both diabetes and lung cancer predictions.
    Expects JSON: {"type": "diabetes" | "lung_cancer", "features": {...}}
    """
    if request.method == 'OPTIONS':
        # Handle CORS preflight
        return '', 204
    
    try:
        data = request.get_json(silent=True) or {}
        print(f"\n[REQ] Received request data: {data}")
        
        prediction_type = (data.get('type') or '').lower()
        features = data.get('features') or {}
        
        if not prediction_type:
            return jsonify({'error': 'Missing prediction type'}), 400
        
        if not features:
            return jsonify({'error': 'Missing features'}), 400
        
        resp, status = predict_with_type(prediction_type, features)
        return jsonify(resp), status
    except Exception as e:
        print(f"[FAIL] Error in predict endpoint: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@predict_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for the prediction service."""
    return jsonify({
        'status': 'healthy',
        'lung_cancer_model_loaded': lung_cancer_model is not None,
        'diabetes_model_loaded': diabetes_model is not None,
        'heart_disease_model_loaded': heart_xgb is not None
    })


@predict_bp.route('/model-info', methods=['GET'])
def model_info():
    """Returns information about loaded models and their expected features."""
    # Use actual feature names from model if available
    lc_features = lung_cancer_feature_names if lung_cancer_feature_names else LUNG_CANCER_FEATURES
    
    return jsonify({
        'lung_cancer_model_loaded': lung_cancer_model is not None,
        'diabetes_model_loaded': diabetes_model is not None,
        'heart_disease_model_loaded': heart_xgb is not None,
        'lung_cancer_features': lc_features,
        'diabetes_features': DIABETES_FEATURES,
        'heart_disease_features': heart_features
    })