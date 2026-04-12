from flask import Blueprint, request, jsonify
import logging
import json
from datetime import datetime, timedelta
import requests
from flask_jwt_extended import jwt_required, get_jwt_identity

from backend.models import db, HealthAnalysis, User
from backend.health_analyzer import analyze_health_data, analyze_weekly_data

google_fit_sync_bp = Blueprint('google_fit_sync', __name__)
logger = logging.getLogger(__name__)

# Safety Net: Simple rule-based analysis used when Gemini hits quota limits
def generate_safety_net_analysis(day_data):
    steps = day_data.get('steps', 0)
    # NOTE: ordered high → low so the correct branch is reached first
    if steps > 10000:   score = 95
    elif steps > 5000:  score = 85
    elif steps >= 2000: score = 70  # Baseline
    else:               score = 60
    
    status = "Active" if steps > 5000 else "Sedentary"
    risk = "Low" if steps > 3000 else "Moderate"
    
    return {
        "date": day_data.get('date'),
        "health_score": score,
        "risk_level": risk,
        "health_status": f"{status} (Standard Analysis)",
        "diet_plan": ["Stay hydrated", "Focus on lean proteins", "Add more vegetables"],
        "recommendations": ["Try to reach 5,000 steps daily", "Maintain consistent sleep schedules"]
    }

# Google Fit Data Source IDs - Using Official Merged Master Streams
STEPS_SOURCE = "derived:com.google.step_count.delta:com.google.android.gms:merge_step_deltas"
HEART_RATE_SOURCE = "derived:com.google.heart_rate.bpm:com.google.android.gms:merge_heart_rate_bpm"
SLEEP_SOURCE = "derived:com.google.sleep_segment:com.google.android.gms:merged"

def _find_dataset(datasets: list, data_type: str) -> dict:
    """Find a dataset within a bucket by its dataSourceId content (order-independent)."""
    for ds in datasets:
        src_id = ds.get('dataSourceId', '')
        if data_type in src_id:
            return ds
    return {}


def _sum_steps_from_dataset(ds: dict) -> int:
    """Sum step values from a single dataset, skipping cumulative sources."""
    total = 0
    for point in ds.get('point', []):
        origin = point.get('originDataSourceId', '')
        # Only skip cumulative (running total) sources — NOT raw sources
        if 'cumulative' in origin.lower():
            print(f"    [SKIP cumulative] {origin}")
            continue
        val_list = point.get('value', [])
        if val_list:
            v = val_list[0]
            step_val = v.get('intVal') or int(v.get('fpVal', 0) or 0)
            total += step_val
            print(f"    [+{step_val} steps] from: {origin}  (running total: {total})")
    return total


def _avg_hr_from_dataset(ds: dict) -> tuple:
    """Extract heart rate values from a dataset. Returns (avg, sample_count)."""
    values = []
    for point in ds.get('point', []):
        val = point.get('value', [{}])[0]
        bpm = val.get('fpVal') or val.get('intVal')
        if bpm and 30 < bpm < 220:
            values.append(float(bpm))
    if values:
        return round(sum(values) / len(values), 1), len(values)
    return 70.0, 0


def _fetch_steps_fallback(headers: dict, start_ms: int, end_ms: int) -> dict:
    """
    Fallback: fetch steps alone using the merged dataSourceId explicitly.
    This catches the case where dataTypeName aggregate returns empty.
    """
    body = {
        "aggregateBy": [{
            "dataSourceId": "derived:com.google.step_count.delta:com.google.android.gms:merge_step_deltas"
        }],
        "bucketByTime": {"durationMillis": 86400000},
        "startTimeMillis": start_ms,
        "endTimeMillis": end_ms
    }
    try:
        url = "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate"
        r = requests.post(url, headers=headers, json=body, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"  [FALLBACK] Steps fetch failed: {e}")
    return {}


