import eventlet
eventlet.monkey_patch(thread=False)

import sys
sys.path.insert(0, r"c:\Users\Anvay Uparkar\Hackathon projects\AI_Health_prediction\project")

import joblib
import pandas as pd
import numpy as np

diabetes_model = joblib.load(r"c:\Users\Anvay Uparkar\Hackathon projects\AI_Health_prediction\project\models\diabetes_model.pkl")
print("Model loaded!")

features = {
    'HighBP': 1.0, 'HighChol': 1.0, 'CholCheck': 1.0, 'BMI': 28.0, 'Smoker': 1.0, 'Stroke': 0.0,
    'HeartDiseaseorAttack': 0.0, 'PhysActivity': 1.0, 'Fruits': 1.0, 'Veggies': 1.0,
    'HvyAlcoholConsump': 0.0, 'AnyHealthcare': 1.0, 'GenHlth': 3.0, 'MentHlth': 2.0,
    'PhysHlth': 0.0, 'DiffWalk': 0.0, 'Sex': 1.0, 'Age': 5.0
}
input_df = pd.DataFrame([features])

print("Predicting...")
res = diabetes_model.predict(input_df)
print(f"Prediction: {res}")
