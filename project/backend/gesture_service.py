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
from backend.services.appointment_service import AppointmentService
from backend.extensions import socketio
import json

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
            running_mode=mp_vision.RunningMode.IMAGE,
            num_hands=1,
            min_hand_detection_confidence=0.7,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.detector = HandLandmarker.create_from_options(options)

        # How many consecutive CLOSED frames before SOS fires
        self.FIST_FRAMES_REQUIRED = 3
        self._fist_frame_count = 0

        self.cooldown = 5.0          # seconds between SOS triggers
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

            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=rgb_frame,
            )

            detection_result = self.detector.detect(mp_image)

            current_gesture = 'NONE'
            hand_detected = False

            if detection_result.hand_landmarks:
                hand_detected = True
                lm = detection_result.hand_landmarks[0]

                tips = [8, 12, 16, 20]   # index, middle, ring, pinky tips
                pips = [6, 10, 14, 18]   # proximal joints

                is_closed = all(lm[t].y > lm[p].y for t, p in zip(tips, pips))
                current_gesture = 'CLOSED' if is_closed else 'OPEN'

            sos_fired = self._update_fist_state(current_gesture, patient_info)

            return {
                'status': 'ok',
                'hand_detected': hand_detected,
                'gesture': current_gesture,
                'fist_frames': self._fist_frame_count,
                'sos_fired': sos_fired,
            }

        except Exception as e:
            print(f'[ERROR] Gesture processing failed: {e}')
            return {'status': 'error', 'message': str(e)}

    # ── Fist-hold logic ───────────────────────────────────────────────────────
    def _update_fist_state(self, current_gesture: str, patient_info: dict | None) -> bool:
        """
        Increments a consecutive-frame counter while the fist is held.
        Fires SOS once the counter reaches FIST_FRAMES_REQUIRED,
        then resets so it won't re-fire until the hand opens and closes again.
        Returns True if SOS was fired this frame.
        """
        if current_gesture == 'CLOSED':
            self._fist_frame_count += 1
        else:
            # Hand opened or disappeared — reset counter
            self._fist_frame_count = 0
            return False

        now = time.time()

        if (
            self._fist_frame_count == self.FIST_FRAMES_REQUIRED   # exactly on threshold
            and now - self.last_sos_time >= self.cooldown
        ):
            print(f'[!!!] FIST HELD FOR {self.FIST_FRAMES_REQUIRED} FRAMES — SOS TRIGGERED')
            self._trigger_sos(patient_info)
            self.last_sos_time = now
            # Reset so a continuous hold doesn't keep re-firing
            self._fist_frame_count = 0
            return True

        return False

    # ── SOS dispatch (unchanged) ──────────────────────────────────────────────
    def _trigger_sos(self, info: dict | None):
        info = info or {}
        patient_id = info.get('patient_id', 'GUEST_GESTURE')
        lat = info.get('latitude')
        lon = info.get('longitude')

        ward_info = AppointmentService.get_patient_ward_info(patient_id)

        location_type = 'REMOTE'
        room_desc = info.get('room_number', 'ZONE_ALPHA')
        nearest_hosp = None
        dist_km = None
        notified_docs = []

        if ward_info and ward_info.get('ward_number'):
            location_type = 'WARD'
            room_desc = f"Ward {ward_info['ward_number']}"
            if ward_info.get('doctor_id'):
                notified_docs = [ward_info['doctor_id']]
        elif lat and lon:
            hosp_data = AppointmentService.calculate_nearest_hospital(lat, lon)
            if hosp_data:
                nearest_hosp = hosp_data['name']
                dist_km = hosp_data['distance']
                room_desc = f"Near {nearest_hosp} ({dist_km} km)"
                hosp_staff = DBService.get_medical_staff_by_hospital(nearest_hosp)
                notified_docs = [d['id'] if isinstance(d, dict) else d.id for d in hosp_staff]

        alert_data = {
            'patient_id': patient_id,
            'room_number': room_desc,
            'ward_number': ward_info.get('ward_number') if ward_info else None,
            'status': 'CRITICAL',
            'confidence': '95%',
            'reason': 'SOS GESTURE DETECTED (FIST CLENCH HELD)',
            'detected_issues': ['Visual Distress Signal', 'Emergency Hand Gesture'],
            'recommended_action': 'Immediate Medical Response Required',
            'alert': True,
            'latitude': lat,
            'longitude': lon,
            'location_type': location_type,
            'nearest_hospital': nearest_hosp,
            'distance_km': dist_km,
            'notified_doctor_ids': json.dumps(notified_docs),
        }

        new_alert = DBService.create_alert(alert_data)

        AppointmentService.log_audit_action(
            action="SOS_TRIGGERED_GESTURE",
            patient_id=patient_id,
            ward_number=ward_info.get('ward_number') if ward_info else None,
            details={
                "location_type": location_type,
                "hospital": nearest_hosp,
                "distance": dist_km,
            }
        )

        response_data = new_alert.to_dict() if hasattr(new_alert, 'to_dict') else alert_data
        socketio.emit('new_alert', response_data)


# Singleton
gesture_detector = GestureService()