def _fetch_steps_estimated(headers: dict, start_ms: int, end_ms: int) -> dict:
    """
    Second fallback: use 'estimated_steps' derived source that Google Fit
    calculates from phone/watch sensors even when no app explicitly writes.
    """
    body = {
        "aggregateBy": [{
            "dataSourceId": "derived:com.google.step_count.delta:com.google.android.gms:estimated_steps"
        }],
        "bucketByTime": {"durationMillis": 86400000},
        "startTimeMillis": start_ms,
        "endTimeMillis": end_ms
    }
    try:
        url = "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate"
        r = requests.post(url, headers=headers, json=body, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"  [FALLBACK-2] Estimated steps fetch failed: {e}")
    return {}


def get_google_fit_data(access_token, start_time_ms, end_time_ms, timezone_offset=0):
    """Fetch 7 days of daily-aggregated health data from Google Fit REST API.
    
    Uses a 3-layer fallback for steps:
      1. dataTypeName aggregate (auto-merged by GMS)  
      2. Explicit merge_step_deltas dataSourceId
      3. Explicit estimated_steps dataSourceId
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    aggregate_body = {
        "aggregateBy": [
            {"dataTypeName": "com.google.step_count.delta"},
            {"dataTypeName": "com.google.heart_rate.bpm"}
        ],
        "bucketByTime": {"durationMillis": 86400000},
        "startTimeMillis": start_time_ms,
        "endTimeMillis": end_time_ms
    }

    print(f"\n{'='*70}")
    print(f"[GoogleFit] AGGREGATE REQUEST")
    print(f"  Start: {start_time_ms}  ({datetime.utcfromtimestamp(start_time_ms/1000).isoformat()}Z)")
    print(f"  End:   {end_time_ms}  ({datetime.utcfromtimestamp(end_time_ms/1000).isoformat()}Z)")
    print(f"  TZ offset: {timezone_offset} min")
    print(f"{'='*70}")

    try:
        url = "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate"
        response = requests.post(url, headers=headers, json=aggregate_body, timeout=15)

        if response.status_code != 200:
            print(f"[GoogleFit] [ERROR] API Error {response.status_code}: {response.text[:500]}")
            return None

        data = response.json()
        buckets = data.get('bucket', [])
        print(f"[GoogleFit] [OK] Got {len(buckets)} buckets")

        # ── Dump the FULL raw JSON of the first bucket for debugging ──────
        if buckets:
            print(f"\n[GoogleFit] RAW FIRST BUCKET (for debugging):")
            first = buckets[0]
            for i, ds in enumerate(first.get('dataset', [])):
                src_id = ds.get('dataSourceId', 'unknown')
                pts = ds.get('point', [])
                print(f"  dataset[{i}] sourceId={src_id}  points={len(pts)}")
                for j, pt in enumerate(pts[:3]):  # show first 3 points
                    print(f"    point[{j}] origin={pt.get('originDataSourceId','')}  value={pt.get('value', [])}")

        daily_metrics = []
        any_steps_found = False

        for bucket in buckets:
            bucket_start = int(bucket['startTimeMillis'])
            local_dt = datetime.utcfromtimestamp(bucket_start / 1000) - timedelta(minutes=timezone_offset)
            bucket_date = local_dt.strftime('%Y-%m-%d')

            datasets = bucket.get('dataset', [])
            print(f"\n  [{bucket_date}] {len(datasets)} datasets in bucket")
            for i, ds in enumerate(datasets):
                print(f"    ds[{i}]: {ds.get('dataSourceId','')}  ({len(ds.get('point',[]))} points)")

            # ── Steps: try name-based match first ──────────────────────────
            step_ds = _find_dataset(datasets, 'step_count')
            if not step_ds.get('point'):
                # Fallback: try positional index 0
                if datasets and datasets[0].get('point'):
                    step_ds = datasets[0]
                    print(f"    [Steps] Using positional ds[0] fallback")

            total_steps = _sum_steps_from_dataset(step_ds)
            if total_steps > 0:
                any_steps_found = True

            # ── Heart Rate ─────────────────────────────────────────────────
            hr_ds = _find_dataset(datasets, 'heart_rate')
            if not hr_ds.get('point'):
                if len(datasets) > 1 and datasets[1].get('point'):
                    hr_ds = datasets[1]
            avg_hr, hr_count = _avg_hr_from_dataset(hr_ds)

            daily_metrics.append({
                "date": bucket_date,
                "steps": int(total_steps),
                "avg_heart_rate": avg_hr,
                "sleep_hours": 7.0
            })
            print(f"  [OK] {bucket_date} | steps={total_steps} | hr={avg_hr} bpm ({hr_count} samples)")

        # ── FALLBACK: If primary aggregate returned 0 steps everywhere ────
        if not any_steps_found:
            print(f"\n[GoogleFit] [WARN] PRIMARY AGGREGATE returned 0 steps for ALL days -- trying fallback sources...")

            # Fallback 1: merge_step_deltas
            fb_data = _fetch_steps_fallback(headers, start_time_ms, end_time_ms)
            fb_buckets = fb_data.get('bucket', [])
            if fb_buckets:
                print(f"  [FALLBACK-1] merge_step_deltas: got {len(fb_buckets)} buckets")
                for i, fb_bucket in enumerate(fb_buckets):
                    if i < len(daily_metrics):
                        fb_ds = fb_bucket.get('dataset', [{}])[0]
                        fb_steps = _sum_steps_from_dataset(fb_ds)
                        if fb_steps > 0:
                            daily_metrics[i]['steps'] = fb_steps
                            any_steps_found = True
                            print(f"  [FALLBACK-1] {daily_metrics[i]['date']} => {fb_steps} steps")

        if not any_steps_found:
            # Fallback 2: estimated_steps
            fb2_data = _fetch_steps_estimated(headers, start_time_ms, end_time_ms)
            fb2_buckets = fb2_data.get('bucket', [])
            if fb2_buckets:
                print(f"  [FALLBACK-2] estimated_steps: got {len(fb2_buckets)} buckets")
                for i, fb_bucket in enumerate(fb2_buckets):
                    if i < len(daily_metrics):
                        fb_ds = fb_bucket.get('dataset', [{}])[0]
                        fb_steps = _sum_steps_from_dataset(fb_ds)
                        if fb_steps > 0:
                            daily_metrics[i]['steps'] = fb_steps
                            print(f"  [FALLBACK-2] {daily_metrics[i]['date']} => {fb_steps} steps")

        print(f"\n{'='*70}")
        print(f"[GoogleFit] FINAL RESULTS:")
        for m in daily_metrics:
            print(f"  {m['date']} | steps={m['steps']} | hr={m['avg_heart_rate']}")
        print(f"{'='*70}\n")

        return daily_metrics

    except Exception as e:
        print(f"[GoogleFit] [EXCEPTION] {e}")
        logger.exception("[GoogleFit] Failed to fetch data: %s", str(e))
        return None

@google_fit_sync_bp.route('/google-fit-sync', methods=['POST'])
@jwt_required()
def sync_google_fit():
    data = request.json
    access_token = data.get('google_token')
    
    if not access_token:
        return jsonify({"success": False, "error": "Google token required"}), 400

    user_identity = get_jwt_identity()
    user_id = user_identity.get('id') if isinstance(user_identity, dict) else user_identity

    timezone_offset = data.get('timezone_offset', 0) # minutes from UTC (e.g. -330 for IST)

    try:
        # 1. Fetch 7 days of history aligned to LOCAL midnight
        #
        # CRITICAL FIX: datetime.utcnow().timestamp() on Windows treats the
        # naive datetime as LOCAL time (IST), silently shifting by 5:30h.
        # Using time.time() + pure integer math avoids ALL timezone traps.
        import time as _time

        now_utc_ms = int(_time.time() * 1000)

        # timezone_offset from JS getTimezoneOffset():
        #   IST (UTC+5:30) => -330   (negative = ahead of UTC)
        # Convert to ms
        offset_ms = timezone_offset * 60 * 1000  # -19800000 for IST

        # Calculate local "now" in ms, then floor to local midnight
        local_now_ms = now_utc_ms - offset_ms       # shift UTC -> local
        local_midnight_ms = (local_now_ms // 86400000) * 86400000  # floor to day

        # Convert local midnight back to UTC
        today_midnight_utc_ms = local_midnight_ms + offset_ms

        # 7-day window: from 6 days before today's local midnight to now
        start_time_ms = today_midnight_utc_ms - (6 * 86400000)
        end_time_ms = now_utc_ms

        print(f"[GoogleFit] Time range (epoch ms):")
        print(f"  start = {start_time_ms}  (local midnight - 6 days)")
        print(f"  end   = {end_time_ms}  (now)")
        print(f"  offset = {timezone_offset} min ({offset_ms} ms)")

        daily_metrics_list = get_google_fit_data(access_token, start_time_ms, end_time_ms, timezone_offset)
        
        if not daily_metrics_list:
            return jsonify({"success": False, "error": "Could not fetch data from Google Fit. Check permissions."}), 400

        # 2. Batch Analyze with Gemini (Safety Net fallback is now handled inside analyze_weekly_data)
        weekly_analysis = analyze_weekly_data(daily_metrics_list)
        
        saved_records = []
        for day_data in daily_metrics_list:
            date_str = day_data['date']
            # Find analysis for this date from the Gemini response
            analysis = next((a for a in weekly_analysis if a.get('date') == date_str), None)
            
            if not analysis:
                continue

            # ROBUST CHECK: Look for a record within the 24h window of this date
            day_start = datetime.strptime(date_str, '%Y-%m-%d')
            day_end = day_start + timedelta(days=1)
            
            existing = HealthAnalysis.query.filter(
                HealthAnalysis.user_id == user_id,
                HealthAnalysis.created_at >= day_start,
                HealthAnalysis.created_at < day_end
            ).order_by(HealthAnalysis.created_at.desc()).first()

            if existing:
                # Update existing record (Fixes history gaps)
                existing.health_score = analysis.get('health_score', 0)
                existing.risk_level = analysis.get('risk_level', 'Low')
                existing.health_status = analysis.get('health_status', 'N/A')
                existing.steps = day_data['steps']
                existing.avg_heart_rate = day_data['avg_heart_rate']
                existing.sleep_hours = day_data['sleep_hours']
                existing.diet_plan = json.dumps(analysis.get('diet_plan', []))
                existing.recommendations = json.dumps(analysis.get('recommendations', []))
                saved_records.append(existing.to_dict())
                logger.info("Updated record for %s", date_str)
            else:
                # Create new record
                day_start = datetime.strptime(date_str, '%Y-%m-%d')
                new_record = HealthAnalysis(
                    user_id=user_id,
                    health_score=analysis.get('health_score', 0),
                    risk_level=analysis.get('risk_level', 'Low'),
                    health_status=analysis.get('health_status', 'N/A'),
                    steps=day_data['steps'],
                    avg_heart_rate=day_data['avg_heart_rate'],
                    sleep_hours=day_data['sleep_hours'],
                    diet_plan=json.dumps(analysis.get('diet_plan', [])),
                    recommendations=json.dumps(analysis.get('recommendations', [])),
                    # Force Noon of the local date to ensure it stays in the correct 24h filter window
                    created_at=day_start + timedelta(hours=12) 
                )
                db.session.add(new_record)
                db.session.flush() # Flush to get ID, but don't let default override our date
                saved_records.append(new_record.to_dict())
                logger.info("Created new record for %s", date_str)
        
        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Successfully synced {len(saved_records)} days of health history",
            "data": saved_records[-1] if saved_records else None # Return today's data for the main card
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error("Google Fit Batch Analysis error: %s", str(e))
        return jsonify({"success": False, "error": str(e)}), 500
