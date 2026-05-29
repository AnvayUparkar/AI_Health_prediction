import joblib
import pandas as pd
import numpy as np
import os

model_path = r"c:\Users\Anvay Uparkar\Hackathon projects\AI_Health_prediction\project\models\diabetes_model.pkl"
print(f"Checking model at: {model_path}")
print(f"File exists: {os.path.exists(model_path)}")

if os.path.exists(model_path):
    try:
        model = joblib.load(model_path)
        print("Model loaded successfully!")
        print(f"Model type: {type(model)}")
        if hasattr(model, "n_features_in_"):
            print(f"Number of features in: {model.n_features_in_}")
        if hasattr(model, "feature_names_in_"):
            print(f"Feature names in: {model.feature_names_in_}")
        else:
            print("Model does not have feature_names_in_ attribute.")
        
        # If it's a random forest or gradient boosting, check its estimators
        if hasattr(model, "estimators_"):
            print(f"Number of estimators: {len(model.estimators_)}")
            # Try to see if we can get feature names by passing dummy data
            # let's try a dummy prediction with 16 features
            try:
                dummy_16 = np.zeros((1, 16))
                pred_16 = model.predict(dummy_16)
                print(f"16 features dummy prediction: {pred_16} (SUCCESS)")
            except Exception as e16:
                print(f"16 features dummy prediction: FAILED with {e16}")
                
            # let's try a dummy prediction with 18 features
            try:
                dummy_18 = np.zeros((1, 18))
                pred_18 = model.predict(dummy_18)
                print(f"18 features dummy prediction: {pred_18} (SUCCESS)")
            except Exception as e18:
                print(f"18 features dummy prediction: FAILED with {e18}")
    except Exception as e:
        print(f"Error loading model: {e}")
