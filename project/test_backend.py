#!/usr/bin/env python3
"""
Test script for the AI Health Predictor Flask backend
This script tests both endpoints with sample data to verify the backend is working correctly.
"""

import requests
import json
import time

# Backend URL
BASE_URL = "http://localhost:5000"

def test_health_endpoint():
    """Test the health check endpoint"""
    print("🏥 Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] Health check passed: {data}")
            return True
        else:
            print(f"[FAIL] Health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("[FAIL] Cannot connect to backend. Make sure the Flask server is running on http://localhost:5000")
        return False
    except Exception as e:
        print(f"[FAIL] Health check error: {e}")
        return False

def test_lung_cancer_endpoint():
    """Test the lung cancer prediction endpoint"""
    print("\n🫁 Testing lung cancer prediction endpoint...")
    
    # Sample data matching the frontend form structure
    sample_data = {
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
    
    try:
        response = requests.post(
            f"{BASE_URL}/predict_lung_cancer",
            headers={"Content-Type": "application/json"},
            data=json.dumps(sample_data)
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"[OK] Lung cancer prediction successful:")
            print(f"   Prediction: {result.get('prediction')}")
            print(f"   Confidence: {result.get('confidence')}%")
            return True
        else:
            error_data = response.json()
            print(f"[FAIL] Lung cancer prediction failed: {error_data.get('error')}")
            return False
            
    except Exception as e:
        print(f"[FAIL] Lung cancer prediction error: {e}")
        return False

def test_diabetes_endpoint():
    """Test the diabetes prediction endpoint"""
    print("\n🩸 Testing diabetes prediction endpoint...")
    
    # Sample data matching the frontend form structure
    sample_data = {
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
    
    try:
        response = requests.post(
            f"{BASE_URL}/predict_diabetes",
            headers={"Content-Type": "application/json"},
            data=json.dumps(sample_data)
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"[OK] Diabetes prediction successful:")
            print(f"   Prediction: {result.get('prediction')}")
            print(f"   Confidence: {result.get('confidence')}%")
            return True
        else:
            error_data = response.json()
            print(f"[FAIL] Diabetes prediction failed: {error_data.get('error')}")
            return False
            
    except Exception as e:
        print(f"[FAIL] Diabetes prediction error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 AI Health Predictor Backend Test Suite")
    print("=" * 50)
    
    # Test health endpoint first
    if not test_health_endpoint():
        print("\n[FAIL] Backend is not running or not accessible.")
        print("Please start the Flask server with: python app.py")
        return
    
    # Test prediction endpoints
    lung_success = test_lung_cancer_endpoint()
    diabetes_success = test_diabetes_endpoint()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"   Health Check: [OK]")
    print(f"   Lung Cancer: {'[OK]' if lung_success else '[FAIL]'}")
    print(f"   Diabetes: {'[OK]' if diabetes_success else '[FAIL]'}")
    
    if lung_success and diabetes_success:
        print("\n🎉 All tests passed! Your backend is working correctly.")
        print("You can now use your React frontend to connect to the backend.")
    else:
        print("\n⚠️  Some tests failed. Please check:")
        print("   1. Model files are in the models/ directory")
        print("   2. Model files have the correct format")
        print("   3. All dependencies are installed")

if __name__ == "__main__":
    main()
