import os

def generate_alert(data: dict) -> dict:
    """
    Alert Engine decision logic for patient monitoring.
    
    INPUT:
    {
      "patient_id": str,
      "room_number": str,
      "fall_detected": bool,
      "movement": "normal | low | none",
      "posture": "standing | sitting | lying | collapsed",
      "eye_state": "open | closed",
      "activity_duration": int,
      "distress": bool
    }

    OUTPUT:
    {
      "status": "SAFE | WARNING | CRITICAL",
      "confidence": "LOW | MEDIUM | HIGH",
      "reason": str,
      "detected_issues": list,
      "recommended_action": str,
      "alert": bool
    }
    """
    
    fall_detected = data.get("fall_detected", False)
    movement = data.get("movement", "normal")
    posture = data.get("posture", "standing")
    eye_state = data.get("eye_state", "open")
    activity_duration = data.get("activity_duration", 0)
    distress = data.get("distress", False)
    
    # Threshold for prolonged inactivity (default 60 seconds)
    INACTIVITY_THRESHOLD = int(os.environ.get("INACTIVITY_THRESHOLD", 60))
    
    status = "SAFE"
    confidence = "HIGH"
    reason = "Patient appears stable"
    detected_issues = []
    recommended_action = "Continue routine monitoring"
    alert_active = False
    
    # 1. CRITICAL Logic
    if (fall_detected and movement == "none") or distress or posture == "collapsed":
        status = "CRITICAL"
        confidence = "HIGH"
        alert_active = True
        
        if fall_detected and movement == "none":
            detected_issues.append("Fall detected with no subsequent movement")
            reason = "Patient fell and is unresponsive"
            recommended_action = "Immediate medical intervention required. Dispatch emergency team to room."
        elif distress:
            detected_issues.append("Patient distress signal active")
            reason = "Patient signaled for help"
            recommended_action = "Urgent nurse assistance required in room."
        elif posture == "collapsed":
            detected_issues.append("Collapsed posture detected")
            reason = "Patient is in a collapsed state"
            recommended_action = "Immediate assessment required. Check vitals and clear airway."
            
    # 2. WARNING Logic (only if not already critical)
    elif movement == "none" and activity_duration > INACTIVITY_THRESHOLD:
        status = "WARNING"
        confidence = "MEDIUM"
        alert_active = True
        detected_issues.append(f"No movement detected for {activity_duration} seconds")
        reason = f"Prolonged inactivity detected (>{INACTIVITY_THRESHOLD}s)"
        recommended_action = "Perform a welfare check on the patient."
        
    elif posture == "lying" and eye_state == "closed":
        status = "WARNING"
        confidence = "MEDIUM"
        alert_active = True
        detected_issues.append("Patient lying down with eyes closed")
        reason = "Patient may be unconscious or sleeping in an unusual manner"
        recommended_action = "Monitor closely or perform a routine check."
        
    # Final cleanup
    if status == "SAFE":
        alert_active = False
        
    return {
        "status": status,
        "confidence": confidence,
        "reason": reason,
        "detected_issues": detected_issues,
        "recommended_action": recommended_action,
        "alert": alert_active
    }
