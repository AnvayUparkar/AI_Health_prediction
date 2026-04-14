"""
Meal Plan & Export Report Routes
=================================

New Flask blueprint providing:
  - GET  /api/meal-plan      → Gemini AI-powered daily meal plan
  - POST /api/export-report  → Downloadable PDF health report

No existing routes or logic are modified.
"""

from flask import Blueprint, request, jsonify, send_file
import logging
import json
import io
from datetime import datetime, timedelta
from flask_jwt_extended import jwt_required, get_jwt_identity

from backend.models import db, HealthAnalysis
from backend.step_meal_planner import generate_step_meal_plan, categorize_activity

meal_plan_bp = Blueprint('meal_plan', __name__)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# GET /api/meal-plan
# ---------------------------------------------------------------------------

@meal_plan_bp.route('/meal-plan', methods=['GET'])
@jwt_required()
def get_meal_plan():
    """
    GET /api/meal-plan
    Required: JWT Auth

    Reads yesterday's step data from HealthAnalysis, generates a
    Gemini AI-powered daily meal plan based on activity level.
    """
    identity = get_jwt_identity()
    user_id = identity.get('id') if isinstance(identity, dict) else identity

    try:
        # Find yesterday's record
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today - timedelta(days=1)

        yesterday_record = HealthAnalysis.query.filter(
            HealthAnalysis.user_id == user_id,
            HealthAnalysis.created_at >= yesterday_start,
            HealthAnalysis.created_at < today
        ).order_by(HealthAnalysis.created_at.desc()).first()

        # Fallback: if no yesterday data, use the most recent record
        if not yesterday_record:
            yesterday_record = HealthAnalysis.query.filter_by(
                user_id=user_id
            ).order_by(HealthAnalysis.created_at.desc()).first()

        if not yesterday_record:
            return jsonify({
                "success": False,
                "error": "No step data found. Please sync your health data first."
            }), 404

        yesterday_steps = yesterday_record.steps or 0

        # Generate meal plan via Gemini (with safety-net fallback)
        result = generate_step_meal_plan(yesterday_steps)

        return jsonify({
            "success": True,
            "yesterday_steps": yesterday_steps,
            "activity_level": result["meal_plan_data"].get("activity_level", "Unknown"),
            "meal_plan": result["meal_plan_data"].get("meal_plan", {}),
            "clinical_assessment": result["meal_plan_data"].get("clinical_assessment", ""),
            "hydration_tips": result["meal_plan_data"].get("hydration_tips", []),
            "lifestyle_tips": result["meal_plan_data"].get("lifestyle_tips", []),
            "safety_note": result["meal_plan_data"].get("safety_note", ""),
            "source": result["source"],
            "data_date": yesterday_record.created_at.strftime('%Y-%m-%d'),
        }), 200

    except Exception as e:
        logger.error("Meal plan generation error: %s", str(e))
        return jsonify({
            "success": False,
            "error": f"Failed to generate meal plan: {str(e)}"
        }), 500


# ---------------------------------------------------------------------------
# POST /api/export-report
# ---------------------------------------------------------------------------

@meal_plan_bp.route('/export-report', methods=['POST'])
@jwt_required()
def export_report():
    """
    POST /api/export-report
    Required: JWT Auth

    Generates a downloadable PDF health report containing:
      - Weekly summary
      - Yesterday's steps & activity level
      - Generated meal plan
      - Daily breakdown
    """
    identity = get_jwt_identity()
    user_id = identity.get('id') if isinstance(identity, dict) else identity

    try:
        # 1. Fetch weekly data (same pattern as /api/health-report)
        fourteen_days_ago = datetime.utcnow() - timedelta(days=14)
        reports = HealthAnalysis.query.filter(
            HealthAnalysis.user_id == user_id,
            HealthAnalysis.created_at >= fourteen_days_ago
        ).order_by(HealthAnalysis.created_at.desc()).all()

        # Deduplicate to unique days
        unique_days = {}
        for r in reports:
            date_key = r.created_at.strftime('%Y-%m-%d')
            if date_key not in unique_days:
                unique_days[date_key] = r

        sorted_keys = sorted(unique_days.keys(), reverse=True)[:7]
        weekly_records = [unique_days[k] for k in sorted(sorted_keys)]

        # 2. Get yesterday's steps for meal plan
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today - timedelta(days=1)

        yesterday_record = HealthAnalysis.query.filter(
            HealthAnalysis.user_id == user_id,
            HealthAnalysis.created_at >= yesterday_start,
            HealthAnalysis.created_at < today
        ).order_by(HealthAnalysis.created_at.desc()).first()

        if not yesterday_record and weekly_records:
            yesterday_record = weekly_records[-1]

        yesterday_steps = yesterday_record.steps if yesterday_record else 0
        activity = categorize_activity(yesterday_steps)

        # 3. Generate meal plan
        meal_result = generate_step_meal_plan(yesterday_steps)
        meal_data = meal_result["meal_plan_data"]

        # 4. Build PDF
        pdf_buffer = _build_pdf(weekly_records, yesterday_steps, activity, meal_data)

        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'health_report_{datetime.utcnow().strftime("%Y%m%d")}.pdf'
        )

    except Exception as e:
        logger.error("Export report error: %s", str(e))
        return jsonify({
            "success": False,
            "error": f"Failed to generate report: {str(e)}"
        }), 500


