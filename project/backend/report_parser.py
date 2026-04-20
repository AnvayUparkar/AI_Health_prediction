"""
Medical Report Parser Module
==============================

Parses OCR-extracted text from medical / blood test reports and produces
structured data.  Uses regex-based extraction, keyword matching, alias
normalisation, and rule-based status classification.

    from backend.report_parser import extract_parameters, detect_important_parameters

Output format (per parameter):
    {
        "Hemoglobin": {
            "value": "10.2",
            "unit": "g/dL",
            "status": "Low",
            "is_important": true,
            "ref_range": "12.0-16.0"
        }
    }

No ML dependencies — pure regex + rule-based for reliability and speed.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ===================================================================
# MEDICAL PARAMETER KNOWLEDGE BASE
# ===================================================================

# Canonical name → (aliases, default unit, ref_min, ref_max)
# ref ranges are representative adult ranges — the parser will prefer
# ranges found in the report text when available.
PARAMETER_DB: Dict[str, dict] = {
    "Hemoglobin": {
        "aliases": ["hemoglobin", "hb", "hgb", "haemoglobin"],
        "unit": "g/dL",
        "ref_min": 12.0,
        "ref_max": 17.5,
    },
    "RBC": {
        "aliases": ["rbc", "red blood cell", "red blood cells", "erythrocytes", "rbc count"],
        "unit": "million/µL",
        "ref_min": 4.0,
        "ref_max": 6.0,
    },
    "WBC": {
        "aliases": ["wbc", "white blood cell", "white blood cells", "leucocytes", "leukocytes", "wbc count", "total wbc", "total leucocyte count", "tlc"],
        "unit": "cells/µL",
        "ref_min": 4000,
        "ref_max": 11000,
    },
    "Platelets": {
        "aliases": ["platelets", "platelet count", "plt"],
        "unit": "lakh/µL",
        "ref_min": 1.5,
        "ref_max": 4.0,
    },
    "Glucose": {
        "aliases": ["glucose", "blood glucose", "random glucose", "random blood sugar", "rbs", "blood sugar"],
        "unit": "mg/dL",
        "ref_min": 70,
        "ref_max": 140,
    },
    "Fasting Blood Sugar": {
        "aliases": ["fasting blood sugar", "fasting glucose", "fbs", "fasting blood glucose"],
        "unit": "mg/dL",
        "ref_min": 70,
        "ref_max": 100,
    },
    "HbA1c": {
        "aliases": [
            # Long aliases FIRST — must beat plain 'hemoglobin' (10 chars)
            "glycated hemoglobin", "glycated haemoglobin",
            "hemoglobin a1c",     "haemoglobin a1c",
            "hb a1c",             "hba1c",
            "a1c",
        ],
        "unit": "%",
        "ref_min": 4.0,
        "ref_max": 5.7,
    },
    "Total Cholesterol": {
        "aliases": ["total cholesterol", "cholesterol", "serum cholesterol", "cholesterol total"],
        "unit": "mg/dL",
        "ref_min": 0,
        "ref_max": 200,
    },
    "HDL Cholesterol": {
        "aliases": ["hdl", "hdl cholesterol", "hdl-c", "hdl c", "high density lipoprotein"],
        "unit": "mg/dL",
        "ref_min": 40,
        "ref_max": 999,  # higher is better
    },
    "LDL Cholesterol": {
        "aliases": ["ldl", "ldl cholesterol", "ldl-c", "ldl c", "low density lipoprotein"],
        "unit": "mg/dL",
        "ref_min": 0,
        "ref_max": 100,
    },
    "Triglycerides": {
        "aliases": ["triglycerides", "tg", "triglyceride", "serum triglycerides"],
        "unit": "mg/dL",
        "ref_min": 0,
        "ref_max": 150,
    },
    "VLDL": {
        "aliases": ["vldl", "vldl cholesterol", "very low density lipoprotein"],
        "unit": "mg/dL",
        "ref_min": 5,
        "ref_max": 40,
    },
    "Vitamin D": {
        "aliases": [
            # -------------------------------------------------------
            # "Vitamin D 25 - Hydroxy" format (exact match from report image)
            # Space-dash-space separates 25 and Hydroxy in some Indian labs
            "vitamin d 25 - hydroxy",  "vitamin d3 25 - hydroxy",
            "vit d 25 - hydroxy",      "vit d3 25 - hydroxy",
            # "Vitamin D 25-Hydroxy" (no spaces around dash)
            "vitamin d 25-hydroxy",    "vitamin d3 25-hydroxy",
            "vit d 25-hydroxy",        "vit d3 25-hydroxy",
            # "Vitamin D 25 Hydroxy" (no dash)
            "vitamin d 25 hydroxy",    "vitamin d3 25 hydroxy",
            "vit d 25 hydroxy",        "vit d3 25 hydroxy",
            # -------------------------------------------------------
            # OH short-form SUFFIX variants: "Vitamin D 25 OH"
            "vitamin d3 (25-oh)",    "vitamin d3 (25 oh)",
            "vitamin d (25-oh)",     "vitamin d (25 oh)",
            "vitamin d3 25-oh",      "vitamin d3 25 oh",
            "vitamin d 25-oh",       "vitamin d 25 oh",
            "vit d3 25-oh",          "vit d3 25 oh",
            "vit d 25-oh",           "vit d 25 oh",
            # 25-OH / 25-Hydroxy PREFIX variants: "25 OH Vitamin D"
            "25-oh vitamin d3",      "25 oh vitamin d3",
            "25-oh vitamin d",       "25 oh vitamin d",
            "25-hydroxy vitamin d3", "25-hydroxy vitamin d",
            "25 hydroxy vitamin d",  "25 hydroxy",
            "25-oh d3",              "25 oh d3",
            # Short forms — must be last so longer aliases win
            "vitamin d3", "vitamin d",
            "vit d3",     "vit d",
        ],
        "unit": "ng/mL",
        "ref_min": 30,
        "ref_max": 100,
    },
    "Vitamin B12": {
        "aliases": ["vitamin b12", "vit b12", "b12", "cobalamin", "cyanocobalamin"],
        "unit": "pg/mL",
        "ref_min": 200,
        "ref_max": 900,
    },
    "Iron": {
        "aliases": ["iron", "serum iron", "fe", "iron level"],
        "unit": "µg/dL",
        "ref_min": 60,
        "ref_max": 170,
    },
    "Ferritin": {
        "aliases": ["ferritin", "serum ferritin"],
        "unit": "ng/mL",
        "ref_min": 12,
        "ref_max": 300,
    },
    "Calcium": {
        "aliases": ["calcium serum", "calcium total", "calcium", "total calcium", "serum calcium"],
        "unit": "mg/dL",
        "ref_min": 8.5,
        "ref_max": 10.5,
    },
    "Uric Acid": {
        "aliases": ["uric acid", "serum uric acid", "urate"],
        "unit": "mg/dL",
        "ref_min": 3.5,
        "ref_max": 7.2,
    },
    "TSH": {
        "aliases": ["tsh", "thyroid stimulating hormone", "thyrotropin"],
        "unit": "µIU/mL",
        "ref_min": 0.4,
        "ref_max": 4.0,
    },
    "T3": {
        "aliases": [
            # Parenthetical suffix format — exact Indian lab format "Triiodothyronine (T3)"
            # MUST be first (longest) so alias_end passes the (T3) and avoids extracting '3'
            "triiodothyronine (t3)",  "total triiodothyronine (t3)",
            "free triiodothyronine (t3)",
            "triiodothyronine(t3)",   # no space before paren
            # Without parenthetical
            "triiodothyronine",       "total triiodothyronine",
            "free triiodothyronine",
            "total t3",  "free t3",   "t3",
        ],
        "unit": "ng/dL",
        "ref_min": 80,
        "ref_max": 200,
    },
    "T4": {
        "aliases": [
            # Parenthetical suffix format — "Total Thyroxine (T4)"
            "total thyroxine (t4)",   "thyroxine (t4)",
            "free thyroxine (t4)",    "total thyroxine(t4)",
            # Without parenthetical
            "total thyroxine",        "free thyroxine",
            "thyroxine",
            "total t4",  "free t4",   "t4",
        ],
        "unit": "µg/dL",
        "ref_min": 5.0,
        "ref_max": 12.0,
    },
    "Creatinine": {
        "aliases": ["creatinine", "serum creatinine", "creat"],
        "unit": "mg/dL",
        "ref_min": 0.6,
        "ref_max": 1.2,
    },
    "BUN": {
        "aliases": ["bun", "blood urea nitrogen", "urea nitrogen"],
        "unit": "mg/dL",
        "ref_min": 7,
        "ref_max": 20,
    },
    "Urea": {
        "aliases": ["urea", "blood urea", "serum urea"],
        "unit": "mg/dL",
        "ref_min": 15,
        "ref_max": 40,
    },
    "SGPT": {
        "aliases": ["sgpt", "alt", "alanine aminotransferase", "alanine transaminase", "sgpt/alt"],
        "unit": "U/L",
        "ref_min": 7,
        "ref_max": 56,
    },
    "SGOT": {
        "aliases": ["sgot", "ast", "aspartate aminotransferase", "aspartate transaminase", "sgot/ast"],
        "unit": "U/L",
        "ref_min": 10,
        "ref_max": 40,
    },
    "Bilirubin Total": {
        "aliases": ["bilirubin", "total bilirubin", "serum bilirubin", "bilirubin total"],
        "unit": "mg/dL",
        "ref_min": 0.1,
        "ref_max": 1.2,
    },
    "Bilirubin Direct": {
        "aliases": ["direct bilirubin", "bilirubin direct", "conjugated bilirubin"],
        "unit": "mg/dL",
        "ref_min": 0.0,
        "ref_max": 0.3,
    },
    "Alkaline Phosphatase": {
        "aliases": ["alkaline phosphatase", "alp", "alk phos", "alkp"],
        "unit": "U/L",
        "ref_min": 44,
        "ref_max": 147,
    },
    "Total Protein": {
        "aliases": ["total protein", "serum protein", "protein total", "total proteins"],
        "unit": "g/dL",
        "ref_min": 6.0,
        "ref_max": 8.3,
    },
    "Albumin": {
        "aliases": ["albumin", "serum albumin", "alb"],
        "unit": "g/dL",
        "ref_min": 3.5,
        "ref_max": 5.5,
    },
    "Globulin": {
        "aliases": ["globulin", "serum globulin"],
        "unit": "g/dL",
        "ref_min": 2.0,
        "ref_max": 3.5,
    },
    "Sodium": {
        "aliases": ["sodium", "na", "serum sodium", "na+"],
        "unit": "mEq/L",
        "ref_min": 136,
        "ref_max": 145,
    },
    "Potassium": {
        "aliases": ["potassium", "k", "serum potassium", "k+"],
        "unit": "mEq/L",
        "ref_min": 3.5,
        "ref_max": 5.0,
    },
    "Chloride": {
        "aliases": ["chloride", "cl", "serum chloride", "cl-"],
        "unit": "mEq/L",
        "ref_min": 98,
        "ref_max": 106,
    },
    "ESR": {
        "aliases": ["esr", "erythrocyte sedimentation rate", "sed rate"],
        "unit": "mm/hr",
        "ref_min": 0,
        "ref_max": 20,
    },
    "GGT": {
        "aliases": [
            # Parenthetical suffix — "Gamma Glutamyl Transferase (GGT)" exact report format
            "gamma glutamyl transferase (ggt)",   "gamma-glutamyl transferase (ggt)",
            "gamma glutamyl transferase(ggt)",
            # Without parenthetical
            "gamma glutamyl transferase",          "gamma-glutamyl transferase",
            "gamma glutamyl transpeptidase",       "gamma-glutamyl transpeptidase",
            "gamma gt", "ggt",
        ],
        "unit": "U/L",
        "ref_min": 9,
        "ref_max": 64,
    },
    "HCT": {
        "aliases": ["hct", "hematocrit", "haematocrit", "pcv", "packed cell volume"],
        "unit": "%",
        "ref_min": 36,
        "ref_max": 54,
    },
    "MCV": {
        "aliases": ["mcv", "mean corpuscular volume"],
        "unit": "fL",
        "ref_min": 80,
        "ref_max": 100,
    },
    "MCH": {
        "aliases": ["mch", "mean corpuscular hemoglobin"],
        "unit": "pg",
        "ref_min": 27,
        "ref_max": 33,
    },
    "MCHC": {
        "aliases": ["mchc", "mean corpuscular hemoglobin concentration"],
        "unit": "g/dL",
        "ref_min": 32,
        "ref_max": 36,
    },
}

# Build a fast lookup: lowered alias → canonical name
_ALIAS_MAP: Dict[str, str] = {}
for _canon, _info in PARAMETER_DB.items():
    for _alias in _info["aliases"]:
        _ALIAS_MAP[_alias.lower()] = _canon

# Sorted aliases — longest first so "fasting blood sugar" matches before
# "blood sugar", "hdl cholesterol" before "cholesterol", etc.
_SORTED_ALIASES: List[Tuple[str, str]] = sorted(
    _ALIAS_MAP.items(), key=lambda x: len(x[0]), reverse=True
)

# Status flag patterns found in medical reports
_FLAG_PATTERNS = [
    (re.compile(r"\bhigh\b", re.I), "High"),
    (re.compile(r"\blow\b", re.I), "Low"),
    (re.compile(r"\babnormal\b", re.I), "Abnormal"),
    (re.compile(r"\bborderline\b", re.I), "Borderline"),
    (re.compile(r"\bcritical\b", re.I), "Critical"),
    # Single H/L at end of line — but NOT when part of a unit like U/L, g/dL, IU/L
    (re.compile(r"(?<!/)\b[Hh]\s*$"), "High"),
    (re.compile(r"(?<!/)\b[Ll]\s*$"), "Low"),
    (re.compile(r"↑|⬆"), "High"),              # arrow up
    (re.compile(r"↓|⬇"), "Low"),               # arrow down
    (re.compile(r"\*\s*[Hh]"), "High"),         # *H pattern
    (re.compile(r"\*\s*[Ll]"), "Low"),          # *L pattern
]

# Regex: reference range pattern.
# Handles all common dash variants (OCR often produces Unicode dashes):
#   hyphen-minus -   en-dash –   em-dash —   Unicode minus −   figure dash ‒
# Also handles "X to Y" text ranges.
_RANGE_PATTERN = re.compile(
    r"(\d+[\.,]?\d*)\s*[-\u2013\u2014\u2212\u2012\u2015]\s*(\d+[\.,]?\d*)"
)
_RANGE_TO_PATTERN = re.compile(
    r"(\d+[\.,]?\d*)\s+to\s+(\d+[\.,]?\d*)", re.I
)

# Simple number finder
_VALUE_NUMBER = re.compile(r"(\d+[\.,]?\d*)")

# Detects numbers used as prose percentages: "50% of…", "40% protein-bound"
# → these are NEVER test result values and must be excluded everywhere.
_PROSE_PCT_RE = re.compile(r"(\d+(?:[\.,]\d+)?)\s*%\s+[a-zA-Z]")

# Status flag words that legitimately appear after a unit (e.g. "14 U/L High")
# These must NOT cause Step 0 to treat the unit as being in prose context.
_UNIT_FLAG_WORDS = {
    "high", "low", "normal", "abnormal", "critical", "borderline", "h", "l",
    "cm", "mm", "detected", "negative", "positive"
}

# Prose words that, if found near a number/unit, suggest it's a footnote
_PROSE_KEYWORDS = {"values", "levels", "noted", "seen", "reference", "noted", "range", "decreased", "increased"}


# Unit patterns (covers most common medical units)
_UNIT_PATTERN = re.compile(
    r"(g/dL|g/dl|mg/dL|mg/dl|ng/mL|ng/ml|pg/mL|pg/ml|"
    r"µg/dL|µg/dl|ug/dL|ug/dl|"
    r"µIU/mL|µIU/ml|uIU/mL|uIU/ml|mIU/L|mIU/l|"
    r"U/L|u/l|IU/L|iu/l|"
    r"mEq/L|meq/l|mmol/L|mmol/l|"
    r"cells/µL|cells/ul|cells/cumm|/cumm|x10[³3]/µL|"
    r"million/µL|million/ul|mill/cumm|"
    r"lakh/µL|lakhs/ul|lac/ul|"
    r"thou/µL|thou/ul|10\^3/ul|"
    r"mm/hr|mm/h|"
    r"fL|fl|pg|%"
    r")",
    re.IGNORECASE,
)

# Parameters that need special unit-aware value normalisation
_UNIT_NORM_RULES = {
    # Platelets: labs may report as 250000 cells/µL but ref range is in lakh
    "Platelets": {
        "check": lambda v: v > 10000,
        "normalise": lambda v: round(v / 100000, 2),
        "normalised_unit": "lakh/µL",
    },
    # WBC: some labs report in thou/µL (thousands), others in cells/µL
    "WBC": {
        "check": lambda v: v < 100,  # likely in thousands
        "normalise": lambda v: round(v * 1000, 0),
        "normalised_unit": "cells/µL",
    },
}


# ===================================================================
# CORE FUNCTIONS
# ===================================================================

def _normalize_ocr_decimals(text: str) -> str:
    """
    Collapses spaces around dots/commas to fix common OCR decimal issues.
    Example: "8 . 9" -> "8.9", "8 , 4" -> "8.4"
    Also converts commas to dots for unified floating point conversion.
    """
    # 1. Collapse digit-space-dot-space-digit to digit.digit
    text = re.sub(r"(\d)\s*[.,]\s*(\d)", r"\1.\2", text)
    
    # 2. Cleanup commas leftovers (if any digit,digit remains)
    text = text.replace(',', '.')
    
    return text


def normalize_medical_term(name: str) -> str:
    """
    Map a raw parameter name from OCR to its canonical form.

    Examples:
        ``"Hb"`` → ``"Hemoglobin"``
        ``"FBS"`` → ``"Fasting Blood Sugar"``
        ``"sgpt"`` → ``"SGPT"``

    Returns the canonical name if found, otherwise the input with
    title-cased formatting.
    """
    lowered = name.strip().lower()

    # Exact alias match
    if lowered in _ALIAS_MAP:
        return _ALIAS_MAP[lowered]

    # Longest-substring match
    best_match = None
    best_len = 0
    for alias, canon in _SORTED_ALIASES:
        if alias in lowered and len(alias) > best_len:
            best_match = canon
            best_len = len(alias)

    if best_match and best_len >= 2:
        return best_match

    return name.strip().title()


def classify_parameter_status(
    value: float,
    ref_min: Optional[float],
    ref_max: Optional[float],
) -> str:
    """
    Classify a numeric value as Normal / Low / High based on reference range.

    Parameters
    ----------
    value : float
        The measured value.
    ref_min : float or None
        Lower bound of the reference range.
    ref_max : float or None
        Upper bound of the reference range.

    Returns
    -------
    str
        One of ``"Low"``, ``"High"``, or ``"Normal"``.
    """
    if ref_min is not None and value < ref_min:
        return "Low"
    if ref_max is not None and value > ref_max:
        return "High"
    return "Normal"


def _detect_flag_in_context(context: str) -> Optional[str]:
    """Detect a status flag (High/Low/Abnormal) in a text fragment."""
    for pattern, status in _FLAG_PATTERNS:
        if pattern.search(context):
            return status
    return None


def _build_boundary_re(alias: str) -> re.Pattern:
    """Build a regex that matches *alias* at word boundaries."""
    escaped = re.escape(alias)
    return re.compile(
        r"(?:^|(?<=[\s,;:(/]))" + escaped + r"(?=$|[\s,;:)/])",
        re.IGNORECASE,
    )


def _find_best_alias(lowered_line: str, already_found: set) -> Optional[Tuple[str, str]]:
    """
    Find the longest-matching alias in a line of text.

    Iterates *_SORTED_ALIASES* (longest first) so that e.g.
    "fasting blood sugar" wins over "blood sugar" or "glucose".

    Parameters
    ----------
    lowered_line : str
        The line in lowercase.
    already_found : set
        Set of canonical names already extracted (skip those).

    Returns
    -------
    (alias, canonical_name) or None
    """
    for alias, canon in _SORTED_ALIASES:
        if canon in already_found:
            continue

        if alias not in lowered_line:
            continue

        # Enforce word-boundary match for ALL aliases
        boundary_re = _build_boundary_re(alias)
        if boundary_re.search(lowered_line):
            return (alias, canon)

        # For longer aliases (≥4 chars) also accept a simple substring
        # because OCR may introduce punctuation artefacts
        if len(alias) >= 4:
            return (alias, canon)

    return None


def _collect_range_numbers(text: str) -> set:
    """
    Collect ALL numbers that appear as part of reference ranges in *text*.

    For a range like ``3.5 - 7.2`` we collect:
        {'3.5', '7.2', '3', '7'}   (full decimal + truncated integer)

    This blacklist is then used to exclude these numbers from
    value candidates.
    """
    blacklist: set = set()
    for pattern in (_RANGE_PATTERN, _RANGE_TO_PATTERN):
        for m in pattern.finditer(text):
            for grp in (m.group(1), m.group(2)):
                blacklist.add(grp)
                # Also add the integer part so '3' from '3.5' is excluded
                if '.' in grp:
                    blacklist.add(grp.split('.')[0])
    return blacklist


def _extract_result_value(line: str, alias_end_pos: int) -> Optional[str]:
    """
    Extract the *test result value* from a line, explicitly avoiding both
    reference-range numbers and prose-percentage values.

    Medical report lines look like any of these:
        ``Hemoglobin   10.2   g/dL   12.0 - 16.0   Low``   (standard)
        ``GGT  * Photometric (L-Gamma…3-Carboxy-4-Nitroani  14  U/L  12 to 64``
        ``Calcium Serum  8.9  mg/dL  8.4 - 10.2``

    Interpretation/footnote text can contain lines like:
        ``50% of calcium is protein-bound, normal range 8.5-10.5 mg/dL``
    These must NOT produce a result value.

    Strategy
    --------
    0. (Prose-pct filter) Identify numbers used as prose percentages
       (``50% of…``) — exclude them in every step below.
    1. (Unit-anchored, highest priority) Iterate every unit match.
       Skip any unit whose following text starts with a lowercase prose word
       (not a known status flag), because that means this is prose
       (``50% of circulating…``) rather than a real measurement.
       For each valid unit, take the last non-blacklisted, non-prose number
       before it.
    2. Section-header gate: if there is no unit AND no reference-range
       pattern, it is a label/header line → return None.
    3. Strip ranges, scan remaining numbers (excluding prose values).
    4. Fallback among all non-blacklisted, non-prose numbers.
    """
    post_alias = line[alias_end_pos:]

    # ── Blacklist: range-endpoint numbers ──────────────────────────────────
    blacklisted = _collect_range_numbers(post_alias)

    # ── Prose-percentage filter ─────────────────────────────────────────────
    # Detect numbers that appear as "50% of …" / "40% protein-bound" etc.
    # These are NEVER test result values (they're from interpretation text)
    # and must be excluded from all candidate sets.
    prose_pcts: set = {m.group(1) for m in _PROSE_PCT_RE.finditer(post_alias)}

    # ── Step 0: Unit-anchored extraction (highest priority) ─────────────────
    # Iterate through ALL unit occurrences in post_alias.
    # For each unit:
    #  - Skip it if the text right after the unit starts with a lowercase
    #    prose word that is NOT a known status flag (High/Low/Normal…).
    #    Example: "50% of circulating calcium" → after "%" = "of …" → SKIP
    #  - Otherwise take the last valid number appearing before that unit.
    for unit_m in _UNIT_PATTERN.finditer(post_alias):
        after_unit = post_alias[unit_m.end():].lstrip()
        if after_unit:
            first_word = after_unit.split()[0].lower()
            # Skip if followed by a prose word (not a status flag or digit)
            if after_unit[0].islower() and first_word not in _UNIT_FLAG_WORDS:
                continue   # e.g. "50% of …" — not a real measurement unit
        pre_unit_text = post_alias[:unit_m.start()]
        # Try candidates from last to first (value is closest to unit)
        for candidate in reversed(_VALUE_NUMBER.findall(pre_unit_text)):
            if candidate not in blacklisted and candidate not in prose_pcts:
                # Plausibility check for Calcium: Values > 25 are likely test codes
                # or page numbers, not serum results (normal is ~9).
                if "calcium" in line.lower() and float(candidate) > 25:
                    continue
                return candidate
        # Candidate list exhausted for this unit — try the next unit match

    # ── Prose word gate ─────────────────────────────────────────────────────
    # If the line contains prose keywords like "noted in" or "reference range",
    # it's likely a footnote and not a result row.
    lowered_post = post_alias.lower()
    if any(word in lowered_post for word in _PROSE_KEYWORDS):
        # But only if it doesn't look like a real result row (value + unit)
        if not _UNIT_PATTERN.search(post_alias):
            return None

    # ── Section-header gate ─────────────────────────────────────────────────
    # A real result row always has at least one of: a unit (checked above)
    # or a reference-range pattern.  Section/category headers have neither.
    # Without this gate the fallback steps would pick up incidental numbers
    # (test codes, page numbers, etc.) stored on header lines.
    has_range = bool(
        _RANGE_PATTERN.search(post_alias) or
        _RANGE_TO_PATTERN.search(post_alias)
    )
    if not has_range:
        return None

    # ── Step 2: strip range patterns, scan remaining numbers ────────────────
    cleaned = _RANGE_PATTERN.sub("", post_alias)
    cleaned = _RANGE_TO_PATTERN.sub("", cleaned)

    for c in _VALUE_NUMBER.findall(cleaned):
        if c not in blacklisted and c not in prose_pcts and c != '':
            return c

    # ── Step 3: fallback among all non-blacklisted, non-prose numbers ────────
    for n in _VALUE_NUMBER.findall(post_alias):
        if n not in blacklisted and n not in prose_pcts:
            return n

    return None


def parse_reference_ranges(report_text: str) -> Dict[str, Tuple[float, float]]:
    """
    Extract reference ranges from report text.

    Looks for patterns like:
        ``"12.0 - 16.0"``
        ``"(70-100)"``
        ``"Ref: 4.0-11.0"``

    Uses longest-alias-first matching so the correct parameter is identified.

    Returns
    -------
    dict
        Mapping of parameter canonical name → (ref_min, ref_max).
        Only parameters whose ranges are found in the text are included.
    """
    ranges: Dict[str, Tuple[float, float]] = {}

    for line in report_text.split("\n"):
        lowered = line.lower().strip()
        if not lowered:
            continue

        # Identify which parameter this line is about (longest alias first)
        match = _find_best_alias(lowered, set())
        if match is None:
            continue
        canon = match[1]

        # Search for reference range pattern on this line
        range_match = _RANGE_PATTERN.search(line)
        if range_match:
            try:
                lo = float(range_match.group(1))
                hi = float(range_match.group(2))
                if lo <= hi:
                    ranges[canon] = (lo, hi)
            except ValueError:
                pass

    return ranges


def extract_parameters(report_text: str) -> Dict[str, dict]:
    """
    Parse OCR-extracted medical report text and extract structured parameters.

    Extraction strategy:
    1. Split text into lines.
    2. For each line, find the **longest** matching alias (prevents
       "blood sugar" from stealing lines meant for "fasting blood sugar").
    3. Extract the result value — separating it from reference range numbers
       (``X - Y`` patterns are excluded from value candidates).
    4. Auto-normalise units (e.g. Platelets 250000 → 2.5 lakh).
    5. Detect status flags **after** the value, not in the whole line.
    6. If no flag is found, classify based on reference range.

    Parameters
    ----------
    report_text : str
        The raw text extracted by OCR.

    Returns
    -------
    dict
        Structured parameter data::

            {
                "Hemoglobin": {
                    "value": "10.2",
                    "unit": "g/dL",
                    "status": "Low",
                    "ref_range": "12.0-16.0",
                    "is_important": false
                },
                ...
            }
    """
    if not report_text or not report_text.strip():
        return {}

    results: Dict[str, dict] = {}
    found_canons: set = set()

    # Pre-clean the text: normalise different dash variants and line endings
    # so the range patterns work consistently on all OCR outputs
    clean_text = report_text.replace('\r\n', '\n').replace('\r', '\n')
    # Normalise Unicode dash variants to plain hyphen for consistency
    for dash_char in ['\u2013', '\u2014', '\u2212', '\u2012', '\u2015']:
        clean_text = clean_text.replace(dash_char, '-')

    # Fix OCR decimal artifacts (e.g. "8 . 9" -> "8.9")
    clean_text = _normalize_ocr_decimals(clean_text)

    lines = clean_text.split("\n")

    for line_idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or len(stripped) < 3:
            continue

        lowered = stripped.lower()

        # --- Find the best (longest) matching alias on this line ---
        match = _find_best_alias(lowered, found_canons)
        if match is None:
            continue

        alias, canon = match

        # Locate where the alias ends in the line
        alias_start = lowered.index(alias)
        alias_end = alias_start + len(alias)

        # --- Extract the result value (not a reference range number) ---
        value_str = _extract_result_value(stripped, alias_end)

        # If no value found on the alias line, try next 1-2 lines.
        # OCR splitting is common: parameter name on one line, numbers below.
        if value_str is None and line_idx + 1 < len(lines):
            next_line = lines[line_idx + 1].strip()
            # Only use next line if it has no known alias (avoid stealing values)
            if next_line and _find_best_alias(next_line.lower(), found_canons) is None:
                value_str = _extract_result_value(next_line, 0)
                if value_str is not None:
                    # Merge lines for range & flag extraction below
                    stripped = stripped + " " + next_line
                    alias_end = alias_start + len(alias)  # unchanged

        # DEBUG: log every matched line so OCR issues are visible in the console
        logger.debug("PARSER | canon=%-25s alias=%-20s raw_line=%r  value=%r",
                     canon, alias, stripped, value_str)

        if value_str is None:
            logger.warning("PARSER | No value found on line for %s: %r", canon, stripped)
            continue

        try:
            numeric_val = float(value_str)
        except ValueError:
            logger.warning("PARSER | Non-numeric value %r for %s on line: %r", value_str, canon, stripped)
            continue

        # --- Extract unit from the line ---
        unit_match = _UNIT_PATTERN.search(stripped[alias_end:])
        db_info = PARAMETER_DB.get(canon, {})
        unit = unit_match.group(1) if unit_match else db_info.get("unit", "")

        # --- Auto-normalise value if unit scale doesn't match ref range ---
        norm_rule = _UNIT_NORM_RULES.get(canon)
        value_was_normalised = False
        if norm_rule and norm_rule["check"](numeric_val):
            numeric_val = norm_rule["normalise"](numeric_val)
            value_str = str(numeric_val)
            unit = norm_rule["normalised_unit"]
            value_was_normalised = True

        # --- Determine reference range ---
        # PRIORITY: extract range from THIS line in the report first.
        # Only fall back to hardcoded DB values when the report doesn't
        # provide a range for this parameter.
        ref_min: Optional[float] = None
        ref_max: Optional[float] = None
        ref_source = "none"

        # Strategy 1: Extract range from the current line (most reliable)
        line_range_match = _RANGE_PATTERN.search(stripped[alias_end:])
        if line_range_match:
            try:
                rr_min = float(line_range_match.group(1))
                rr_max = float(line_range_match.group(2))
                if rr_min <= rr_max:
                    # If we normalised the value, also normalise the ranges
                    if value_was_normalised and norm_rule and norm_rule["check"](rr_min):
                        rr_min = norm_rule["normalise"](rr_min)
                        rr_max = norm_rule["normalise"](rr_max)
                    ref_min, ref_max = rr_min, rr_max
                    ref_source = "report"
            except ValueError:
                pass

        # Strategy 2: Fallback to hardcoded DB values
        if ref_source == "none":
            ref_min = db_info.get("ref_min")
            ref_max = db_info.get("ref_max")
            if ref_min is not None:
                ref_source = "database"

        # --- Detect status flag (only look AFTER the value position) ---
        # Find where the value appears in the post-alias text
        post_value_text = stripped[alias_end:]
        value_pos_in_post = post_value_text.find(value_str)
        if value_pos_in_post >= 0:
            flag_region = post_value_text[value_pos_in_post + len(value_str):]
        else:
            flag_region = post_value_text

        flag = _detect_flag_in_context(flag_region)

        # If no explicit flag, classify by reference range
        if flag is None:
            flag = classify_parameter_status(numeric_val, ref_min, ref_max)

        # --- Build reference range string ---
        ref_range_str = ""
        if ref_min is not None and ref_max is not None:
            # Format nicely — avoid trailing .0 for integers
            def _fmt(v):
                return str(int(v)) if v == int(v) else str(v)
            ref_range_str = f"{_fmt(ref_min)}-{_fmt(ref_max)}"

        results[canon] = {
            "value": value_str,
            "unit": unit,
            "status": flag,
            "ref_range": ref_range_str,
            "ref_source": ref_source,  # "report" or "database" — transparency
            "is_important": False,
        }
        found_canons.add(canon)

    return results


def detect_important_parameters(
    parameters: Dict[str, dict],
) -> Dict[str, dict]:
    """
    Identify which parameters are medically important for diet planning.

    Importance criteria (any of the following):
    1. Status is "High", "Low", "Abnormal", "Critical", or "Borderline"
    2. The parameter is in a high-priority list for diet-based intervention
    3. The value deviates significantly from the reference range (>20%)

    Parameters
    ----------
    parameters : dict
        Output of :func:`extract_parameters`.

    Returns
    -------
    dict
        The same dict with ``is_important`` flags updated in-place.
        Also returns only the dict (for chaining convenience).
    """
    # Parameters that are always diet-relevant if abnormal
    DIET_PRIORITY_PARAMS = {
        "Hemoglobin", "Glucose", "Fasting Blood Sugar", "HbA1c",
        "Total Cholesterol", "HDL Cholesterol", "LDL Cholesterol",
        "Triglycerides", "Vitamin D", "Vitamin B12", "Iron", "Ferritin",
        "Calcium", "Uric Acid", "Creatinine", "SGPT", "SGOT",
        "Total Protein", "Albumin", "TSH", "Sodium", "Potassium",
    }

    for name, info in parameters.items():
        status = info.get("status", "Normal")
        is_important = False

        # Criterion 1: Non-normal status
        if status in ("High", "Low", "Abnormal", "Critical", "Borderline"):
            is_important = True

        # Criterion 2: Diet-priority parameter with any abnormal flag
        if name in DIET_PRIORITY_PARAMS and status != "Normal":
            is_important = True

        # Criterion 3: Significant deviation (>20% outside range)
        try:
            value = float(info.get("value", 0))
            db_info = PARAMETER_DB.get(name, {})
            ref_min = db_info.get("ref_min")
            ref_max = db_info.get("ref_max")
            if ref_min is not None and value < ref_min * 0.8:
                is_important = True
            if ref_max is not None and ref_max > 0 and value > ref_max * 1.2:
                is_important = True
        except (ValueError, TypeError):
            pass

        info["is_important"] = is_important

    return parameters


def get_important_parameters(parameters: Dict[str, dict]) -> Dict[str, dict]:
    """
    Filter and return only the important parameters.

    Parameters
    ----------
    parameters : dict
        Output of :func:`detect_important_parameters`.

    Returns
    -------
    dict
        Subset containing only entries where ``is_important`` is True.
    """
    return {
        name: info
        for name, info in parameters.items()
        if info.get("is_important", False)
    }


def summarize_report(parameters: Dict[str, dict]) -> str:
    """
    Generate a human-readable summary of the extracted medical parameters.

    Parameters
    ----------
    parameters : dict
        Output of :func:`extract_parameters` (after importance detection).

    Returns
    -------
    str
        Formatted text summary.
    """
    if not parameters:
        return "No medical parameters were detected in the report."

    if not parameters:
        return "No medical parameters were detected in the report."

    abnormal = [
        f"{name} ({info['status']})"
        for name, info in parameters.items()
        if info.get("status") not in ("Normal", "Unknown")
    ]

    if not abnormal:
        return "All detected parameters are within the normal reference range."

    # Identify high-level conditions
    conditions = detect_high_level_conditions(parameters)
    cond_str = ""
    if conditions:
        cond_str = f" The results suggest indicators of: {', '.join(conditions).replace('_', ' ')}."

    return f"Detected {len(abnormal)} abnormal values: {', '.join(abnormal)}.{cond_str}"


# ===================================================================
# HIGH-LEVEL CONDITION DETECTION
# ===================================================================

def detect_high_level_conditions(parameters: Dict[str, dict]) -> List[str]:
    """
    Detect high-level health conditions based on parsed lab parameters.
    Returns a list of condition strings (e.g., 'diabetes', 'anemia').
    Uses strict clinical validation rules.
    """
    conditions = []

    # 1. Prediabetes / Diabetes
    hba1c = parameters.get("HbA1c", {})
    fasting = parameters.get("Fasting Blood Sugar", {})
    glucose = parameters.get("Glucose", {})
    
    # Strict Prediabetes check
    if (hba1c.get("status") in ("High", "Borderline") or 
        fasting.get("status") in ("High", "Borderline") or 
        glucose.get("status") in ("High", "Borderline")):
        conditions.append("prediabetes")

    # 2. Lipid Profile - Split into specific conditions
    triglycerides = parameters.get("Triglycerides", {})
    if triglycerides.get("status") == "High":
        conditions.append("hypertriglyceridemia")

    hdl = parameters.get("HDL Cholesterol", {})
    if hdl.get("status") == "Low":
        conditions.append("low_hdl")

    total_chol = parameters.get("Total Cholesterol", {})
    ldl = parameters.get("LDL Cholesterol", {})
    if total_chol.get("status") == "High" or ldl.get("status") == "High":
        conditions.append("hyperlipidemia")

    # 3. Anemia - Strict Hb + MCV check
    hemoglobin = parameters.get("Hemoglobin", {})
    mcv = parameters.get("MCV", {})
    if hemoglobin.get("status") == "Low" and mcv.get("status") == "Low":
        conditions.append("iron_deficiency_anemia")

    # 4. Specific Deficiencies
    vit_b12 = parameters.get("Vitamin B12", {})
    if vit_b12.get("status") == "Low":
        conditions.append("vitamin_b12_deficiency")

    calcium = parameters.get("Calcium", {})
    if calcium.get("status") == "Low":
        conditions.append("hypocalcemia")

    vit_d = parameters.get("Vitamin D", {})
    if vit_d.get("status") == "Low":
        conditions.append("vitamin_d_deficiency")

    # 5. Uric Acid
    uric_acid = parameters.get("Uric Acid", {})
    if uric_acid.get("status") == "High":
        conditions.append("high_uric_acid")

    # 6. Optional: Protein (only if markers present)
    albumin = parameters.get("Albumin", {})
    total_protein = parameters.get("Total Protein", {})
    if albumin.get("status") == "Low" or total_protein.get("status") == "Low":
        conditions.append("protein_deficiency")

    # 7. Liver/Kidney/Thyroid - Only if markers are present and definitively abnormal
    sgpt = parameters.get("SGPT", {})
    sgot = parameters.get("SGOT", {})
    if sgpt.get("status") == "High" or sgot.get("status") == "High":
        conditions.append("liver_stress")

    creatinine = parameters.get("Creatinine", {})
    if creatinine.get("status") == "High":
        conditions.append("kidney_strain")

    tsh = parameters.get("TSH", {})
    if tsh.get("status") in ("Low", "High"):
        conditions.append("thyroid_issues")

    return list(set(conditions))


def detect_conditions_from_text(text: str) -> List[str]:
    """
    Detect condition mentions directly from the OCR text using keywords.
    """
    lowered = text.lower()
    conditions = []

    mappings = {
        "hyperglycemia": ["diabetes", "diabetic", "hyperglycemia", "sugar", "type 2"],
        "hyperlipidemia": ["cholesterol", "lipid", "triglycerides", "hyperlipidemia"],
        "hypertension": ["hypertension", "high blood pressure", "hbp"],
        "iron_deficiency_anemia": ["anemia", "anaemia", "low hemoglobin", "iron deficiency"],
        "protein_deficiency": ["protein deficiency", "low protein", "hypoproteinemia", "malnutrition"],
        "thyroid_issues": ["thyroid", "hypothyroid", "hyperthyroid", "goiter", "hashimoto", "tsh"],
        "kidney_strain": ["kidney", "renal", "nephro", "creatinine", "dialysis"],
        "liver_stress": ["liver", "hepatic", "fatty liver", "sgpt", "sgot", "jaundice"],
        "vitamin_d_deficiency": ["vitamin d deficiency", "low vit d", "osteomalacia", "rickets"],
        "vitamin_b12_deficiency": ["vitamin b12 deficiency", "low b12", "cobalamin deficiency"],
        "high_uric_acid": ["uric acid", "gout", "joint pain", "hyperuricemia"],
        "hypoxia": ["hypoxia", "low oxygen", "oxygen", "spo2", "breathing", "respiratory"],
    }

    for condition, keywords in mappings.items():
        if any(kw in lowered for kw in keywords):
            conditions.append(condition)

    return list(set(conditions))
