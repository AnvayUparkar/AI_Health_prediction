import os
import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import google.generativeai as genai
import time
from backend.models import User, db

logger = logging.getLogger(__name__)

chat_bp = Blueprint('chat_bp', __name__)

# Emergency keywords to trigger safety net
EMERGENCY_KEYWORDS = [
    "chest pain", "heart attack", "can't breathe", "breathing issue", 
    "severe pain", "unconscious", "stroke", "bleeding heavily", 
]

_MODEL_FALLBACK_CHAIN = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-flash-latest",
]

def _is_quota_error(exc: Exception) -> bool:
    err_str = str(exc).lower()
    return any(k in err_str for k in ["429", "quota", "rate limit", "resource_exhausted", "rate_limit"])

def _is_model_unavailable(exc: Exception) -> bool:
    err_str = str(exc).lower()
    return any(k in err_str for k in ["404", "not found", "is not supported", "listmodels"])

SYSTEM_PROMPT = """
You are a highly experienced senior doctor with over 25 years of clinical expertise across cardiology, general medicine, endocrinology, and preventive healthcare.

Guidelines:
- Explain medical concepts in simple, empathetic, and clear terms. Be calm and professional.
- Do NOT prescribe specific medicines or dosages.
- Provide structured answers focusing on Possible Causes, Lifestyle Suggestions, and When to consult a doctor.
- Always include a disclaimer that this is general guidance and they should consult a real doctor for diagnosis.
- If symptoms sound severe or related to chest pain, breathing issues, or unconsciousness, strictly recommend IMMEDIATE medical help.
- Do NOT break character. You are the Senior Doctor.

Example structured tone:
"Based on your symptoms, this could be due to fatigue or mild infection. I recommend staying hydrated and monitoring your condition. 
*Please consult a doctor for a proper diagnosis.*"
"""

DOCTOR_SYSTEM_PROMPT = """
You are a peer-to-peer Clinical Co-Pilot and Senior Medical Consultant assisting a licensed healthcare professional.

Role:
- Act as a high-level medical advisor providing evidence-based insights.
- You ARE allowed to suggest clinical protocols, medication classes, and standard dosage ranges for professional consideration.
- Maintain a highly technical but collegial professional tone.
- Help the doctor interpret complex report values and suggest potential treatment paths.

Disclaimer (Always include):
"This is a clinical suggestion based on standard protocols. Please exercise your own medical judgement before prescribing."
"""

def _is_emergency(text: str) -> bool:
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in EMERGENCY_KEYWORDS)

@chat_bp.route('/chat', methods=['POST'])
@jwt_required()
def handle_chat():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        data = request.get_json()
        message = data.get("message", "").strip()
        history = data.get("history", [])
        report_context = data.get("report_context") # Optional dict from recently analyzed report
        
        if not message:
            return jsonify({"error": "Message is required"}), 400

        # Pre-flight safety check
        if _is_emergency(message):
            return jsonify({
                "response": "⚠️ **This sounds like a medical emergency.** Please seek immediate medical attention or call your local emergency services (e.g., 911/112). Do not wait."
            }), 200

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return jsonify({"error": "Gemini API key not configured"}), 500

        genai.configure(api_key=api_key)
        
        # Convert frontend history to gemini history format
        gemini_history = []
        for msg in history:
            role = "user" if msg.get("role") == "user" else "model"
            gemini_history.append({"role": role, "parts": [msg.get("content", "")]})
        
        # Select prompt and inject context
        is_doctor = user and user.role == 'doctor'
        base_prompt = DOCTOR_SYSTEM_PROMPT if is_doctor else SYSTEM_PROMPT
        
        if report_context:
            context_str = "\n\nACTIVE PATIENT REPORT CONTEXT:\n"
            for param, info in report_context.items():
                context_str += f"- {param}: {info.get('value')} {info.get('unit')} (Status: {info.get('status')})\n"
            current_system_prompt = base_prompt + context_str
        else:
            current_system_prompt = base_prompt

        last_err = None
        ai_text = None
        
        for candidate in _MODEL_FALLBACK_CHAIN:
            try:
                model = genai.GenerativeModel(
                    model_name=candidate,
                    system_instruction=current_system_prompt
                )
                chat = model.start_chat(history=gemini_history)
                response = chat.send_message(message)
                ai_text = response.text
                break # Success
            except Exception as exc:
                last_err = exc
                if _is_quota_error(exc):
                    logger.warning(f"Model {candidate} hit quota - trying fallback.")
                    time.sleep(1)
                    continue
                if _is_model_unavailable(exc):
                    logger.warning(f"Model {candidate} unavailable (404) - trying fallback.")
                    continue
                
                err_str = str(exc).lower()
                if "api_key_invalid" in err_str or "400" in err_str:
                    logger.error("API Key invalid.")
                    return jsonify({"error": "Configuration error with AI service."}), 500
                    
                # Other errors
                logger.error(f"Error with model {candidate}: {exc}")
                break # Don't fallback for unexpected errors
                
        if ai_text is None:
            logger.error(f"All models failed. Last error: {last_err}")
            # RESCUE LOGIC: Deterministic clinical guidance if AI is down
            from backend.fallback_diet_engine import detect_high_level_conditions, CONDITION_MAP
            conditions = detect_high_level_conditions(message)
            if conditions:
                rescue_lines = [
                    "⚠️ **Clinical Fallback Active**: My primary AI engine is currently unavailable, but here is my deterministic medical guidance based on your symptoms:",
                    ""
                ]
                for cond in conditions:
                    info = CONDITION_MAP[cond]
                    rescue_lines.append(f"**Concerning: {info['technical_name']}**")
                    rescue_lines.append(f"- {info['explanation']}")
                    rescue_lines.append(f"- *Action*: {info['solution']}")
                    rescue_lines.append("")
                rescue_lines.append("*Please consult a doctor for a formal diagnosis. This is an automated safety fallback.*")
                ai_text = "\n".join(rescue_lines)
            else:
                return jsonify({"error": "All AI models are currently overwhelmed. Please try again later."}), 503
        
        # Post-flight disclaimer check (Ensure the AI actually included a disclaimer)
        if "consult" not in ai_text.lower() and "doctor" not in ai_text.lower():
            ai_text += "\n\n*Disclaimer: This is general guidance. Please consult a doctor for diagnosis.*"

        return jsonify({
            "response": ai_text
        }), 200

    except Exception as e:
        logger.error(f"Chatbot Error: {str(e)}")
        return jsonify({"error": "An error occurred while processing your request."}), 500
