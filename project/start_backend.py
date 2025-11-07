#!/usr/bin/env python3
"""
Startup script for the AI Health Predictor Flask backend
This script checks for required model files and provides helpful setup instructions.
"""

import os
import sys
import subprocess

def check_model_files():
    """Check if required model files exist"""
    models_dir = "models"
    required_files = [
        "lung_cancer_model.pkl",
        "lung_cancer_label_encoder.pkl", 
        "diabetes_model.pkl"
    ]
    
    missing_files = []
    
    if not os.path.exists(models_dir):
        print(f"❌ Models directory '{models_dir}' not found!")
        print("Creating models directory...")
        os.makedirs(models_dir)
        missing_files = required_files
    else:
        for file in required_files:
            file_path = os.path.join(models_dir, file)
            if not os.path.exists(file_path):
                missing_files.append(file)
    
    return missing_files

def print_setup_instructions():
    """Print setup instructions for missing model files"""
    print("\n📋 SETUP INSTRUCTIONS")
    print("=" * 50)
    print("To run the backend, you need to place your pre-trained models in the 'models/' directory:")
    print()
    print("Required files:")
    print("  📁 models/")
    print("    ├── lung_cancer_model.pkl")
    print("    ├── lung_cancer_label_encoder.pkl")
    print("    └── diabetes_model.pkl")
    print()
    print("Model requirements:")
    print("  • lung_cancer_model.pkl: Scikit-learn classifier trained on 23 features")
    print("  • lung_cancer_label_encoder.pkl: LabelEncoder for converting predictions to text")
    print("  • diabetes_model.pkl: Scikit-learn classifier trained on 16 features")
    print()
    print("For detailed model specifications, see: models/README.md")
    print()
    print("After placing your model files, run:")
    print("  python app.py")

def install_dependencies():
    """Install Python dependencies"""
    print("📦 Installing Python dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies. Please run manually:")
        print("  pip install -r requirements.txt")
        return False

def main():
    """Main startup function"""
    print("🚀 AI Health Predictor Backend Startup")
    print("=" * 50)
    
    # Check for model files
    missing_files = check_model_files()
    
    if missing_files:
        print(f"❌ Missing model files: {', '.join(missing_files)}")
        print_setup_instructions()
        return False
    
    # Check if requirements.txt exists
    if not os.path.exists("requirements.txt"):
        print("❌ requirements.txt not found!")
        return False
    
    # Install dependencies
    if not install_dependencies():
        return False
    
    # Check if app.py exists
    if not os.path.exists("app.py"):
        print("❌ app.py not found!")
        return False
    
    print("✅ All checks passed! Starting the Flask server...")
    print("🌐 Server will be available at: http://localhost:5000")
    print("📡 API endpoints:")
    print("   - POST /predict_lung_cancer")
    print("   - POST /predict_diabetes")
    print("   - GET  /health")
    print("\nPress Ctrl+C to stop the server")
    print("-" * 50)
    
    # Start the Flask server
    try:
        subprocess.run([sys.executable, "app.py"])
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()
