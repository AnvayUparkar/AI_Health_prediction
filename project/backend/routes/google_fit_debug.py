"""
google_fit_debug.py
====================
NEW MODULE — Google Fit Debug & Verification Service Layer
Does NOT modify any existing routes or architecture.

Provides:
  POST /api/google-fit/verify    — Pre-flight check: verify scopes + data availability
  POST /api/google-fit/raw       — Fetch raw (non-aggregated) data for a single metric
  POST /api/google-fit/aggregate — Correct aggregate call with full log output
  GET  /api/google-fit/sources   — List all data sources registered in Google Fit account
  POST /api/google-fit/diagnose  — Full diagnostic report (scope, sources, sample data)

Usage: import this blueprint in app.py and register with url_prefix='/api'
"""

import json
import logging
import time
from datetime import datetime, timedelta, timezone

import requests
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

logger = logging.getLogger(__name__)

google_fit_debug_bp = Blueprint("google_fit_debug", __name__)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS — correct dataTypeName values for every metric
# ─────────────────────────────────────────────────────────────────────────────

DATA_TYPE_STEPS        = "com.google.step_count.delta"
DATA_TYPE_HEART_RATE   = "com.google.heart_rate.bpm"
DATA_TYPE_CALORIES     = "com.google.calories.expended"
DATA_TYPE_DISTANCE     = "com.google.distance.delta"
DATA_TYPE_ACTIVE_MINS  = "com.google.active_minutes"
DATA_TYPE_SLEEP        = "com.google.sleep.segment"

# ─── Officially merged master data-source IDs (always prefer these) ──────────
MERGED_SOURCE_STEPS      = "derived:com.google.step_count.delta:com.google.android.gms:merge_step_deltas"
MERGED_SOURCE_HEART_RATE = "derived:com.google.heart_rate.bpm:com.google.android.gms:merge_heart_rate_bpm"
MERGED_SOURCE_CALORIES   = "derived:com.google.calories.expended:com.google.android.gms:merge_calories_expended"

# ─── Required OAuth scopes ────────────────────────────────────────────────────
REQUIRED_SCOPES = [
    "https://www.googleapis.com/auth/fitness.activity.read",
    "https://www.googleapis.com/auth/fitness.heart_rate.read",
    "https://www.googleapis.com/auth/fitness.body.read",
    "https://www.googleapis.com/auth/fitness.sleep.read",
]

BASE_URL = "https://www.googleapis.com/fitness/v1/users/me"


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _now_ms() -> int:
    return int(time.time() * 1000)


def _days_ago_ms(days: int) -> int:
    """Return UTC epoch-ms for midnight N days ago (local-aligned)."""
    now = datetime.now(timezone.utc)
    past = now - timedelta(days=days)
    past_midnight = past.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(past_midnight.timestamp() * 1000)


def _ms_to_iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


def _safe_get(url, headers, params=None, label="request"):
    """Wrapped GET with full error logging."""
    try:
        r = requests.get(url, headers=headers, params=params, timeout=15)
        logger.info("[GoogleFit][%s] GET %s → %d", label, url, r.status_code)
        if r.status_code != 200:
            logger.warning("[GoogleFit][%s] Body: %s", label, r.text[:500])
        return r
    except requests.RequestException as e:
        logger.error("[GoogleFit][%s] Network error: %s", label, str(e))
        return None


def _safe_post(url, headers, body, label="request"):
    """Wrapped POST with full error logging."""
    try:
        r = requests.post(url, headers=headers, json=body, timeout=15)
        logger.info("[GoogleFit][%s] POST %s → %d", label, url, r.status_code)
        if r.status_code != 200:
            logger.warning("[GoogleFit][%s] Body: %s", label, r.text[:1000])
        return r
    except requests.RequestException as e:
        logger.error("[GoogleFit][%s] Network error: %s", label, str(e))
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 1. VERIFY TOKEN — check active scopes & token validity
# ─────────────────────────────────────────────────────────────────────────────

