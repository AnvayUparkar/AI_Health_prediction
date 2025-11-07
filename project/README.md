# AI Health Predictor - Flask Backend

A Flask-based REST API server for healthcare prediction using machine learning models. This backend provides endpoints for lung cancer and diabetes risk prediction.

## Features

- **Lung Cancer Prediction**: Analyzes 12 user inputs and fills missing features with mean values for accurate prediction
- **Diabetes Prediction**: Processes 16 health indicators to predict diabetes risk
- **Model Loading**: Automatically loads pre-trained models on server startup
- **Error Handling**: Comprehensive error handling with meaningful error messages
- **CORS Support**: Cross-origin resource sharing enabled for frontend integration

## Prerequisites

- Python 3.8 or higher
- Pre-trained machine learning models (see Model Files section)

## Installation

1. **Clone or download the project files**

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Prepare model files**:
   Create a `models` directory in the project root and place your pre-trained models:
   ```
   models/
   ├── lung_cancer_model.pkl
   ├── lung_cancer_label_encoder.pkl
   └── diabetes_model.pkl
   ```

## Running the Server

Start the Flask development server:
```bash
python app.py
```

The server will start on `http://localhost:5000` with the following endpoints:

- `POST /predict_lung_cancer` - Lung cancer risk prediction
- `POST /predict_diabetes` - Diabetes risk prediction  
- `GET /health` - Health check endpoint

## API Endpoints

### 1. Lung Cancer Prediction

**Endpoint**: `POST /predict_lung_cancer`

**Request Body** (JSON):
```json
{
  "Age": 55,
  "Gender": "1",
  "Alcohol use": "4",
  "Dust Allergy": "3",
  "OccuPational Hazards": "5",
  "Genetic Risk": "2",
  "chronic Lung Disease": "1",
  "Balanced Diet": "6",
  "Obesity": "3",
  "Smoking": "7",
  "Passive Smoker": "2",
  "Coughing of Blood": "1"
}
```

**Response**:
```json
{
  "prediction": "High",
  "confidence": "94.23"
}
```

### 2. Diabetes Prediction

**Endpoint**: `POST /predict_diabetes`

**Request Body** (JSON):
```json
{
  "Age": 45,
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
```

**Response**:
```json
{
  "prediction": "Positive",
  "confidence": "87.45"
}
```

### 3. Health Check

**Endpoint**: `GET /health`

**Response**:
```json
{
  "status": "healthy",
  "models_loaded": true,
  "endpoints": {
    "lung_cancer": "/predict_lung_cancer (POST)",
    "diabetes": "/predict_diabetes (POST)",
    "health": "/health (GET)"
  }
}
```

## Model Files

The backend expects the following model files in the `models/` directory:

1. **lung_cancer_model.pkl** - Pre-trained lung cancer prediction model
2. **lung_cancer_label_encoder.pkl** - Label encoder for lung cancer predictions
3. **diabetes_model.pkl** - Pre-trained diabetes prediction model

### Model Requirements

- **Lung Cancer Model**: Should be trained on 23 features in the specified order
- **Label Encoder**: Should encode risk levels (e.g., "Low", "Medium", "High")
- **Diabetes Model**: Should predict binary outcomes (0 for Negative, 1 for Positive)

## Data Preprocessing

### Lung Cancer Features
The backend automatically handles missing features by filling them with mean values calculated from the training dataset. The complete feature list includes:

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

### Diabetes Features
All 16 features are required for diabetes prediction:

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

## Error Handling

The API returns appropriate HTTP status codes and error messages:

- **400 Bad Request**: Invalid or missing data
- **500 Internal Server Error**: Model loading or prediction errors

Error response format:
```json
{
  "error": "Description of the error"
}
```

## Frontend Integration

To connect your React frontend to this backend:

1. **Update API calls** in your frontend components to use the actual endpoints
2. **Replace mock data** with real API calls
3. **Handle loading states** and error responses

Example frontend API call:
```javascript
const response = await fetch('http://localhost:5000/predict_lung_cancer', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify(formData)
});

const result = await response.json();
```

## Development

### Project Structure
```
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── models/               # Model files directory
│   ├── lung_cancer_model.pkl
│   ├── lung_cancer_label_encoder.pkl
│   └── diabetes_model.pkl
└── frontend/             # Your React frontend
```

### Environment Variables
For production deployment, consider setting:
- `FLASK_ENV=production`
- `FLASK_DEBUG=False`
- Custom port via `PORT` environment variable

## Troubleshooting

### Common Issues

1. **Models not found**: Ensure all model files are in the `models/` directory
2. **Import errors**: Install all dependencies with `pip install -r requirements.txt`
3. **CORS errors**: The backend includes CORS support, but check frontend URL configuration
4. **Port conflicts**: Change the port in `app.py` if 5000 is already in use

### Debug Mode
The server runs in debug mode by default. For production, set `debug=False` in `app.run()`.

## License

This project is for educational purposes. Please ensure compliance with healthcare data regulations in your jurisdiction.

## Disclaimer

This tool is for educational purposes only and is not a substitute for professional medical advice. Always consult healthcare professionals for medical decisions.
