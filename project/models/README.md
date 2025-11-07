# Model Files Directory

This directory should contain your pre-trained machine learning models for the AI Health Predictor backend.

## Required Files

Place the following files in this directory:

1. **lung_cancer_model.pkl** - Pre-trained lung cancer prediction model
2. **lung_cancer_label_encoder.pkl** - Label encoder for lung cancer predictions  
3. **diabetes_model.pkl** - Pre-trained diabetes prediction model

## Model Requirements

### Lung Cancer Model (lung_cancer_model.pkl)
- **Type**: Scikit-learn classifier (RandomForest, SVM, etc.)
- **Features**: 23 features in the exact order specified in app.py
- **Output**: Numeric predictions (0, 1, 2, etc.) that will be decoded by the label encoder
- **Methods required**: `.predict()` and `.predict_proba()`

### Lung Cancer Label Encoder (lung_cancer_label_encoder.pkl)
- **Type**: Scikit-learn LabelEncoder
- **Purpose**: Converts numeric predictions back to text labels (e.g., "Low", "Medium", "High")
- **Methods required**: `.inverse_transform()`

### Diabetes Model (diabetes_model.pkl)
- **Type**: Scikit-learn classifier
- **Features**: 16 features in the exact order specified in app.py
- **Output**: Binary predictions (0 for "Negative", 1 for "Positive")
- **Methods required**: `.predict()` and `.predict_proba()`

## Feature Order

### Lung Cancer Features (23 total)
1. Age
2. Gender
3. Air Pollution
4. Alcohol use
5. Dust Allergy
6. OccuPational Hazards
7. Genetic Risk
8. chronic Lung Disease
9. Balanced Diet
10. Obesity
11. Smoking
12. Passive Smoker
13. Chest Pain
14. Coughing of Blood
15. Fatigue
16. Weight Loss
17. Shortness of Breath
18. Wheezing
19. Swallowing Difficulty
20. Clubbing of Finger Nails
21. Frequent Cold
22. Dry Cough
23. Snoring

### Diabetes Features (16 total)
1. Age
2. Gender
3. Polyuria
4. Polydipsia
5. sudden weight loss
6. weakness
7. Polyphagia
8. Genital thrush
9. visual blurring
10. Itching
11. Irritability
12. delayed healing
13. partial paresis
14. muscle stiffness
15. Alopecia
16. Obesity

## Creating Models

If you need to create these models, here's a basic example:

```python
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split

# Load your training data
# data = pd.read_csv('your_training_data.csv')

# For lung cancer model
lung_features = ['Age', 'Gender', 'Air Pollution', 'Alcohol use', 'Dust Allergy', 
                'OccuPational Hazards', 'Genetic Risk', 'chronic Lung Disease', 
                'Balanced Diet', 'Obesity', 'Smoking', 'Passive Smoker', 
                'Chest Pain', 'Coughing of Blood', 'Fatigue', 'Weight Loss', 
                'Shortness of Breath', 'Wheezing', 'Swallowing Difficulty', 
                'Clubbing of Finger Nails', 'Frequent Cold', 'Dry Cough', 'Snoring']

# X_lung = data[lung_features]
# y_lung = data['Lung_Cancer_Risk']  # Your target variable

# Create and train lung cancer model
lung_model = RandomForestClassifier(random_state=42)
# lung_model.fit(X_lung, y_lung)

# Create and fit label encoder
lung_encoder = LabelEncoder()
# lung_encoder.fit(y_lung)

# For diabetes model
diabetes_features = ['Age', 'Gender', 'Polyuria', 'Polydipsia', 'sudden weight loss', 
                    'weakness', 'Polyphagia', 'Genital thrush', 'visual blurring', 
                    'Itching', 'Irritability', 'delayed healing', 'partial paresis', 
                    'muscle stiffness', 'Alopecia', 'Obesity']

# X_diabetes = data[diabetes_features]
# y_diabetes = data['Diabetes']  # Your target variable

# Create and train diabetes model
diabetes_model = RandomForestClassifier(random_state=42)
# diabetes_model.fit(X_diabetes, y_diabetes)

# Save models
# joblib.dump(lung_model, 'lung_cancer_model.pkl')
# joblib.dump(lung_encoder, 'lung_cancer_label_encoder.pkl')
# joblib.dump(diabetes_model, 'diabetes_model.pkl')
```

## Testing Models

You can test your models before placing them in this directory:

```python
import joblib
import pandas as pd

# Load models
lung_model = joblib.load('lung_cancer_model.pkl')
lung_encoder = joblib.load('lung_cancer_label_encoder.pkl')
diabetes_model = joblib.load('diabetes_model.pkl')

# Test lung cancer prediction
test_lung_data = pd.DataFrame([{
    'Age': 55, 'Gender': 1, 'Alcohol use': 4, 'Dust Allergy': 3,
    'OccuPational Hazards': 5, 'Genetic Risk': 2, 'chronic Lung Disease': 1,
    'Balanced Diet': 6, 'Obesity': 3, 'Smoking': 7, 'Passive Smoker': 2,
    'Coughing of Blood': 1
}])

prediction = lung_model.predict(test_lung_data)[0]
label = lung_encoder.inverse_transform([prediction])[0]
print(f"Lung Cancer Risk: {label}")

# Test diabetes prediction
test_diabetes_data = pd.DataFrame([{
    'Age': 45, 'Gender': 1, 'Polyuria': 1, 'Polydipsia': 1,
    'sudden weight loss': 0, 'weakness': 1, 'Polyphagia': 0,
    'Genital thrush': 0, 'visual blurring': 1, 'Itching': 0,
    'Irritability': 0, 'delayed healing': 1, 'partial paresis': 0,
    'muscle stiffness': 0, 'Alopecia': 0, 'Obesity': 1
}])

prediction = diabetes_model.predict(test_diabetes_data)[0]
label = "Positive" if prediction == 1 else "Negative"
print(f"Diabetes Risk: {label}")
```

## Important Notes

- Ensure your models are compatible with the scikit-learn version specified in requirements.txt
- Test your models thoroughly before deployment
- Keep backup copies of your trained models
- Update the mean values in app.py if you retrain your models with different data