def _build_pdf(weekly_records, yesterday_steps, activity, meal_data):
    """
    Generate a PDF report using reportlab.

    Returns a BytesIO buffer containing the PDF.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import inch, mm
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=22,
        textColor=HexColor('#1e3a5f'),
        spaceAfter=12,
        alignment=TA_CENTER,
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=HexColor('#2563eb'),
        spaceBefore=16,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        spaceAfter=6,
    )
    sub_style = ParagraphStyle(
        'SubInfo',
        parent=styles['Normal'],
        fontSize=9,
        textColor=HexColor('#6b7280'),
        alignment=TA_CENTER,
        spaceAfter=20,
    )

    elements = []

    # ── Title ──────────────────────────────────────────────────────────
    elements.append(Paragraph("Weekly Health Report", title_style))
    elements.append(Paragraph(
        f"Generated on {datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')}",
        sub_style
    ))
    elements.append(Spacer(1, 8))

    # ── Steps Summary Table ───────────────────────────────────────────
    elements.append(Paragraph("📊 Weekly Steps Summary", heading_style))

    table_data = [['Date', 'Steps', 'Heart Rate', 'Sleep', 'Score', 'Risk']]
    for record in weekly_records:
        table_data.append([
            record.created_at.strftime('%b %d'),
            f"{record.steps:,}" if record.steps else "—",
            f"{record.avg_heart_rate:.0f} bpm" if record.avg_heart_rate else "—",
            f"{record.sleep_hours:.1f}h" if record.sleep_hours else "—",
            str(record.health_score) if record.health_score else "—",
            record.risk_level or "—",
        ])

    if len(table_data) > 1:
        t = Table(table_data, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#2563eb')),
            ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#d1d5db')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#f9fafb'), HexColor('#ffffff')]),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(t)
    else:
        elements.append(Paragraph("No weekly data available.", body_style))

    elements.append(Spacer(1, 12))

    # ── Activity Level ────────────────────────────────────────────────
    elements.append(Paragraph("🏃 Activity Level", heading_style))
    elements.append(Paragraph(
        f"Yesterday's Steps: <b>{yesterday_steps:,}</b> — "
        f"Activity Level: <b>{activity['label']}</b>",
        body_style
    ))

    assessment = meal_data.get('clinical_assessment', activity.get('clinical_context', ''))
    if assessment:
        elements.append(Paragraph(f"<i>{assessment}</i>", body_style))

    elements.append(Spacer(1, 8))

    # ── Meal Plan ─────────────────────────────────────────────────────
    elements.append(Paragraph("🍽 Daily Meal Plan", heading_style))

    meal_plan = meal_data.get('meal_plan', {})
    meal_icons = {'breakfast': '🍳', 'lunch': '🥗', 'dinner': '🍲'}

    for meal_key in ['breakfast', 'lunch', 'dinner']:
        meal = meal_plan.get(meal_key, {})
        if not meal:
            continue

        icon = meal_icons.get(meal_key, '🍽')
        title = meal.get('title', meal_key.capitalize())
        items = meal.get('items', [])
        reasoning = meal.get('reasoning', '')

        elements.append(Paragraph(f"<b>{icon} {title}</b>", body_style))
        for item in items:
            elements.append(Paragraph(f"  • {item}", body_style))
        if reasoning:
            reasoning_style = ParagraphStyle(
                f'Reasoning_{meal_key}',
                parent=body_style,
                textColor=HexColor('#6b7280'),
                fontSize=8,
                leftIndent=12,
            )
            elements.append(Paragraph(f"<i>{reasoning}</i>", reasoning_style))
        elements.append(Spacer(1, 4))

    # ── Hydration & Lifestyle Tips ────────────────────────────────────
    hydration = meal_data.get('hydration_tips', [])
    if hydration:
        elements.append(Paragraph("💧 Hydration Tips", heading_style))
        for tip in hydration:
            elements.append(Paragraph(f"  • {tip}", body_style))

    lifestyle = meal_data.get('lifestyle_tips', [])
    if lifestyle:
        elements.append(Paragraph("💡 Lifestyle Tips", heading_style))
        for tip in lifestyle:
            elements.append(Paragraph(f"  • {tip}", body_style))

    # ── Daily Breakdown ───────────────────────────────────────────────
    elements.append(Spacer(1, 8))
    elements.append(Paragraph("📋 Daily Breakdown", heading_style))

    for record in reversed(weekly_records):
        if not record.health_score:
            continue
        date_str = record.created_at.strftime('%B %d, %Y')
        elements.append(Paragraph(
            f"<b>{date_str}</b> — Score: {record.health_score}/100 | "
            f"Risk: {record.risk_level} | Status: {record.health_status}",
            body_style
        ))
        elements.append(Paragraph(
            f"  Steps: {record.steps:,} | HR: {record.avg_heart_rate:.0f} bpm | "
            f"Sleep: {record.sleep_hours:.1f}h",
            body_style
        ))

    # ── Safety Note ───────────────────────────────────────────────────
    elements.append(Spacer(1, 16))
    safety = meal_data.get('safety_note', '')
    if safety:
        note_style = ParagraphStyle(
            'SafetyNote',
            parent=body_style,
            textColor=HexColor('#9ca3af'),
            fontSize=8,
            alignment=TA_CENTER,
        )
        elements.append(Paragraph(f"⚠ {safety}", note_style))

    # Build the PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer


# ---------------------------------------------------------------------------
# POST /api/export-report-analysis
# ---------------------------------------------------------------------------

@meal_plan_bp.route('/export-report-analysis', methods=['POST'])
@jwt_required()
def export_report_analysis():
    """
    POST /api/export-report-analysis
    Required: JWT Auth
    Body: JSON with the analysis result data from the frontend

    Generates a downloadable PDF of the medical report analysis including:
      - Detected parameters table
      - Issues detected
      - Diet recommendation (meal plan, foods, tips)
      - Clinical protocol
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        pdf_buffer = _build_report_analysis_pdf(data)

        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'report_analysis_{datetime.utcnow().strftime("%Y%m%d_%H%M")}.pdf'
        )

    except Exception as e:
        logger.error("Export report analysis error: %s", str(e))
        return jsonify({
            "success": False,
            "error": f"Failed to generate PDF: {str(e)}"
        }), 500


