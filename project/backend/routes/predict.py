import os
import sys
import types
import traceback
from typing import Tuple, Any, Dict
from flask import Blueprint, request, jsonify, current_app
import joblib
import numpy as np
import pandas as pd

predict_bp = Blueprint('predict', __name__)

# Resolve repo root (two levels up from this file)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
LUNG_CANCER_MODEL_PATH = os.path.join(BASE_DIR, 'models', 'lung_cancer_model.pkl')
LUNG_CANCER_LABEL_ENCODER_PATH = os.path.join(BASE_DIR, 'models', 'lung_cancer_label_encoder.pkl')
DIABETES_MODEL_PATH = os.path.join(BASE_DIR, 'models', 'diabetes_model.pkl')
DIABETES_LABEL_ENCODER_PATH = os.path.join(BASE_DIR, 'models', 'diabetes_label_encoder.pkl')

lung_cancer_model = None
lung_cancer_label_encoder = None
lung_cancer_feature_names = None  # Store actual feature names from model
diabetes_model = None
diabetes_label_encoder = None

# Define expected features for each model (fallback defaults)
DIABETES_FEATURES = [
    'Age', 'Gender', 'Polyuria', 'Polydipsia', 'sudden weight loss', 
    'weakness', 'Polyphagia', 'Genital thrush', 'visual blurring', 
    'Itching', 'Irritability', 'delayed healing', 'partial paresis', 
    'muscle stiffness', 'Alopecia', 'Obesity'
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

def load_models_once():
    """
    Load models lazily. Safe to call inside a request context.
    Each model loads independently - if one fails, others can still work.
    """
    global lung_cancer_model, lung_cancer_label_encoder, lung_cancer_feature_names
    global diabetes_model, diabetes_label_encoder
    
    print("Loading models...")
    models_loaded = []
    models_failed = []
    
    # Try to load lung cancer model (non-critical)
    if lung_cancer_model is None:
        try:
            if os.path.exists(LUNG_CANCER_MODEL_PATH):
                print(f"  Loading lung cancer model from {LUNG_CANCER_MODEL_PATH}")
                lung_cancer_model = _safe_joblib_load(LUNG_CANCER_MODEL_PATH)
                
                # CRITICAL FIX: Extract actual feature names from the model
                if hasattr(lung_cancer_model, 'feature_names_in_'):
                    lung_cancer_feature_names = list(lung_cancer_model.feature_names_in_)
                    print(f"  ✓ Extracted feature names from model: {lung_cancer_feature_names}")
                else:
                    lung_cancer_feature_names = LUNG_CANCER_FEATURES
                    print(f"  ⚠ Model has no feature_names_in_, using defaults")
                
                print("  ✓ Lung cancer model loaded")
                models_loaded.append("lung_cancer_model")
            else:
                print(f"  ⚠ Lung cancer model not found: {LUNG_CANCER_MODEL_PATH}")
                models_failed.append("lung_cancer_model (not found)")
        except Exception as e:
            print(f"  ✗ Failed to load lung cancer model: {e}")
            models_failed.append(f"lung_cancer_model ({str(e)[:50]})")
    
    # Try to load lung cancer encoder (non-critical)
    if lung_cancer_label_encoder is None:
        try:
            if os.path.exists(LUNG_CANCER_LABEL_ENCODER_PATH):
                print(f"  Loading lung cancer encoder from {LUNG_CANCER_LABEL_ENCODER_PATH}")
                lung_cancer_label_encoder = _safe_joblib_load(LUNG_CANCER_LABEL_ENCODER_PATH)
                print("  ✓ Lung cancer encoder loaded")
                models_loaded.append("lung_cancer_encoder")
        except Exception as e:
            print(f"  ✗ Failed to load lung cancer encoder: {e}")
            models_failed.append(f"lung_cancer_encoder ({str(e)[:50]})")
    
    # Try to load diabetes model (critical)
    if diabetes_model is None:
        try:
            if os.path.exists(DIABETES_MODEL_PATH):
                print(f"  Loading diabetes model from {DIABETES_MODEL_PATH}")
                diabetes_model = _safe_joblib_load(DIABETES_MODEL_PATH)
                print("  ✓ Diabetes model loaded")
                models_loaded.append("diabetes_model")
            else:
                error_msg = f"Diabetes model not found: {DIABETES_MODEL_PATH}"
                print(f"  ✗ {error_msg}")
                models_failed.append("diabetes_model (not found)")
        except Exception as e:
            print(f"  ✗ Failed to load diabetes model: {e}")
            traceback.print_exc()
            models_failed.append(f"diabetes_model ({str(e)[:50]})")
    
    # Try to load diabetes encoder (optional)
    if diabetes_label_encoder is None:
        try:
            if os.path.exists(DIABETES_LABEL_ENCODER_PATH):
                print(f"  Loading diabetes encoder from {DIABETES_LABEL_ENCODER_PATH}")
                diabetes_label_encoder = _safe_joblib_load(DIABETES_LABEL_ENCODER_PATH)
                print("  ✓ Diabetes encoder loaded")
                models_loaded.append("diabetes_encoder")
        except Exception as e:
            print(f"  ⚠ Failed to load diabetes encoder (optional): {e}")
            models_failed.append(f"diabetes_encoder ({str(e)[:50]})")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"✓ Models loaded successfully: {', '.join(models_loaded) if models_loaded else 'None'}")
    if models_failed:
        print(f"✗ Models failed to load: {', '.join(models_failed)}")
    print(f"{'='*60}\n")

