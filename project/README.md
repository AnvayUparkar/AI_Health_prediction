# 🩺 AI Health Predictor: The Clinical Intelligence Ecosystem

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/frontend-React_18-cyan.svg)](https://react.dev/)
[![Gemini 1.5 Pro](https://img.shields.io/badge/AI-Gemini_Pro_1.5-violet.svg)](https://deepmind.google/technologies/gemini/)
[![TensorFlow/Scikit-Learn](https://img.shields.io/badge/ML-Predictive_Analytics-orange.svg)](https://scikit-learn.org/)
[![OAuth 2.0](https://img.shields.io/badge/Auth-Google_OAuth-4285F4.svg)](https://developers.google.com/identity/protocols/oauth2)
[![Zoom API](https://img.shields.io/badge/Telehealth-Zoom_Ready-blue.svg)](https://developers.zoom.us/)
[![Brevo API](https://img.shields.io/badge/Email-Brevo-0092FF.svg)](https://www.brevo.com/)

An enterprise-grade, multi-modal healthcare platform integrating Predictive Analytics, Generative AI Clinical Guidance, and Real-time Emergency Monitoring. Built for hospitals, clinicians, and patients to bridge the gap between data and care.

---

## 🚀 1. AI Clinical Intelligence (Powered by Gemini 1.5 Pro)

### 🧬 Automated Medical Report Analyzer
- **OCR Multi-Format Parsing**: Intelligent extraction of clinical markers from PDF, JPG, PNG, and BMP reports.
- **Biochemical Parameter Mapping**: Automatically maps raw text to clinical parameters (HbA1c, Lipid Profile, LFT, KFT, etc.).
- **Perfection Protocol™ Engine**: Generates data-anchored nutrient pairing (e.g., Vitamin C + Iron) to optimize patient recovery.
- **Biochemical Synergy Tracking**: Identifies "Synergy Pairings" to maximize therapeutic outcomes through dietary intervention.

### 🍱 Activity-Driven Meal Planner
- **Dynamic Caloric Optimization**: Generates localized (South-Asian/Indian) diet plans based on real-time activity data from Google Fit/Health Connect.
- **Step-Tiered Logic**: Adjusts nutrient density based on daily physical exertion (Low <3k, Moderate 3k-8k, High >8k).
- **Fixed Clinical Reasoning**: Every meal includes automated "Clinical Justification" for patient education and transparency.

### 🛡️ Resilient Clinical Fallback Engine
- **USDA Biochemical Database**: A deterministic rule-based engine that utilizes USDA food data to provide expert-level dietary recommendations even when the AI API is offline.
- **Safety Registry**: Hardcoded clinical advisory system to ensure service continuity during API rate limits or outages.

### 🩺 Clinical AI Co-Pilot (Senior Consultant Mode)
- **Expert Peer-to-Peer Guidance**: Specialized clinical reasoning for healthcare professionals using a Senior Medical Consultant persona (30+ years experience).
- **Structured Differential Diagnosis**: Provides ranked DDx, pathophysiology interpretations, and standard management protocols (WHO/NICE/ICMR aligned).

---

## 🏥 2. Admitted Patient Monitoring System

- **Real-Time Vitals Tracking**: Continuous monitoring of Blood Glucose, Blood Pressure (Systolic/Diastolic), and Oxygen Saturation (SpO2).
- **Automated Trend Analysis**: Statistical engine calculating vital slopes (Rising/Stable/Declining) to predict potential clinical deterioration.
- **Dietary Compliance Tracking**: Integrated monitoring of hospital meal consumption (Breakfast, Lunch, Snacks, Dinner).
- **Risk-Based Alerting**: Dynamic "Risk Badge" system (Low/Warning/Critical) based on real-time vital trends and automated clinical alerts.

---

## 🔮 3. Predictive Analytics (Machine Learning)

- **Lung Cancer Evaluator**: 23-feature clinical model predicting risk based on dietary, occupational, and lifestyle markers.
- **Diabetes Risk Engine**: 16-parameter model assessing markers like polyuria, polydipsia, and obesity flags.
- **Heart Disease Evaluator**: Comprehensive cardiovascular risk assessment using advanced patient bio-markers and MLP/XGBoost models.
- **Model Persistence**: Optimized model loading and warm-up on server initialization for zero-latency inference.

---

## 🚨 4. Emergency & SOS Infrastructure

### ✋ Gesture-Based SOS Trigger
- **Vision-Aware SOS**: Integrated hand-gesture recognition system (via OpenCV/MediaPipe) to trigger emergency alerts without physical contact.
- **Zero-Touch Panic Activation**: Designed for scenarios where physical interaction with the device is restricted.

### 🗺️ SOS Navigation & Smart Routing
- **Location-Aware Routing**: Intelligently routes SOS alerts based on whether the patient is in an assigned hospital ward or at a remote location.
- **Healthcare Map Integration**: Real-time map routing to the nearest hospital via OpenStreetMap and Overpass API.
- **Live Staff Dispatch**: WebSocket-based (Socket.IO) emergency broadcasting to medical dashboards for immediate response.

---

## 📅 5. Medical Operations & Telehealth

- **Hybrid Appointment Booking**: Support for both In-Person and Online (Telehealth) consultations.
- **Zoom Integration**: Automated generation of Zoom meeting links for online consultations, delivered directly to patients.
- **Smart Notifications**: Automated email delivery via **Brevo** for appointment confirmations, Zoom links, and clinical reports.
- **Role-Based Access Control (RBAC)**: Specialized dashboards for **Admins, Doctors, Receptionists, and Patients**.

---

## 🎮 6. Patient Engagement & UI/UX

- **Glassmorphic UI**: High-end design system with backdrop blurs, animated gradients, and 3D motion containers for a premium experience.
- **Gamification Suite**: Incentivizes clinical compliance through Health Scores, Experience Points (XP), Levels, and a **Rewards Shop**.
- **Personalized Health Dossiers**: Automated generation of weekly PDF health summaries including activity charts and wellness scores.

---

## 📊 7. Data Synchronization Hub

- **Google Cloud Sync**: Full OAuth 2.0 integration with Google Fit for seamless cloud activity ingestion.
- **Health Connect API**: Android-layer integration for multi-source data aggregation (Steps, Sleep, Heart Rate).
- **Cloudinary Integration**: Secure, scalable storage for medical reports and clinical imagery.

---

## 🛠 Project Architecture

```
├── backend/
│   ├── routes/              # Modular API Hub (Alerts, Auth, Diet, Appointments)
│   ├── services/            # Core Service Layer (Gemini, Zoom, Brevo, USDA)
│   ├── models/              # SQLAlchemy Database Models
│   └── ml_models/           # Pickled ML models for predictive analytics
├── src/                     # React 18 Frontend
│   ├── components/          # Glassmorphic UI Component Library
│   ├── services/            # API Communication Layer (Axios + Sockets)
│   └── pages/               # Functional Modules (Monitoring, Predictions, Shop)
└── app.py                   # Flask Core Infrastructure & WebSocket Server
```

---

## ⚖️ Safety & Compliance

> [!CAUTION]
> **DEVELOPER DISCLAIMER**: This application is a clinical software prototype. All medical interpretations are generated by AI/ML models based on provided heuristics. It is **NOT** a substitute for professional medical diagnosis. Users must consult a licensed physician before following any "Perfection Protocol" or diet plan generated by this system.

---
*Architected for Medical Intelligence. Built for Human Care.*  
*Developed by Anvay Mahesh Uparkar*