def _build_report_analysis_pdf(data):
    """
    Generate a PDF from report analysis data.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'RATitle', parent=styles['Title'],
        fontSize=22, textColor=HexColor('#0d9488'),
        spaceAfter=12, alignment=TA_CENTER,
    )
    heading_style = ParagraphStyle(
        'RAHeading', parent=styles['Heading2'],
        fontSize=14, textColor=HexColor('#0d9488'),
        spaceBefore=16, spaceAfter=8,
    )
    body_style = ParagraphStyle(
        'RABody', parent=styles['Normal'],
        fontSize=10, leading=14, spaceAfter=6,
    )
    sub_style = ParagraphStyle(
        'RASub', parent=styles['Normal'],
        fontSize=9, textColor=HexColor('#6b7280'),
        alignment=TA_CENTER, spaceAfter=20,
    )

    elements = []

    # ── Title ──────────────────────────────────────────────────────────
    elements.append(Paragraph("Medical Report Analysis", title_style))
    elements.append(Paragraph(
        f"Generated on {datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')}",
        sub_style
    ))

    # ── Report Summary ────────────────────────────────────────────────
    summary = data.get('report_summary', '')
    if summary:
        elements.append(Paragraph("📋 Report Summary", heading_style))
        elements.append(Paragraph(summary, body_style))

    # ── Diet Summary ──────────────────────────────────────────────────
    diet = data.get('diet_recommendation', {})
    diet_summary = diet.get('summary', '')
    if diet_summary:
        elements.append(Spacer(1, 4))
        summary_style = ParagraphStyle(
            'DietSummary', parent=body_style,
            textColor=HexColor('#0d9488'), fontSize=10,
        )
        elements.append(Paragraph(f"<i>\"{diet_summary}\"</i>", summary_style))

    # ── Detected Parameters Table ─────────────────────────────────────
    all_params = data.get('all_parameters', {})
    if all_params:
        elements.append(Spacer(1, 8))
        elements.append(Paragraph("🔬 Detected Parameters", heading_style))

        table_data = [['Parameter', 'Value', 'Unit', 'Status', 'Ref Range']]
        for name, info in all_params.items():
            table_data.append([
                name,
                str(info.get('value', '—')),
                info.get('unit', ''),
                info.get('status', '—'),
                info.get('ref_range', ''),
            ])

        t = Table(table_data, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#0d9488')),
            ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#d1d5db')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#f0fdfa'), HexColor('#ffffff')]),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(t)

    # ── Urgent Flags ──────────────────────────────────────────────────
    urgent = diet.get('urgent_flags', [])
    if urgent:
        elements.append(Spacer(1, 8))
        elements.append(Paragraph("🚨 Urgent — Seek Medical Attention", heading_style))
        for flag in urgent:
            elements.append(Paragraph(f"  ⚠ {flag}", body_style))

    # ── Issues Detected ───────────────────────────────────────────────
    issues = diet.get('issues_detected', [])
    if issues:
        elements.append(Spacer(1, 8))
        elements.append(Paragraph("⚠ Issues Detected", heading_style))
        for issue in issues:
            elements.append(Paragraph(f"  • {issue}", body_style))

    # ── Clinical Protocol ─────────────────────────────────────────────
    protocol = diet.get('clinical_protocol', [])
    if protocol:
        elements.append(Spacer(1, 8))
        elements.append(Paragraph("🧠 Clinical Optimization Protocol", heading_style))
        for idx, step in enumerate(protocol, 1):
            elements.append(Paragraph(f"  {idx}. {step}", body_style))

    # ── Recommended Foods ─────────────────────────────────────────────
    rec_foods = diet.get('recommended_foods', [])
    if rec_foods:
        elements.append(Spacer(1, 8))
        elements.append(Paragraph("✅ Recommended Foods", heading_style))
        for food in rec_foods:
            elements.append(Paragraph(f"  • {food}", body_style))

    # ── Foods to Avoid ────────────────────────────────────────────────
    avoid = diet.get('foods_to_avoid', [])
    blocked = diet.get('blocked_foods_safety', {})
    if blocked:
        elements.append(Spacer(1, 8))
        elements.append(Paragraph("🚫 Foods to Avoid", heading_style))
        for food, reason in blocked.items():
            elements.append(Paragraph(f"  • <b>{food}</b>: {reason}", body_style))
    elif avoid:
        elements.append(Spacer(1, 8))
        elements.append(Paragraph("🚫 Foods to Avoid", heading_style))
        for food in avoid:
            elements.append(Paragraph(f"  • {food}", body_style))

    # ── Meal Plan ─────────────────────────────────────────────────────
    meal_plan = diet.get('meal_plan', {})
    meal_labels = {
        'breakfast': '☕ Breakfast', 'mid_morning': '🍌 Mid-Morning',
        'lunch': '🍛 Lunch', 'evening_snack': '🍎 Evening Snack',
        'dinner': '🥗 Dinner'
    }
    has_meals = any(meal_plan.get(k) for k in meal_labels)
    if has_meals:
        elements.append(Spacer(1, 8))
        elements.append(Paragraph("🍽 Daily Meal Plan", heading_style))
        for key, label in meal_labels.items():
            items = meal_plan.get(key, [])
            if items:
                elements.append(Paragraph(f"<b>{label}</b>", body_style))
                for item in items:
                    elements.append(Paragraph(f"    • {item}", body_style))

    # ── Hydration & Lifestyle ─────────────────────────────────────────
    hydration = diet.get('hydration_tips', [])
    if hydration:
        elements.append(Spacer(1, 8))
        elements.append(Paragraph("💧 Hydration Tips", heading_style))
        for tip in hydration:
            elements.append(Paragraph(f"  • {tip}", body_style))

    lifestyle = diet.get('lifestyle_tips', []) or diet.get('diet_tips', [])
    if lifestyle:
        elements.append(Spacer(1, 8))
        elements.append(Paragraph("💡 Lifestyle Tips", heading_style))
        for tip in lifestyle:
            elements.append(Paragraph(f"  • {tip}", body_style))

    # ── Synergy Pairing ───────────────────────────────────────────────
    synergy = diet.get('synergy_pairing', [])
    if synergy:
        elements.append(Spacer(1, 8))
        elements.append(Paragraph("🔬 Biochemical Synergy Protocol", heading_style))
        for pair in synergy:
            elements.append(Paragraph(f"  • {pair}", body_style))

    # ── Parameter Reasoning ───────────────────────────────────────────
    reasoning = diet.get('parameter_reasoning', {})
    if reasoning:
        elements.append(Spacer(1, 8))
        elements.append(Paragraph("❤ Why These Recommendations", heading_style))
        for param, reason in reasoning.items():
            elements.append(Paragraph(f"  <b>[{param}]</b>: {reason}", body_style))

    # ── Safety Note ───────────────────────────────────────────────────
    elements.append(Spacer(1, 16))
    safety = diet.get('safety_note', '') or diet.get('disclaimer', '')
    if safety:
        note_style = ParagraphStyle(
            'RASafety', parent=body_style,
            textColor=HexColor('#9ca3af'), fontSize=8,
            alignment=TA_CENTER,
        )
        elements.append(Paragraph(f"⚠ {safety}", note_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer
