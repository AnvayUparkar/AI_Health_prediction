import sys
import os

sys.path.insert(0, r"c:\Users\Anvay Uparkar\Hackathon projects\AI_Health_prediction\project")

from backend.routes.predict import predict_with_type
print("Imported successfully!")

features = {
    "Age": "45",
    "Gender": "Male",
    "Polyuria": "Yes",
    "Polydipsia": "Yes",
    "sudden weight loss": "No",
    "weakness": "Yes",
    "Polyphagia": "No",
    "Genital thrush": "No",
    "visual blurring": "Yes",
    "Itching": "No",
    "Irritability": "No",
    "delayed healing": "Yes",
    "partial paresis": "No",
    "muscle stiffness": "No",
    "Alopecia": "No",
    "Obesity": "Yes"
}

print("Running predict_with_type...")
res, code = predict_with_type('diabetes', features)
print(f"Result: {res}, Code: {code}")
