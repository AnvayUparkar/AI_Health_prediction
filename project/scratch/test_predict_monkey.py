import eventlet
eventlet.monkey_patch()

import sys
sys.path.insert(0, r"c:\Users\Anvay Uparkar\Hackathon projects\AI_Health_prediction\project")

from backend.routes.predict import predict_with_type
print("Imported predict_with_type successfully!")

features = {
    "HighBP": "1",
    "HighChol": "1",
    "CholCheck": "1",
    "BMI": "28",
    "Smoker": "1",
    "Stroke": "0",
    "HeartDiseaseorAttack": "0",
    "PhysActivity": "1",
    "Fruits": "1",
    "Veggies": "1",
    "HvyAlcoholConsump": "0",
    "AnyHealthcare": "1",
    "GenHlth": "3",
    "MentHlth": "2",
    "PhysHlth": "0",
    "DiffWalk": "0",
    "Sex": "1",
    "Age": "5"
}

print("Running predict_with_type for lung_cancer...")
res, code = predict_with_type('lung_cancer', {
    "Gender": "1",
    "Age": "55",
    "Smoking": "2",
    "Yellow fingers": "1",
    "Anxiety": "2",
    "Peer_pressure": "1",
    "Chronic Disease": "2",
    "Fatigue ": "2",
    "Allergy ": "1",
    "Wheezing": "2",
    "Alcohol": "1",
    "Coughing": "2",
    "Shortness of Breath": "2",
    "Swallowing Difficulty": "1",
    "Chest Pain": "2"
})
print(f"Lung cancer result: {res}, Code: {code}")

print("Running predict_with_type for diabetes...")
res, code = predict_with_type('diabetes', features)
print(f"Diabetes result: {res}, Code: {code}")
