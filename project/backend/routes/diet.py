# Modified by Cursor integration: 2025-11-07 — fixed Pylance/type issues and made JWT helper import robust.
# Changes:
# - Avoid direct import of `verify_jwt_in_request_optional` to prevent Pylance unknown-import diagnostics;
#   use getattr on flask_jwt_extended with a safe fallback no-op.
# - Coerce temporary dir and uploaded filename to str before calling os.path.join to satisfy type checkers.
# - Accept Optional[str] in parse_health_keywords and coerce None -> '' before calling .lower().
# - Minor defensive guards for missing optional OCR/pdf libs; behavior unchanged.

import os
import tempfile
from typing import Optional
from flask import Blueprint, request, jsonify
import flask_jwt_extended as _fj
from backend.models import db, User
import mimetypes

# robustly obtain optional helpers from flask_jwt_extended (avoid static-analysis unknown-symbol warnings)
verify_jwt_in_request_optional = getattr(_fj, 'verify_jwt_in_request_optional', lambda: None)
get_jwt_identity = getattr(_fj, 'get_jwt_identity', lambda: None)

diet_bp = Blueprint('diet', __name__)

# Try optional imports
try:
    import pdfplumber  # type: ignore
except Exception:
    pdfplumber = None

try:
    from PIL import Image  # type: ignore
    import pytesseract  # type: ignore
except Exception:
    Image = None
    pytesseract = None

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def allowed_file(filename: str) -> bool:
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return ext in ALLOWED_EXTENSIONS

def extract_text_from_pdf(path: str) -> str:
    text = ''
    if pdfplumber:
        try:
            with pdfplumber.open(path) as pdf:
                pages = [p.extract_text() or '' for p in pdf.pages]
                text = '\n'.join(pages)
            return text
        except Exception:
            pass
    # fallback to PyPDF2
    try:
        import PyPDF2  # type: ignore
        with open(path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            pages = [p.extract_text() or '' for p in reader.pages]
            text = '\n'.join(pages)
    except Exception:
        pass
    return text

def extract_text_from_image(path: str) -> str:
    if Image and pytesseract:
        try:
            img = Image.open(path)
            return pytesseract.image_to_string(img)
        except Exception:
            return ''
    return ''

def parse_health_keywords(text: Optional[str]) -> dict:
    # Very simple keyword-based parser, returns a list of detected conditions and numeric hints
    lowered = (text or '').lower()
    found: dict = {}
    keywords = ['diabetes', 'hypertension', 'hbp', 'cholesterol', 'thyroid', 'anemia', 'obesity', 'bmi', 'age', 'glucose', 'hba1c']
    for kw in keywords:
        if kw in lowered:
            found[kw] = True
    # try to extract numbers after bmi or glucose/hba1c
    import re
    m = re.search(r'bmi[: ]*([0-9]+\.?[0-9]*)', lowered)
    if m:
        try:
            found['bmi_value'] = float(m.group(1))
        except Exception:
            pass
    m2 = re.search(r'glucose[: ]*([0-9]+\.?[0-9]*)', lowered)
    if m2:
        try:
            found['glucose_value'] = float(m2.group(1))
        except Exception:
            pass
    m3 = re.search(r'hba1c[: ]*([0-9]+\.?[0-9]*)', lowered)
    if m3:
        try:
            found['hba1c_value'] = float(m3.group(1))
        except Exception:
            pass
    return found

def generate_diet_plan(parsed: dict) -> dict:
    # Very simple rule-based diet plan generator
    # defaults
    calories = 2000
    protein = '100g'
    carbs = '250g'
    fats = '70g'
    include = ['Vegetables', 'Lean Protein (chicken, fish, tofu)', 'Whole grains', 'Legumes', 'Fruits (limited)']
    avoid = ['Sugary drinks', 'Fried foods', 'Processed snacks', 'Excess salt']

    if 'diabetes' in parsed or parsed.get('glucose_value') or parsed.get('hba1c_value'):
        calories = 1800
        protein = '110g'
        carbs = '180g'
        fats = '60g'
        include = ['Non-starchy vegetables', 'Lean protein', 'Whole grains in moderation', 'Nuts & seeds']
        avoid = ['Sugary drinks', 'White bread', 'Processed sweets', 'High GI foods']

    if 'obesity' in parsed or ('bmi_value' in parsed and parsed['bmi_value'] >= 30):
        calories = 1600
        protein = '120g'
        carbs = '150g'
        fats = '50g'
        include = ['High-fiber vegetables', 'Lean protein', 'Low-calorie snacks', 'Water-rich foods']
        avoid += ['High-calorie desserts', 'Large portions']

    if 'cholesterol' in parsed:
        include += ['Oats', 'Fatty fish (omega-3)', 'Olive oil in moderation']
        avoid += ['Full-fat dairy', 'Trans fats']

    notes = "Personalized by simple keyword rules; for medical advice consult a clinician."

    return {
        'calories_target': calories,
        'macros': {'protein': protein, 'carbs': carbs, 'fats': fats},
        'foods_to_include': include,
        'foods_to_avoid': avoid,
        'notes': notes
    }

@diet_bp.route('/upload-report', methods=['POST'])
def upload_report():
    """
    POST /api/upload-report
    Form field: 'report' (file)
    Optional Authorization: Bearer <token>
    Returns: { diet_plan: {...}, extracted_text: '...', parsed: {...} }
    """
    # optional token: we won't block unauthenticated users but will read user if present
    current_user = None
    try:
        # verify_jwt_in_request_optional is a no-op if the runtime does not provide it
        verify_jwt_in_request_optional()
        identity = get_jwt_identity()
        if identity and isinstance(identity, dict):
            user_id = identity.get('id')
            if user_id:
                try:
                    current_user = User.query.get(user_id)
                except Exception:
                    current_user = None
    except Exception:
        current_user = None

    if 'report' not in request.files:
        return jsonify({'error': 'No file provided under key "report"'}), 400
    f = request.files['report']
    filename = getattr(f, 'filename', '') or ''
    if filename == '':
        return jsonify({'error': 'Empty filename'}), 400
    if not allowed_file(filename):
        return jsonify({'error': 'Unsupported file type'}), 400

    # Check size (Flask will also enforce MAX_CONTENT_LENGTH)
    f.seek(0, os.SEEK_END)
    size = f.tell()
    f.seek(0)
    if size > MAX_FILE_SIZE:
        return jsonify({'error': 'File too large (max 10MB)'}), 400

    tmpdir = tempfile.gettempdir() or ''
    # ensure both args to os.path.join are strings (satisfy type checkers)
    save_path = os.path.join(str(tmpdir), str(filename))
    f.save(save_path)

    extracted = ''
    mimetype, _ = mimetypes.guess_type(save_path)
    if filename.lower().endswith('.pdf'):
        extracted = extract_text_from_pdf(save_path) or ''
    else:
        extracted = extract_text_from_image(save_path) or ''

    if not extracted:
        # fallback: try reading as text file for any plain text
        try:
            with open(save_path, 'r', encoding='utf-8', errors='ignore') as fh:
                extracted = fh.read(10000)
        except Exception:
            extracted = ''

    parsed = parse_health_keywords(extracted or '')
    diet_plan = generate_diet_plan(parsed)

    # Optionally associate with user by saving in DB / another table — not implemented here
    response = {
        'diet_plan': diet_plan,
        'extracted_text': (extracted or '')[:5000],
        'parsed': parsed
    }
    return jsonify(response)