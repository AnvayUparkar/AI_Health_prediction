# 🩺 AI Health Predictor: The Clinical Intelligence Ecosystem

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/frontend-React_18-cyan.svg)](https://react.dev/)
[![Gemini 1.5 Pro](https://img.shields.io/badge/AI-Gemini_Pro_1.5-violet.svg)](https://deepmind.google/technologies/gemini/)
[![TensorFlow/Scikit-Learn](https://img.shields.io/badge/ML-Predictive_Analytics-orange.svg)](https://scikit-learn.org/)
[![OAuth 2.0](https://img.shields.io/badge/Auth-Google_OAuth-4285F4.svg)](https://developers.google.com/identity/protocols/oauth2)

An enterprise-grade, multi-modal healthcare platform integrating Predictive Analytics, Generative AI Clinical Guidance, and Real-time Emergency Monitoring.

---

## 🚀 1. AI Clinical Intelligence (Powered by Gemini)

### 🧬 Automated Medical Report Analyzer
- **OCR Multi-Format Parsing**: Extracts clinical markers from PDF, JPG, PNG, and BMP reports using an intelligent OCR pipeline.
- **Biochemical Parameter Mapping**: Automatically maps raw text to clinical parameters (HbA1c, Cholesterol, Glucose, etc.).
- **Perfection Protocol™ Engine**: Generates data-anchored nutrient pairing (e.g., Vitamin C + Iron) to optimize recovery.
- **Biochemical Synergy Tracking**: Identifies "Synergy Pairings" to maximize therapeutic outcomes.

### 🍱 Activity-Driven Meal Planner
- **Dynamic Caloric Optimization**: Automatically generates localized (South-Asian/Indian) diet plans based on the previous day's step count.
- **Step-Tiered Logic**:
    - **Tier 1 (Low <3k)**: Focus on insulin sensitivity and inflammation control.
    - **Tier 2 (Moderate 3k-8k)**: Balanced maintenance and metabolic support.
    - **Tier 3 (High >8k)**: Protein-sparing energy replenishment and muscle recovery.
- **Fixed Clinical Reasoning**: Every meal includes a permanent "Clinical Justification" for transparency.

### 💬 Clinical AI Chatbox
- **Cross-Module Persistence**: The AI remembers your latest lab results and activity levels during the session.
- **Safety Fallback Registry**: Hardcoded rule-based advisory system for when API quotas are reached.

---

## 🔮 2. Predictive Analytics (Machine Learning)

- **Lung Cancer Evaluator**: 23-feature model predicting risk based on dietary, occupational, and lifestyle markers.
- **Diabetes Risk Engine**: 16-parameter clinical model assessing polyuria, polydipsia, and obesity flags.
- **Heart Disease Evaluator**: Comprehensive cardiovascular risk assessment using patient bio-markers.
- **Model Persistance**: Automated model loading and warm-up on server initialization.

---

## 🚨 3. Emergency & Safety Infrastructure

### ✋ Gesture-Based SOS Trigger
- **Vision-Aware SOS**: Integrated hand-gesture recognition system to trigger emergency alerts without physical contact.
- **Zero-Touch Panic Activation**: Designed for situations where physical interaction with the device is impossible.

### 🏥 Ward & Proximity Monitoring
- **Ward Assignment Logic**: Intelligently routes SOS alerts based on whether the patient is in a assigned hospital ward or at home.
- **Real-time Alerting**: WebSocket-based (SocketIO) emergency broadcasting to medical dashboards.
- **Remote GPS Location**: Full GPS tracking for SOS alerts occurring outside medical facilities.

---

## 📊 4. Data Synchronization Hub

- **Google Cloud Sync**: Full OAuth 2.0 integration with Google Fit for seamless cloud activity ingestion.
- **Health Connect API**: Android-layer integration for multi-source data aggregation (Steps, Sleep, Heart Rate).
- **Graceful Fallback**: Automated manual entry failover when device sync or cloud APIs are unavailable.

---

## 📄 5. Professional Reporting & Exports

- **Weekly Health Dossier**: Professionally designed PDF summaries including activity charts, weight trends, and wellness scores.
- **Lab Analysis Protocol**: High-fidelity PDF exports of the AI Clinical Analysis, including parameter tables and protocols.
- **ReportLab Integration**: Custom-engineered PDF layouts with biochemical parameter tables.

---

## 🎮 6. Patient Engagement & UI/UX

- **Glassmorphic UI**: High-end design system with backdrop blurs, animated gradients, and 3D motion containers.
- **Gamification Suite**: Health scores, experience points (XP), and a rewards shop to encourage clinical compliance.
- **Animated Dashboards**: Real-time visualization of step activity and hydration levels.

---

## 🛠 Project Architecture

```
├── backend/
│   ├── routes/              # Modular API Hub (Alerts, Auth, Diet, Prediction)
│   ├── step_meal_planner.py  # Gemini Activity-Aware Logic
│   ├── report_parser.py     # OCR & Parameter Mapping
│   └── health_analyzer.py   # Decision Support Engine
├── src/                     # React 18 Frontend
│   ├── components/          # Glassmorphic Component Library
│   ├── pages/               # Functional Modules (Report Analyzer, Predictions)
│   └── services/            # API Communication Layer
└── app.py                   # Flask Core Infrastructure
```

---

## ⚖️ Safety & Compliance

> [!CAUTION]
> **DEVELOPER DISCLAIMER**: This application is a clinical software prototype. All medical interpretations are generated by AI/ML models based on provided heuristics. It is **NOT** a substitute for professional medical diagnosis. Users must consult a licensed physician before following any "Perfection Protocol" or diet plan generated by this system.

---
*Architected for Medical Intelligence. Built for Human Care.*
*Developed by Anvay Mahesh Uparkar*