def predict_with_type(prediction_type: str, features: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """
    Main prediction function that handles both diabetes and lung cancer predictions.
    """
    load_models_once()

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
                        print(f"⚠ Feature '{expected_feat}' not found in input, skipping")
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
                print(f"✗ Missing features: {missing_features}")
                return ({'error': f'Missing required features: {missing_features}'}, 400)
            
            # Reorder columns to match model training order
            input_df = input_df[expected_features]
            print(f"Input DataFrame shape: {input_df.shape}")
            print(f"Input DataFrame columns: {list(input_df.columns)}")
            print(f"Input DataFrame:\n{input_df}")
            
            # Make prediction
            pred_enc = lung_cancer_model.predict(input_df)
            
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
                    probs = lung_cancer_model.predict_proba(input_df)[0]
                    confidence = round(float(np.max(probs)) * 100, 2)
                except Exception as e:
                    print(f"Warning: Could not get confidence: {e}")
                    confidence = None

            result = {'prediction': pred_label, 'confidence': confidence}
            print(f"✓ Prediction result: {result}")
            print(f"{'='*60}\n")
            
            return (result, 200)
        except Exception as e:
            print(f"✗ Prediction error: {str(e)}")
            traceback.print_exc()
            return ({'error': f'Prediction error: {str(e)}'}, 500)

    elif prediction_type == 'diabetes':
        if not diabetes_model:
            return ({'error': 'Diabetes model not available'}, 500)
        try:
            print(f"\n{'='*60}")
            print("DIABETES PREDICTION REQUEST")
            print(f"{'='*60}")
            print(f"Received features: {features}")
            
            # Process the features
            processed = dict(features)
            mapping = {'Yes': 1, 'No': 0, 'Male': 1, 'Female': 0}
            
            for k, v in list(processed.items()):
                if isinstance(v, str):
                    if v in mapping:
                        processed[k] = mapping[v]
                    else:
                        s = v.strip()
                        try:
                            processed[k] = float(s) if s != '' else v
                        except Exception:
                            processed[k] = v
            
            print(f"Processed features: {processed}")
            
            # Create DataFrame with features in correct order
            input_df = pd.DataFrame([processed])
            
            # Ensure we have all required features
            missing_features = [f for f in DIABETES_FEATURES if f not in input_df.columns]
            if missing_features:
                print(f"✗ Missing features: {missing_features}")
                return ({'error': f'Missing required features: {missing_features}'}, 400)
            
            # Reorder columns to match training
            input_df = input_df[DIABETES_FEATURES]
            print(f"Input DataFrame shape: {input_df.shape}")
            print(f"Input DataFrame:\n{input_df}")
            
            # Make prediction
            pred_enc = diabetes_model.predict(input_df)
            pred_label = "Positive" if int(pred_enc[0]) == 1 else "Negative"
            
            # Get confidence
            confidence = None
            if hasattr(diabetes_model, 'predict_proba'):
                try:
                    probs = diabetes_model.predict_proba(input_df)[0]
                    confidence = round(float(np.max(probs)) * 100, 2)
                except Exception as e:
                    print(f"Warning: Could not get confidence: {e}")
                    confidence = None
            
            result = {'prediction': pred_label, 'confidence': confidence}
            print(f"✓ Prediction result: {result}")
            print(f"{'='*60}\n")
            
            return (result, 200)
        except Exception as e:
            print(f"✗ Prediction error: {str(e)}")
            traceback.print_exc()
            return ({'error': f'Prediction error: {str(e)}'}, 500)

    else:
        return ({'error': f'Invalid prediction type: {prediction_type}'}, 400)


@predict_bp.route('/predict', methods=['OPTIONS', 'POST'])
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
        print(f"\n📨 Received request data: {data}")
        
        prediction_type = (data.get('type') or '').lower()
        features = data.get('features') or {}
        
        if not prediction_type:
            return jsonify({'error': 'Missing prediction type'}), 400
        
        if not features:
            return jsonify({'error': 'Missing features'}), 400
        
        resp, status = predict_with_type(prediction_type, features)
        return jsonify(resp), status
    except Exception as e:
        print(f"✗ Error in predict endpoint: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@predict_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for the prediction service."""
    return jsonify({
        'status': 'healthy',
        'lung_cancer_model_loaded': lung_cancer_model is not None,
        'diabetes_model_loaded': diabetes_model is not None
    })


@predict_bp.route('/model-info', methods=['GET'])
def model_info():
    """Returns information about loaded models and their expected features."""
    # Use actual feature names from model if available
    lc_features = lung_cancer_feature_names if lung_cancer_feature_names else LUNG_CANCER_FEATURES
    
    return jsonify({
        'lung_cancer_model_loaded': lung_cancer_model is not None,
        'diabetes_model_loaded': diabetes_model is not None,
        'lung_cancer_features': lc_features,
        'diabetes_features': DIABETES_FEATURES
    })