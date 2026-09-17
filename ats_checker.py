"""
Deterministic ATS Rule Engine for CareerAI.
Performs transparent, explainable rule-based scoring and formatting checks on resume text,
augmented with semantic evaluation when Gemini AI is active.
"""

import re
from typing import Dict, Any, List, Optional
from gemini_service import is_gemini_active, generate_ats_analysis

STANDARD_SECTIONS = {
    "summary": ["summary", "professional summary", "about me", "profile", "objective", "career objective"],
    "experience": ["experience", "work experience", "employment history", "professional experience", "work history"],
    "skills": ["skills", "technical skills", "core competencies", "technologies", "key skills", "skills & tools"],
    "education": ["education", "academic background", "academic qualifications", "degrees", "university"],
    "projects": ["projects", "personal projects", "academic projects", "key projects", "portfolio"],
    "certifications": ["certifications", "licenses", "certificates", "courses & certifications"]
}

ACTION_VERBS = [
    "architected", "developed", "engineered", "implemented", "optimized", "built", "designed",
    "deployed", "spearheaded", "accelerated", "automated", "created", "delivered", "executed",
    "integrated", "launched", "managed", "orchestrated", "reduced", "scaled", "streamlined",
    "transformed", "analyzed", "collaborated", "constructed", "established", "formulated",
    "generated", "improved", "increased", "maintained", "mentored", "programmed", "refactored"
]


def check_sections(text: str) -> Dict[str, Any]:
    """Check for standard ATS resume sections."""
    lines = [line.strip().lower() for line in text.splitlines() if line.strip()]
    text_lower = text.lower()
    
    found_sections = {}
    missing_sections = []

    for section_name, variants in STANDARD_SECTIONS.items():
        found = False
        for variant in variants:
            # Check as standalone header line or bold heading pattern
            for line in lines:
                if line == variant or line.startswith(f"{variant}:") or line.startswith(f"{variant} -"):
                    found = True
                    break
            if not found and re.search(r'\b' + re.escape(variant) + r'\b', text_lower):
                found = True
                break
        if found:
            found_sections[section_name] = True
        else:
            if section_name in ["experience", "skills", "education"]:  # Essential sections
                missing_sections.append(section_name.title())

    return {
        "found": list(found_sections.keys()),
        "missing_critical": missing_sections,
        "section_count": len(found_sections)
    }


def check_contact_info(text: str) -> Dict[str, Any]:
    """Check for email, phone, LinkedIn/GitHub, location."""
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    phone_pattern = r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    has_email = bool(re.search(email_pattern, text))
    has_phone = bool(re.search(phone_pattern, text))
    has_linkedin = "linkedin.com" in text.lower() or "linkedin" in text.lower()
    has_github = "github.com" in text.lower() or "github" in text.lower()

    missing = []
    if not has_email:
        missing.append("Email Address")
    if not has_phone:
        missing.append("Phone Number")
    if not has_linkedin and not has_github:
        missing.append("LinkedIn or Portfolio Link")

    return {
        "has_email": has_email,
        "has_phone": has_phone,
        "has_linkedin": has_linkedin,
        "has_github": has_github,
        "missing_contact": missing
    }


def check_metrics_and_verbs(text: str) -> Dict[str, Any]:
    """Check for quantifiable impact metrics and strong action verbs."""
    text_lower = text.lower()
    words = text_lower.split()
    
    # Action verbs
    verbs_found = [v for v in ACTION_VERBS if re.search(r'\b' + v + r'\b', text_lower)]
    
    # Numbers and metrics (e.g. 20%, $50K, 3x, 500+)
    metrics_pattern = r'\b(\d+[\.,]?\d*\s*(%|\$|k|m|x|users|ms|sec|hours|days|million|billion))\b|\b\d{2,}\b'
    metrics_matches = re.findall(metrics_pattern, text, re.IGNORECASE)
    
    return {
        "verbs_count": len(verbs_found),
        "verbs_sample": verbs_found[:6],
        "has_metrics": len(metrics_matches) >= 3,
        "metrics_count": len(metrics_matches)
    }