def verify_token_and_scopes(access_token: str) -> dict:
    """
    Call Google's tokeninfo endpoint to verify the token and check granted scopes.
    ROOT CAUSE ALERT: Missing scopes is the #1 reason for empty datasets.
    """
    url = f"https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={access_token}"
    r = _safe_get(url, {}, label="tokeninfo")

    if not r or r.status_code != 200:
        return {
            "valid": False,
            "error": "Token invalid or expired — re-authenticate the user",
            "status_code": r.status_code if r else 0,
        }

    info = r.json()
    granted_scopes = info.get("scope", "").split()

    missing = [s for s in REQUIRED_SCOPES if s not in granted_scopes]
    extra   = [s for s in granted_scopes if "fitness" in s]

    expires_in = int(info.get("expires_in", 0))

    result = {
        "valid": True,
        "user_id": info.get("user_id"),
        "email": info.get("email"),
        "expires_in_seconds": expires_in,
        "expires_soon": expires_in < 300,
        "granted_fitness_scopes": extra,
        "missing_required_scopes": missing,
        "scope_ok": len(missing) == 0,
        "diagnosis": (
            "⚠️  MISSING SCOPES — data will be empty until user re-consents"
            if missing else "✅ All required fitness scopes are granted"
        ),
    }

    logger.info("[GoogleFit][Verify] scope_ok=%s missing=%s", result["scope_ok"], missing)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 2. LIST DATA SOURCES — see what sensors/apps are registered
# ─────────────────────────────────────────────────────────────────────────────

def list_data_sources(access_token: str) -> list:
    """
    Returns all data sources available in the user's Google Fit account.
    ROOT CAUSE ALERT: Noise → Health Connect → Google Fit creates a
    "derived" source; if the source isn't here, data will never appear.
    """
    url = f"{BASE_URL}/dataSources"
    r = _safe_get(url, _auth_headers(access_token), label="dataSources")

    if not r or r.status_code != 200:
        return []

    sources = r.json().get("dataSource", [])
    simplified = []
    for s in sources:
        simplified.append({
            "dataSourceId": s.get("dataStreamId"),
            "dataTypeName": s.get("dataType", {}).get("name"),
            "device": s.get("device", {}).get("model", "unknown"),
            "application": s.get("application", {}).get("packageName", "unknown"),
            "type": s.get("type"),  # "raw" | "derived"
        })

    logger.info("[GoogleFit][Sources] Found %d data sources", len(simplified))
    return simplified


# ─────────────────────────────────────────────────────────────────────────────
# 3. AGGREGATE — correct implementation with calories support
# ─────────────────────────────────────────────────────────────────────────────

