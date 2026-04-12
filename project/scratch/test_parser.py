
import re
from typing import Optional, List, Tuple

_VALUE_NUMBER = re.compile(r"(\d+\.?\d*)")
_UNIT_PATTERN = re.compile(r"(g/dL|mg/dL|mg/dl|U/L|u/l|%)", re.IGNORECASE)
_RANGE_PATTERN = re.compile(r"(\d+\.?\d*)\s*-\s*(\d+\.?\d*)")
_RANGE_TO_PATTERN = re.compile(r"(\d+\.?\d*)\s+to\s+(\d+\.?\d*)", re.I)
_PROSE_PCT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%\s+[a-zA-Z]")
_UNIT_FLAG_WORDS = {"high", "low", "normal", "abnormal", "critical", "borderline", "h", "l"}
_PROSE_KEYWORDS = {"values", "levels", "noted", "seen", "reference", "range", "decreased", "increased"}

def _collect_range_numbers(text: str) -> set:
    nums = set()
    for m in _RANGE_PATTERN.finditer(text):
        nums.add(m.group(1))
        nums.add(m.group(2))
        if '.' in m.group(1): nums.add(m.group(1).split('.')[0])
        if '.' in m.group(2): nums.add(m.group(2).split('.')[0])
    for m in _RANGE_TO_PATTERN.finditer(text):
        nums.add(m.group(1))
        nums.add(m.group(2))
        if '.' in m.group(1): nums.add(m.group(1).split('.')[0])
        if '.' in m.group(2): nums.add(m.group(2).split('.')[0])
    return nums

def _extract_result_value(line: str, alias_end_pos: int) -> Optional[str]:
    post_alias = line[alias_end_pos:]
    blacklisted = _collect_range_numbers(post_alias)
    prose_pcts = {m.group(1) for m in _PROSE_PCT_RE.finditer(post_alias)}

    # Step 0: Unit-anchored
    for unit_m in _UNIT_PATTERN.finditer(post_alias):
        after_unit = post_alias[unit_m.end():].lstrip()
        if after_unit:
            first_word = after_unit.split()[0].lower()
            if after_unit[0].islower() and first_word not in _UNIT_FLAG_WORDS:
                continue
        pre_unit_text = post_alias[:unit_m.start()]
        for candidate in reversed(_VALUE_NUMBER.findall(pre_unit_text)):
            if candidate not in blacklisted and candidate not in prose_pcts:
                # Plausibility check for Calcium
                if "calcium" in line.lower() and float(candidate) > 25:
                    continue
                return candidate
    
    # Prose gate
    lowered_post = post_alias.lower()
    if any(word in lowered_post for word in _PROSE_KEYWORDS):
        if not _UNIT_PATTERN.search(post_alias):
            return None

    # Gate
    has_range = bool(_RANGE_PATTERN.search(post_alias) or _RANGE_TO_PATTERN.search(post_alias))
    if not has_range: return None

    # Fallbacks
    cleaned = _RANGE_PATTERN.sub("", post_alias)
    cleaned = _RANGE_TO_PATTERN.sub("", cleaned)
    for c in _VALUE_NUMBER.findall(cleaned):
        if c not in blacklisted and c not in prose_pcts and c != '':
            return c
    return None

# TEST CASES
tests = [
    ("Calcium Serum  8.9  mg/dL  8.4 - 10.2", 13), # Expected 8.9
    ("Calcium 50 mg/dl High 8.5-10.5", 7), # Expected None (fails plausibility > 25)
    ("Decreased levels of calcium are noted in vitamin D deficiency", 20), # Expected None (prose gate)
    ("GGT  3-Carboxy-4-Nitroani  14 U/L 12 to 64", 4), # Expected 14
]

for text, pos in tests:
    res = _extract_result_value(text, pos)
    print(f"Line: {text!r} -> Result: {res}")
