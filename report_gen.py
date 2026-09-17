"""
PDF Report Generator for CareerAI.
Produces high-quality executive career intelligence reports using ReportLab,
incorporating candidate metadata, target JD match breakdown, ATS simulation results,
skill evidence, missing skills roadmap, and interview prep recommendations.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import io
from datetime import datetime


def generate_report(analysis: dict) -> bytes:
    """Generate a comprehensive Career Intelligence PDF report from analysis results."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch
    )

    styles = getSampleStyleSheet()
    story = []

    # Custom styles
    title_style = ParagraphStyle(
        'MainTitle',
        parent=styles['Title'],
        fontSize=22,
        textColor=colors.HexColor('#4f46e5'),
        spaceAfter=4,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#64748b'),
        alignment=TA_CENTER,
        spaceAfter=14
    )
    section_style = ParagraphStyle(
        'Section',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#1e293b'),
        spaceBefore=12,
        spaceAfter=6,
        fontName='Helvetica-Bold'
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#334155'),
        spaceAfter=3,
        leading=12
    )
    bullet_style = ParagraphStyle(
        'Bullet',
        parent=styles['Normal'],
        fontSize=8.5,
        textColor=colors.HexColor('#475569'),
        spaceAfter=2,
        leading=11
    )

    # Header
    story.append(Paragraph("CareerAI Intelligence Report", title_style))
    role_title = analysis.get("job_role", "Target Role")
    story.append(Paragraph(f"Comprehensive Resume & Skill Gap Audit • {datetime.now().strftime('%B %d, %Y')}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))
    story.append(Spacer(1, 10))

    # Score summary table (4-column card)
    match_score = analysis.get("match_score", analysis.get("overall_match", 0))
    ats_score = analysis.get("resume_score", analysis.get("ats_score", 0))
    skills_matched = analysis.get("total_matched", len(analysis.get("matched_skills", [])))
    skills_required = analysis.get("total_required", len(analysis.get("missing_skills", [])) + skills_matched)

    score_data = [
        ["Target Job Role", "Match Score", "ATS Score", "Skill Coverage"],
        [
            role_title,
            f"{match_score}%",
            f"{ats_score}/100",
            f"{skills_matched} / {skills_required}"
        ]
    ]
    score_table = Table(score_data, colWidths=[2.2 * inch, 1.4 * inch, 1.4 * inch, 1.6 * inch])
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9.5),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWHEIGHT', (0, 0), (-1, -1), 24),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#f8fafc')),
        ('TEXTCOLOR', (0, 1), (-1, 1), colors.HexColor('#0f172a')),
        ('FONTSIZE', (0, 1), (-1, 1), 11),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 12))

    # Matched Skills Section
    story.append(Paragraph("✓ Matched Skills & Verified Evidence", section_style))
    matched = analysis.get("matched_skills", [])
    if matched:
        # If matched items are strings or dicts
        skill_names = [s["skill"] if isinstance(s, dict) else s for s in matched]
        skills_text = " • ".join([str(s).title() for s in skill_names[:25]])
        story.append(Paragraph(skills_text, body_style))
    else:
        story.append(Paragraph("No direct matching skills detected for target profile.", body_style))
    story.append(Spacer(1, 8))

    # Skill Gaps (Missing Skills)
    story.append(Paragraph("✗ Critical Skill Gaps to Bridge", section_style))
    missing = analysis.get("missing_skills", [])
    if missing:
        missing_data = [["Missing Skill", "Importance", "Recommended Action / Project"]]
        for item in missing[:8]:
            if isinstance(item, dict):
                s_name = item.get("skill", "").title()
                s_imp = item.get("importance", "High")
                s_act = item.get("recommended_project", item.get("why_it_matters", "Build practical project"))
            else:
                s_name = str(item).title()
                s_imp = "High"
                s_act = "Complete hands-on implementation and add evidence"
            missing_data.append([s_name, s_imp, s_act[:60]])

        missing_table = Table(missing_data, colWidths=[1.6 * inch, 1.1 * inch, 3.9 * inch])
        missing_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8.5),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWHEIGHT', (0, 0), (-1, -1), 20),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#fef2f2'), colors.white]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#fecaca')),
        ]))
        story.append(missing_table)
    else:
        story.append(Paragraph("No critical skill gaps identified — strong technical alignment!", body_style))
    story.append(Spacer(1, 8))

    # AI Recommendations & Action Items
    story.append(Paragraph("⚡ Actionable Optimization Recommendations", section_style))
    suggestions = analysis.get("suggestions", analysis.get("recommendations", []))
    if suggestions:
        for i, sugg in enumerate(suggestions[:5], 1):
            story.append(Paragraph(f"<b>{i}.</b> {sugg}", bullet_style))
    story.append(Spacer(1, 8))

    # ATS Tips & Formatting Guidelines
    ats_tips = analysis.get("ats_tips", [])
    if ats_tips:
        story.append(Paragraph("🛡️ ATS Parser & Keyword Optimization", section_style))
        for tip in ats_tips[:4]:
            story.append(Paragraph(f"• {tip}", bullet_style))
        story.append(Spacer(1, 8))

    # Recommended Courses
    courses = analysis.get("courses", [])
    if courses:
        story.append(Paragraph("📚 Recommended Courses & Certifications", section_style))
        course_data = [["Skill", "Course Title", "Platform", "Level"]]
        for c in courses[:4]:
            course_data.append([
                c.get("skill", "").title(),
                c.get("title", "")[:40],
                c.get("platform", "Coursera"),
                c.get("level", "Intermediate")
            ])
        course_table = Table(course_data, colWidths=[1.3 * inch, 2.8 * inch, 1.3 * inch, 1.2 * inch])
        course_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#334155')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWHEIGHT', (0, 0), (-1, -1), 18),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f8fafc'), colors.white]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ]))
        story.append(course_table)

    # Footer
    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))
    story.append(Spacer(1, 6))
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7.5,
                                   textColor=colors.HexColor('#94a3b8'), alignment=TA_CENTER)
    story.append(Paragraph("Generated by CareerAI Platform • Powered by Google Gemini AI & NLP Engine", footer_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
