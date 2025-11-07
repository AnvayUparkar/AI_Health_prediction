# AI Health Predictor - Complete Setup Guide

This guide will walk you through setting up and running the complete AI Health Predictor project with both the React frontend and Flask backend.

## 📋 Prerequisites

- **Python 3.8+** installed on your system
- **Node.js 16+** and npm installed on your system
- **Pre-trained machine learning models** (see Model Requirements section)

## 🚀 Quick Start

### Option 1: Automated Setup (Recommended)

1. **Start the backend**:
   ```bash
   python start_backend.py
   ```

2. **Start the frontend** (in a new terminal):
   ```bash
   npm install
   npm run dev
   ```

3. **Test the backend** (optional):
   ```bash
   python test_backend.py
   ```

### Option 2: Manual Setup

Follow the detailed steps below if you prefer manual setup or encounter issues.

## 📦 Backend Setup

### Step 1: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Prepare Model Files

Create a `models` directory and place your pre-trained models:

```
models/
├── lung_cancer_model.pkl
├── lung_cancer_label_encoder.pkl
└── diabetes_model.pkl
```

**Model Requirements**:
- **lung_cancer_model.pkl**: Scikit-learn classifier trained on 23 features
- **lung_cancer_label_encoder.pkl**: LabelEncoder for converting predictions to text labels
- **diabetes_model.pkl**: Scikit-learn classifier trained on 16 features

For detailed model specifications, see `models/README.md`.

### Step 3: Start the Flask Backend

```bash
python app.py
```

The server will start on `http://localhost:5000` with these endpoints:
- `POST /predict_lung_cancer` - Lung cancer risk prediction
- `POST /predict_diabetes` - Diabetes risk prediction
- `GET /health` - Health check endpoint

### Step 4: Test the Backend

```bash
python test_backend.py
```

This will test all endpoints and verify everything is working correctly.

## 🎨 Frontend Setup

### Step 1: Install Node.js Dependencies

```bash
npm install
```

### Step 2: Start the Development Server

```bash
npm run dev
```

The frontend will be available at `http://localhost:5173` (or the next available port).

## 🔗 Connecting Frontend to Backend

The frontend has already been updated to connect to the Flask backend. The connection is configured in:

- `src/pages/LungCancer.tsx` - Connects to `/predict_lung_cancer`
- `src/pages/Diabetes.tsx` - Connects to `/predict_diabetes`

Both components will automatically send form data to the backend and display the prediction results.

## 📊 API Endpoints

### Lung Cancer Prediction

**Endpoint**: `POST http://localhost:5000/predict_lung_cancer`

**Request Body**:
```json
{
  "Age": "55",
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

### Diabetes Prediction

**Endpoint**: `POST http://localhost:5000/predict_diabetes`

**Request Body**:
```json
{
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
```

**Response**:
```json
{
  "prediction": "Positive",
  "confidence": "87.45"
}
```

## 🧪 Testing

### Backend Testing

Run the comprehensive test suite:
```bash
python test_backend.py
```

This will test:
- Health check endpoint
- Lung cancer prediction endpoint
- Diabetes prediction endpoint

### Frontend Testing

The frontend includes built-in testing. Run:
```bash
npm test
```

## 🐛 Troubleshooting

### Common Issues

#### 1. Backend Won't Start

**Error**: "Models not loaded. Please restart the server."

**Solution**: 
- Ensure all model files are in the `models/` directory
- Check that model files have the correct format
- Verify file permissions

#### 2. Frontend Can't Connect to Backend

**Error**: "Prediction failed. Please try again or check if the backend server is running."

**Solution**:
- Ensure the Flask server is running on `http://localhost:5000`
- Check for CORS issues (should be handled automatically)
- Verify the backend URL in the frontend code

#### 3. Import Errors

**Error**: "ModuleNotFoundError: No module named 'flask'"

**Solution**:
```bash
pip install -r requirements.txt
```

#### 4. Port Conflicts

**Error**: "Address already in use"

**Solution**:
- Change the port in `app.py` (line 280)
- Or kill the process using the port:
  ```bash
  # Windows
  netstat -ano | findstr :5000
  taskkill /PID <PID> /F
  
  # Mac/Linux
  lsof -ti:5000 | xargs kill -9
  ```

### Debug Mode

The Flask server runs in debug mode by default. For production:

1. Set `debug=False` in `app.py`
2. Use a production WSGI server like Gunicorn
3. Set environment variables for production

## 📁 Project Structure

```
project/
├── app.py                    # Flask backend application
├── requirements.txt          # Python dependencies
├── start_backend.py         # Automated backend startup
├── test_backend.py          # Backend testing script
├── README.md                # Main documentation
├── SETUP_GUIDE.md           # This setup guide
├── models/                  # Model files directory
│   ├── README.md           # Model specifications
│   ├── lung_cancer_model.pkl
│   ├── lung_cancer_label_encoder.pkl
│   └── diabetes_model.pkl
└── src/                     # React frontend
    ├── pages/
    │   ├── LungCancer.tsx   # Lung cancer prediction page
    │   └── Diabetes.tsx     # Diabetes prediction page
    └── components/          # React components
```

## 🔧 Development

### Adding New Features

1. **Backend**: Add new endpoints in `app.py`
2. **Frontend**: Create new components in `src/components/`
3. **Testing**: Update `test_backend.py` for new endpoints

### Environment Variables

For production deployment, consider setting:
- `FLASK_ENV=production`
- `FLASK_DEBUG=False`
- `PORT=5000` (or your preferred port)

## 📝 Notes

- The backend automatically fills missing lung cancer features with mean values
- All predictions include confidence scores
- Error handling is implemented for both frontend and backend
- CORS is enabled for local development
- The frontend uses modern React with TypeScript

## 🆘 Getting Help

If you encounter issues:

1. Check the troubleshooting section above
2. Run the test scripts to identify specific problems
3. Check the console logs in both frontend and backend
4. Verify all dependencies are installed correctly

## 📄 License

This project is for educational purposes. Please ensure compliance with healthcare data regulations in your jurisdiction.

## ⚠️ Disclaimer

This tool is for educational purposes only and is not a substitute for professional medical advice. Always consult healthcare professionals for medical decisions.
