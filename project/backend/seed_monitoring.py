"""
Seed realistic 2-day monitoring data for all admitted patients.

Generates trending vitals (slightly increasing glucose, stable BP/SpO2)
across 6 time slots (2 days × 3 slots) per patient.

Usage:
    python -c "from backend.seed_monitoring import seed_patient_monitoring; seed_patient_monitoring()"
    
    Or via the API endpoint: POST /api/monitoring/seed
"""
import random
from datetime import datetime, timedelta
from backend.models import db, Appointment, PatientMonitoring


def seed_patient_monitoring():
    """
    Seed 2 days × 3 time-slots of realistic vitals for every admitted patient.
    Skips patients who already have monitoring data (idempotent).
    """
    # 1. Find all admitted patients
    admitted = Appointment.query.filter_by(isAdmitted=True).all()
    if not admitted:
        print("[SEED] No admitted patients found. Nothing to seed.")
        return {"seeded": 0, "skipped": 0}

    today = datetime.utcnow().date()
    day1 = (today - timedelta(days=1)).strftime('%Y-%m-%d')
    day2 = today.strftime('%Y-%m-%d')
    days = [day1, day2]
    slots = ["morning", "afternoon", "evening"]

    seeded_count = 0
    skipped_count = 0

    for appt in admitted:
        pid = str(appt.patient_id)

        # Check if data already exists for this patient
        existing = PatientMonitoring.query.filter_by(patient_id=pid).first()
        if existing:
            print(f"[SEED] Skipping patient {pid} — already has monitoring data")
            skipped_count += 1
            continue

        # Generate trending data
        # Glucose: slightly increasing trend across 6 readings
        glucose_base = random.uniform(110, 130)
        glucose_step = random.uniform(5, 10)  # per-reading increment

        # BP: relatively stable with small variance
        bp_sys_base = random.uniform(112, 125)
        bp_dia_base = random.uniform(72, 82)

        # SpO2: stable with minor fluctuations
        spo2_base = random.uniform(95, 98)

        reading_idx = 0
        for day_str in days:
            for slot in slots:
                # Glucose: trending upward
                glucose = round(glucose_base + glucose_step * reading_idx + random.uniform(-3, 3), 1)

                # BP: stable with ±5 jitter
                bp_sys = round(bp_sys_base + random.uniform(-5, 5) + reading_idx * 1.5, 1)
                bp_dia = round(bp_dia_base + random.uniform(-3, 3) + reading_idx * 0.8, 1)

                # SpO2: stable with minor fluctuation
                spo2 = round(spo2_base + random.uniform(-1.5, 1.0), 1)
                spo2 = min(spo2, 100.0)  # Cap at 100

                # Diet: random completion (more likely earlier meals are done)
                breakfast_done = random.random() > 0.2
                lunch_done = random.random() > 0.3
                snacks_done = random.random() > 0.5
                dinner_done = random.random() > 0.4

                record = PatientMonitoring(
                    patient_id=pid,
                    date=day_str,
                    time_slot=slot,
                    glucose=glucose,
                    bp_systolic=bp_sys,
                    bp_diastolic=bp_dia,
                    spo2=spo2,
                    breakfast_done=breakfast_done,
                    lunch_done=lunch_done,
                    snacks_done=snacks_done,
                    dinner_done=dinner_done,
                )
                db.session.add(record)
                reading_idx += 1

        seeded_count += 1
        print(f"[SEED] ✅ Seeded 6 records for patient {pid}")

    db.session.commit()
    summary = {"seeded": seeded_count, "skipped": skipped_count}
    print(f"[SEED] Done. {summary}")
    return summary
