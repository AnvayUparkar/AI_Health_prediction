import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from mediapipe.tasks.python.vision import HandLandmarkerOptions, HandLandmarker
import base64
import numpy as np
import time
import os
import urllib.request
from datetime import datetime, timezone
from backend.db_service import DBService
from backend.extensions import socketio

# ── Download the hand landmark model if not present ──────────────────────────
_MODEL_PATH = os.path.join(os.path.dirname(__file__), 'hand_landmarker.task')
_MODEL_URL = (
    'https://storage.googleapis.com/mediapipe-models/'
    'hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task'
)

def _ensure_model():
    if not os.path.exists(_MODEL_PATH):
        print('[INFO] Downloading hand_landmarker.task model...')
        urllib.request.urlretrieve(_MODEL_URL, _MODEL_PATH)
        print('[OK] Model downloaded.')

_ensure_model()

# ─────────────────────────────────────────────────────────────────────────────

class GestureService:
    def __init__(self):
        base_options = mp_python.BaseOptions(model_asset_path=_MODEL_PATH)
        options = HandLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.IMAGE,   # per-frame, not video stream
            num_hands=1,
            min_hand_detection_confidence=0.7,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.detector = HandLandmarker.create_from_options(options)

        # State tracking for clench sequence: OPEN → CLOSED → OPEN
        self.last_state = 'OPEN'
        self.state_sequence: list[str] = []
        self.last_change_time = time.time()
        self.cooldown = 2.0  # seconds between SOS triggers
        self.last_sos_time = 0.0

    # ── Public API ────────────────────────────────────────────────────────────
    def process_frame(self, base64_frame: str, patient_info: dict | None = None) -> dict:
        try:
            # Decode base64 → numpy frame
            encoded_data = base64_frame.split(',')[1]
            nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if frame is None:
                return {'status': 'error', 'message': 'Invalid frame data'}

            # Mirror + convert to RGB
            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Wrap in MediaPipe Image
            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=rgb_frame,
            )

            detection_result = self.detector.detect(mp_image)

            current_gesture = 'NONE'
            hand_detected = False

            if detection_result.hand_landmarks:
                hand_detected = True
                lm = detection_result.hand_landmarks[0]  # first hand

                # Finger tip indices:  thumb=4, index=8, middle=12, ring=16, pinky=20
                # PIP/MCP joints:              3        6        10       14       18
                # A finger is "open" when its tip y-coord < its pip y-coord
                # (smaller y = higher on screen after flip)
                tips = [8, 12, 16, 20]   # index, middle, ring, pinky tips
                pips = [6, 10, 14, 18]   # their proximal joints

                is_closed = all(lm[t].y > lm[p].y for t, p in zip(tips, pips))
                current_gesture = 'CLOSED' if is_closed else 'OPEN'

            self._update_sequence(current_gesture, patient_info)

            return {
                'status': 'ok',
                'hand_detected': hand_detected,
                'gesture': current_gesture,
                'sequence': self.state_sequence,
            }

        except Exception as e:
            print(f'[ERROR] Gesture processing failed: {e}')
            return {'status': 'error', 'message': str(e)}

    # ── Sequence logic ────────────────────────────────────────────────────────
    def _update_sequence(self, current_state: str, patient_info: dict | None):
        if current_state == 'NONE':
            return

        now = time.time()

        # Reset if stale
        if now - self.last_change_time > 3.0:
            self.state_sequence = []

        if current_state != self.last_state:
            print(f'[DEBUG] Gesture: {self.last_state} → {current_state}')
            self.state_sequence.append(current_state)
            self.last_state = current_state
            self.last_change_time = now

            # Check OPEN → CLOSED → OPEN
            if len(self.state_sequence) >= 3:
                last_three = self.state_sequence[-3:]
                if last_three == ['OPEN', 'CLOSED', 'OPEN']:
                    if now - self.last_sos_time >= self.cooldown:
                        print('[!!!] GESTURE SOS TRIGGERED')
                        self._trigger_sos(patient_info)
                        self.last_sos_time = now
                    self.state_sequence = []  # reset after match

    def _trigger_sos(self, info: dict | None):
        info = info or {}
        patient_id = info.get('patient_id', 'GUEST_GESTURE')
        room = info.get('room_number', 'ZONE_ALPHA')

        alert_data = {
            'patient_id': patient_id,
            'room_number': room,
            'status': 'CRITICAL',
            'confidence': '95%',
            'reason': 'SOS TARGET GESTURE DETECTED (FIST CLENCH)',
            'detected_issues': ['Visual Distress Signal', 'Emergency Hand Gesture'],
            'recommended_action': 'Immediate Nurse Dispatch',
            'alert': True,
        }

        new_alert = DBService.create_alert(alert_data)
        response_data = new_alert.to_dict() if hasattr(new_alert, 'to_dict') else alert_data
        socketio.emit('new_alert', response_data)


# Singleton
gesture_detector = GestureService()