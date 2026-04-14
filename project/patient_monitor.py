import cv2
import time
import requests
import json
import numpy as np

# Configuration
API_URL = "http://localhost:5000/api/alert/data"
PATIENT_ID = "P-104"
ROOM_NUMBER = "402-B"
REPORT_INTERVAL = 2  # State report every 2 seconds
MOTION_THRESHOLD = 500  # Sensitivity for movement detection
INACTIVITY_LIMIT = 60   # Seconds of "none" movement before warning

def monitor():
    # Initialize Camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] Could not open camera.")
        return

    print(f"[INFO] Monitoring Room {ROOM_NUMBER} for Patient {PATIENT_ID}...")
    
    # Background subtractor for motion detection
    fgbg = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=16, detectShadows=True)
    
    last_report_time = time.time()
    last_movement_time = time.time()
    
    state = {
        "movement": "normal",
        "posture": "standing",
        "eye_state": "open",
        "fall_detected": False,
        "distress": False
    }

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 1. Preprocess
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (21, 21), 0)
            
            # 2. Motion Detection
            fgmask = fgbg.apply(blur)
            motion_score = np.sum(fgmask > 0)
            
            # Categorize movement
            if motion_score > MOTION_THRESHOLD * 10:
                state["movement"] = "normal"
                last_movement_time = time.time()
            elif motion_score > MOTION_THRESHOLD:
                state["movement"] = "low"
                last_movement_time = time.time()
            else:
                state["movement"] = "none"
            
            # 3. Posture Detection (Simple Contour Analysis)
            contours, _ = cv2.findContours(fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                # Find largest contour (assume it's the patient)
                c = max(contours, key=cv2.contourArea)
                if cv2.contourArea(c) > 5000:
                    x, y, w, h = cv2.boundingRect(c)
                    aspect_ratio = w / float(h)
                    
                    # Heuristic for posture
                    if aspect_ratio > 1.5:
                        state["posture"] = "lying"
                    elif aspect_ratio < 0.6:
                        state["posture"] = "standing"
                    else:
                        state["posture"] = "sitting"
                    
                    # Fall detection heuristic
                    # (Simplified: if posture changed to lying very fast with high motion)
                    if state["posture"] == "lying" and motion_score > 50000:
                         state["fall_detected"] = True
                    else:
                         state["fall_detected"] = False

                    # Draw for visual feedback
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(frame, f"Posture: {state['posture']}", (x, y - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # 4. Reporting
            current_time = time.time()
            activity_duration = int(current_time - last_movement_time)
            
            if current_time - last_report_time > REPORT_INTERVAL:
                payload = {
                    "patient_id": PATIENT_ID,
                    "room_number": ROOM_NUMBER,
                    "fall_detected": state["fall_detected"],
                    "movement": state["movement"],
                    "posture": state["posture"],
                    "eye_state": state["eye_state"],
                    "activity_duration": activity_duration,
                    "distress": state["distress"]
                }
                
                try:
                    response = requests.post(API_URL, json=payload, timeout=1)
                    if response.status_code == 201:
                        res_data = response.json()
                        if res_data.get('alert'):
                            print(f"[!] ALERT: {res_data.get('status')} - {res_data.get('reason')}")
                    else:
                        print(f"[WARN] Failed to report: {response.status_code}")
                except Exception as e:
                    print(f"[ERROR] Connection to backend failed: {e}")
                
                last_report_time = current_time

            # 5. Display
            status_color = (0, 255, 0) if state["movement"] != "none" else (0, 165, 255)
            cv2.putText(frame, f"System Active | Move: {state['movement']}", (20, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
            cv2.putText(frame, f"Duration: {activity_duration}s", (20, 70), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
            
            cv2.imshow("AI Patient Monitor", frame)
            
            # Exit on ESC
            if cv2.waitKey(30) & 0xFF == 27:
                break
                
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("[INFO] Monitoring stopped.")

if __name__ == "__main__":
    monitor()