def fetch_aggregated_data(
    access_token: str,
    start_ms: int,
    end_ms: int,
    bucket_duration_ms: int = 86_400_000,  # default = 1 day
) -> dict:
    """
    Fetch steps, heart rate, and calories using the /dataset:aggregate endpoint.

    Key rules that fix 90% of empty-data bugs:
      - Use dataTypeName (not dataSourceId) so GMS auto-selects the best merged source
      - bucketByTime.durationMillis must be ≤ (endTime - startTime)
      - timestamps must be in MILLISECONDS, not nanoseconds or seconds
      - start/end must be UTC (not local time)
    """
    url = f"{BASE_URL}/dataset:aggregate"

    body = {
        "aggregateBy": [
            {"dataTypeName": DATA_TYPE_STEPS},
            {"dataTypeName": DATA_TYPE_HEART_RATE},
            {"dataTypeName": DATA_TYPE_CALORIES},
        ],
        "bucketByTime": {"durationMillis": bucket_duration_ms},
        "startTimeMillis": start_ms,
        "endTimeMillis": end_ms,
    }

    logger.info(
        "[GoogleFit][Aggregate] Range: %s → %s",
        _ms_to_iso(start_ms), _ms_to_iso(end_ms)
    )

    r = _safe_post(url, _auth_headers(access_token), body, label="aggregate")
    if not r or r.status_code != 200:
        return {"error": f"API returned {r.status_code if r else 'no response'}", "buckets": []}

    raw = r.json()
    buckets = raw.get("bucket", [])
    parsed = []

    for bucket in buckets:
        b_start = int(bucket["startTimeMillis"])
        b_end   = int(bucket["endTimeMillis"])

        # ── Steps (dataset index 0) ──
        steps = 0
        step_raw_points = []
        ds0 = bucket.get("dataset", [{}])[0]
        for point in ds0.get("point", []):
            origin = point.get("originDataSourceId", "")
            # FILTER: skip cumulative sensors (they are running totals, not deltas)
            if "cumulative" in origin.lower():
                logger.debug("[GoogleFit][Steps] Skipping cumulative source: %s", origin)
                continue
            for v in point.get("value", []):
                val = v.get("intVal") or int(v.get("fpVal", 0) or 0)
                steps += val
                step_raw_points.append({"source": origin, "value": val})

        # ── Heart Rate (dataset index 1) ──
        hr_values = []
        ds1 = bucket.get("dataset", [{}, {}])[1]
        for point in ds1.get("point", []):
            for v in point.get("value", []):
                bpm = v.get("fpVal") or v.get("intVal")
                if bpm and 30 < bpm < 220:  # physiological range check
                    hr_values.append(float(bpm))
        avg_hr = round(sum(hr_values) / len(hr_values), 1) if hr_values else None

        # ── Calories (dataset index 2) ──
        calories = 0.0
        ds2 = bucket.get("dataset", [{}, {}, {}])[2]
        for point in ds2.get("point", []):
            for v in point.get("value", []):
                cal = v.get("fpVal") or v.get("intVal") or 0
                calories += float(cal)

        date_str = datetime.fromtimestamp(b_start / 1000, tz=timezone.utc).strftime("%Y-%m-%d")

        entry = {
            "date": date_str,
            "bucket_start_utc": _ms_to_iso(b_start),
            "bucket_end_utc":   _ms_to_iso(b_end),
            "steps": int(steps),
            "avg_heart_rate_bpm": avg_hr,
            "calories_kcal": round(calories, 1),
            "hr_sample_count": len(hr_values),
            "step_sources": step_raw_points[:5],  # log first 5 for debug
            "data_present": steps > 0 or (avg_hr is not None) or calories > 0,
        }
        parsed.append(entry)

        logger.info(
            "[GoogleFit][Aggregate] %s | steps=%d | hr=%s bpm | cal=%.1f kcal",
            date_str, steps, avg_hr, calories,
        )

    # ── Sync-delay detection ──
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_entry = next((e for e in parsed if e["date"] == today_str), None)
    sync_warning = None
    if today_entry and not today_entry["data_present"]:
        sync_warning = (
            "⚠️  No data for today yet — possible sync delay from Noise → Health Connect → Google Fit. "
            "Health Connect typically syncs every 15–60 min. Check again later."
        )

    return {
        "range_start_utc": _ms_to_iso(start_ms),
        "range_end_utc":   _ms_to_iso(end_ms),
        "bucket_count": len(parsed),
        "sync_warning": sync_warning,
        "buckets": parsed,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 4. RAW DATASET — fetch raw points from a single merged source
# ─────────────────────────────────────────────────────────────────────────────

def fetch_raw_dataset(access_token: str, data_source_id: str, start_ns: int, end_ns: int) -> dict:
    """
    Fetch raw data points from a specific dataSourceId.

    ROOT CAUSE NOTE: The dataset endpoint uses NANOSECOND timestamps in the URL,
    NOT milliseconds. This is different from the aggregate endpoint (milliseconds).
    Getting this wrong returns empty {} or 400 errors.

    datasetId format: {startTimeNanos}-{endTimeNanos}
    """
    dataset_id = f"{start_ns}-{end_ns}"
    url = f"{BASE_URL}/dataSources/{data_source_id}/datasets/{dataset_id}"

    logger.info("[GoogleFit][Raw] Fetching %s | %s", data_source_id, dataset_id)
    r = _safe_get(url, _auth_headers(access_token), label="rawDataset")

    if not r or r.status_code != 200:
        return {"error": f"API {r.status_code if r else 'no response'}", "points": []}

    raw = r.json()
    points = raw.get("point", [])
    logger.info("[GoogleFit][Raw] Got %d raw points", len(points))
    return {"point_count": len(points), "points": points[:20]}  # cap at 20 for response size


# ─────────────────────────────────────────────────────────────────────────────
# 5. FULL DIAGNOSTIC REPORT
# ─────────────────────────────────────────────────────────────────────────────

def run_full_diagnostic(access_token: str, days: int = 7) -> dict:
    """
    Comprehensive diagnostic:
      1. Token validity + scope check
      2. Data source enumeration (detect Noise/Health Connect)
      3. 7-day aggregated data
      4. Raw merged steps for today
      5. Root cause suggestions
    """
    report = {"timestamp_utc": datetime.now(timezone.utc).isoformat()}

    # Step 1: Token
    report["token_check"] = verify_token_and_scopes(access_token)

    # Step 2: Data sources
    sources = list_data_sources(access_token)
    noise_sources  = [s for s in sources if "noise" in s.get("application", "").lower()]
    health_connect = [s for s in sources if "health_connect" in s.get("application", "").lower()
                      or "healthconnect" in s.get("dataSourceId", "").lower()]
    step_sources   = [s for s in sources if s.get("dataTypeName") == DATA_TYPE_STEPS]

    report["data_sources"] = {
        "total_count": len(sources),
        "step_sources": step_sources,
        "noise_sources": noise_sources,
        "health_connect_bridge_sources": health_connect,
        "all_sources": sources,
    }

    # Step 3: 7-day aggregate
    end_ms   = _now_ms()
    start_ms = _days_ago_ms(days)
    report["aggregated_data"] = fetch_aggregated_data(access_token, start_ms, end_ms)

    # Step 4: Raw steps today (last 24h)
    now_ns   = _now_ms() * 1_000_000
    past_ns  = (_now_ms() - 86_400_000) * 1_000_000
    report["raw_steps_today"] = fetch_raw_dataset(
        access_token, MERGED_SOURCE_STEPS, past_ns, now_ns
    )

    # Step 5: Root cause analysis
    causes = []
    if not report["token_check"]["valid"]:
        causes.append("CRITICAL: Token expired or invalid — user must re-authenticate")
    if report["token_check"].get("missing_required_scopes"):
        causes.append(
            f"CRITICAL: Missing OAuth scopes → {report['token_check']['missing_required_scopes']}. "
            "Re-consent with correct scopes."
        )
    if not noise_sources and not health_connect:
        causes.append(
            "WARNING: No Noise or Health Connect bridge data source found. "
            "Ensure Noise app has synced at least once to Google Fit / Health Connect."
        )
    if not step_sources:
        causes.append("WARNING: No step count data source found — Noise may not be syncing steps.")

    buckets = report["aggregated_data"].get("buckets", [])
    empty_days = [b["date"] for b in buckets if not b["data_present"]]
    if empty_days:
        causes.append(
            f"INFO: {len(empty_days)} day(s) have no data: {empty_days}. "
            "Could be sync delay (up to 60 min) or Health Connect permissions not granted."
        )

    report["root_causes"] = causes if causes else ["✅ No obvious root causes — data looks healthy"]
    return report


# ─────────────────────────────────────────────────────────────────────────────
# FLASK ROUTES
# ─────────────────────────────────────────────────────────────────────────────

def _extract_token(data: dict) -> tuple[str | None, dict | None]:
    token = data.get("google_token") or data.get("access_token")
    if not token:
        return None, ({"success": False, "error": "google_token is required"}, 400)
    return token, None


@google_fit_debug_bp.route("/google-fit/verify", methods=["POST"])
@jwt_required()
def route_verify():
    """
    Verify Google OAuth token and check fitness scopes.
    Body: { "google_token": "<access_token>" }
    """
    data = request.get_json(silent=True) or {}
    token, err = _extract_token(data)
    if err:
        return jsonify(err[0]), err[1]

    result = verify_token_and_scopes(token)
    return jsonify({"success": True, "data": result}), 200


@google_fit_debug_bp.route("/google-fit/sources", methods=["POST"])
@jwt_required()
def route_sources():
    """
    List all Google Fit data sources for this user's account.
    Body: { "google_token": "<access_token>" }
    """
    data = request.get_json(silent=True) or {}
    token, err = _extract_token(data)
    if err:
        return jsonify(err[0]), err[1]

    sources = list_data_sources(token)
    return jsonify({"success": True, "count": len(sources), "data": sources}), 200


@google_fit_debug_bp.route("/google-fit/aggregate", methods=["POST"])
@jwt_required()
def route_aggregate():
    """
    Fetch aggregated steps, heart rate, and calories.
    Body: {
        "google_token": "<access_token>",
        "days": 7,               // optional, default 7
        "bucket_hours": 24       // optional, default 24 (daily buckets)
    }
    """
    data = request.get_json(silent=True) or {}
    token, err = _extract_token(data)
    if err:
        return jsonify(err[0]), err[1]

    days          = int(data.get("days", 7))
    bucket_hours  = int(data.get("bucket_hours", 24))
    bucket_ms     = bucket_hours * 3_600_000

    end_ms   = _now_ms()
    start_ms = _days_ago_ms(days)

    result = fetch_aggregated_data(token, start_ms, end_ms, bucket_ms)
    return jsonify({"success": True, "data": result}), 200


@google_fit_debug_bp.route("/google-fit/raw", methods=["POST"])
@jwt_required()
def route_raw():
    """
    Fetch raw data points from a specific merged data source.
    Body: {
        "google_token": "<access_token>",
        "metric": "steps" | "heart_rate" | "calories",   // default: steps
        "hours": 24   // look-back window, default 24
    }
    """
    data = request.get_json(silent=True) or {}
    token, err = _extract_token(data)
    if err:
        return jsonify(err[0]), err[1]

    metric = data.get("metric", "steps")
    source_map = {
        "steps":      MERGED_SOURCE_STEPS,
        "heart_rate": MERGED_SOURCE_HEART_RATE,
        "calories":   MERGED_SOURCE_CALORIES,
    }
    source_id = source_map.get(metric)
    if not source_id:
        return jsonify({"success": False, "error": f"Unknown metric '{metric}'. Use: steps, heart_rate, calories"}), 400

    hours    = int(data.get("hours", 24))
    now_ms   = _now_ms()
    past_ms  = now_ms - (hours * 3_600_000)

    # Raw dataset endpoint uses NANOSECONDS
    now_ns  = now_ms  * 1_000_000
    past_ns = past_ms * 1_000_000

    result = fetch_raw_dataset(token, source_id, past_ns, now_ns)
    return jsonify({"success": True, "source_id": source_id, "data": result}), 200


@google_fit_debug_bp.route("/google-fit/diagnose", methods=["POST"])
@jwt_required()
def route_diagnose():
    """
    Run the full diagnostic report — token, scopes, sources, 7-day data, root causes.
    Body: { "google_token": "<access_token>", "days": 7 }
    """
    data = request.get_json(silent=True) or {}
    token, err = _extract_token(data)
    if err:
        return jsonify(err[0]), err[1]

    days   = int(data.get("days", 7))
    report = run_full_diagnostic(token, days)
    return jsonify({"success": True, "diagnostic_report": report}), 200