def run_ats_simulation(resume_text: str, jd_text: str = "", target_role: str = "") -> Dict[str, Any]:
    """
    Run full ATS simulation with deterministic scoring rules, enhanced with Gemini if available.
    """
    # 1. Deterministic Rule Evaluation
    section_eval = check_sections(resume_text)
    contact_eval = check_contact_info(resume_text)
    content_eval = check_metrics_and_verbs(resume_text)
    
    words = resume_text.split()
    word_count = len(words)
    
    critical_issues = []
    warnings = []
    suggestions = []

    # Structure Score (25%)
    structure_score = 100
    if "experience" in [s.lower() for s in section_eval["missing_critical"]]:
        structure_score -= 30
        critical_issues.append("Critical: No distinct 'Experience' or 'Work History' section heading detected.")
    if "skills" in [s.lower() for s in section_eval["missing_critical"]]:
        structure_score -= 25
        critical_issues.append("Critical: Missing a dedicated 'Skills' or 'Technical Skills' section.")
    if "education" in [s.lower() for s in section_eval["missing_critical"]]:
        structure_score -= 15
        warnings.append("No standard 'Education' section heading found.")
    if len(section_eval["found"]) < 4:
        structure_score -= 15
        warnings.append("Resume contains fewer than 4 standard sections.")

    # Formatting & Contact Score (25%)
    formatting_score = 100
    if not contact_eval["has_email"]:
        formatting_score -= 30
        critical_issues.append("Critical: Contact email address not found or formatted ambiguously.")
    if not contact_eval["has_phone"]:
        formatting_score -= 15
        warnings.append("Phone number not clearly identified.")
    if not contact_eval["has_linkedin"] and not contact_eval["has_github"]:
        formatting_score -= 10
        suggestions.append("Add a clickable LinkedIn profile or GitHub portfolio URL in header.")
    
    # Readability & Content Score (25%)
    readability_score = 100
    if word_count < 250:
        readability_score -= 30
        critical_issues.append(f"Resume is very brief ({word_count} words). Aim for at least 350-700 words.")
    elif word_count > 1200:
        readability_score -= 15
        warnings.append(f"Resume word count is high ({word_count} words). Consider condensing to 1-2 pages.")

    if content_eval["verbs_count"] < 3:
        readability_score -= 20
        warnings.append("Few strong action verbs detected (e.g. 'Architected', 'Implemented', 'Optimized').")
    elif content_eval["verbs_count"] < 6:
        readability_score -= 10
        suggestions.append("Incorporate more active power verbs at the start of each bullet point.")

    if not content_eval["has_metrics"]:
        readability_score -= 15
        suggestions.append("Include quantified results (e.g. 'reduced load time by 35%', 'scaled to 10k users').")

    # Keyword & JD Alignment Score (25%)
    keywords_score = 75
    jd_alignment_score = 75

    if jd_text:
        jd_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', jd_text.lower()))
        resume_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', resume_text.lower()))
        
        common_words = jd_words.intersection(resume_words)
        match_ratio = len(common_words) / max(len(jd_words), 1)
        
        keywords_score = min(100, max(30, int(match_ratio * 150)))
        jd_alignment_score = min(100, max(30, int(match_ratio * 140) + 10))
        
        if keywords_score < 60:
            warnings.append("Low keyword overlap with target Job Description.")
            suggestions.append("Align your project bullet points with key phrases from the target JD.")

    # Clamp sub-scores
    structure_score = max(20, min(100, structure_score))
    formatting_score = max(20, min(100, formatting_score))
    readability_score = max(20, min(100, readability_score))
    keywords_score = max(20, min(100, keywords_score))
    jd_alignment_score = max(20, min(100, jd_alignment_score))

    # Overall ATS Score Calculation
    overall_ats_score = int(
        (keywords_score * 0.25) +
        (structure_score * 0.25) +
        (readability_score * 0.20) +
        (formatting_score * 0.15) +
        (jd_alignment_score * 0.15)
    )

    result = {
        "ats_score": overall_ats_score,
        "sub_scores": {
            "keywords": keywords_score,
            "structure": structure_score,
            "readability": readability_score,
            "jd_alignment": jd_alignment_score,
            "formatting": formatting_score
        },
        "critical_issues": critical_issues,
        "warnings": warnings,
        "suggestions": suggestions,
        "sections_detected": section_eval["found"],
        "word_count": word_count,
        "action_verbs_found": content_eval["verbs_sample"],
        "has_quantifiable_metrics": content_eval["has_metrics"],
        "ai_powered": False
    }

    # If Gemini is available, combine with semantic AI analysis
    if is_gemini_active():
        try:
            ai_ats = generate_ats_analysis(resume_text, jd_text)
            if ai_ats and "ats_score" in ai_ats:
                # Merge AI suggestions and calibrate score
                result["ai_ats_score"] = ai_ats["ats_score"]
                # Weighted blend between deterministic check and semantic AI
                blended_score = int((overall_ats_score * 0.4) + (ai_ats["ats_score"] * 0.6))
                result["ats_score"] = blended_score
                
                if ai_ats.get("critical_issues"):
                    for issue in ai_ats["critical_issues"]:
                        if issue not in result["critical_issues"]:
                            result["critical_issues"].append(issue)
                if ai_ats.get("warnings"):
                    for warn in ai_ats["warnings"]:
                        if warn not in result["warnings"]:
                            result["warnings"].append(warn)
                if ai_ats.get("suggestions"):
                    for sugg in ai_ats["suggestions"]:
                        if sugg not in result["suggestions"]:
                            result["suggestions"].append(sugg)
                if ai_ats.get("sub_scores"):
                    result["sub_scores"] = ai_ats["sub_scores"]
                
                result["ai_powered"] = True
        except Exception as e:
            logger.warning("Error running Gemini ATS analysis: %s", e)

    return result
