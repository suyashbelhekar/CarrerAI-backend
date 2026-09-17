"""
NLP Engine for resume parsing, skill extraction, and offline fallback analysis.
Combines Google Gemini AI with local NLP/spaCy, TF-IDF cosine similarity, and regex evidence mapping.
"""

import re
import io
import sys
import os
import logging
from typing import List, Dict, Any, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from skill_db import JOB_ROLES, COURSE_RECOMMENDATIONS, ATS_KEYWORDS
from gemini_service import (
    is_gemini_active,
    compare_resume_with_jd,
    identify_skill_gaps_and_evidence,
    generate_career_roadmap,
    generate_interview_questions
)

logger = logging.getLogger(__name__)

# Attempt to load spaCy model gracefully
nlp = None
try:
    import spacy
    try:
        nlp = spacy.load("en_core_web_sm")
    except Exception:
        try:
            import subprocess
            logger.info("Downloading spaCy en_core_web_sm model...")
            subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"], check=True)
            nlp = spacy.load("en_core_web_sm")
        except Exception as e:
            logger.warning("Could not load/download spaCy model; falling back to regex + TF-IDF parsing: %s", e)
except ImportError:
    logger.warning("spaCy is not installed. Using regex & TF-IDF parser.")


def is_gemini_available() -> bool:
    """Check if Gemini AI is active and configured."""
    return is_gemini_active()


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF bytes with multi-library fallback."""
    # Try pdfplumber first
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            if text.strip():
                return text
    except Exception as e:
        logger.debug("pdfplumber failed, trying pypdf: %s", e)

    # Fallback to pypdf
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
        if text.strip():
            return text
    except Exception as e:
        logger.error("pypdf extraction failed: %s", e)

    raise ValueError("Failed to extract text from PDF. Ensure the file contains selectable text.")


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX bytes."""
    try:
        from docx import Document
        doc = Document(io.BytesIO(file_bytes))
        text = "\n".join([para.text for para in doc.paragraphs if para.text])
        return text
    except Exception as e:
        raise ValueError(f"Failed to extract DOCX text: {str(e)}")


def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    """Extract text from PDF, DOCX, DOC, or TXT file bytes."""
    fname_lower = filename.lower()
    if fname_lower.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    elif fname_lower.endswith((".docx", ".doc")):
        return extract_text_from_docx(file_bytes)
    elif fname_lower.endswith((".txt", ".md")):
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return file_bytes.decode("latin-1", errors="ignore")
    else:
        raise ValueError("Unsupported file format. Please upload PDF, DOCX, or TXT.")


def preprocess_text(text: str) -> str:
    """Clean and normalize text."""
    text = text.lower()
    text = re.sub(r'[^\w\s\+\#\./]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_skills_from_text(text: str, all_skills: list) -> list:
    """
    Extract skills using regex keyword matching, spaCy NER, and TF-IDF cosine similarity.
    """
    text_lower = preprocess_text(text)
    found_skills = set()

    # 1. Direct keyword matching (with boundary checking for clean matches)
    for skill in all_skills:
        skill_lower = skill.lower()
        pattern = r'(?<![a-zA-Z0-9])' + re.escape(skill_lower) + r'(?![a-zA-Z0-9])'
        if re.search(pattern, text_lower):
            found_skills.add(skill_lower)

    # 2. spaCy NER (if available)
    if nlp is not None:
        try:
            doc = nlp(text[:100000])
            for ent in doc.ents:
                ent_text = ent.text.lower().strip()
                if ent.label_ in ["ORG", "PRODUCT", "GPE"] and len(ent_text) > 2:
                    for skill in all_skills:
                        if ent_text in skill.lower() or skill.lower() in ent_text:
                            found_skills.add(skill.lower())
        except Exception:
            pass

    # 3. TF-IDF similarity for fuzzy matching
    if len(text_lower.split()) > 10:
        try:
            skill_docs = [skill.lower() for skill in all_skills]
            corpus = [text_lower] + skill_docs
            vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
            tfidf_matrix = vectorizer.fit_transform(corpus)
            resume_vec = tfidf_matrix[0]
            skill_vecs = tfidf_matrix[1:]
            similarities = cosine_similarity(resume_vec, skill_vecs)[0]
            for idx, sim in enumerate(similarities):
                if sim > 0.15:
                    found_skills.add(all_skills[idx].lower())
        except Exception:
            pass

    return list(found_skills)


def extract_skill_evidence_offline(resume_text: str, matched_skills: list) -> list:
    """
    Locate exact sentences and sections where skills appear in the resume text (offline fallback).
    """
    lines = resume_text.splitlines()
    paragraphs = [p.strip() for p in resume_text.split('\n\n') if p.strip()]
    
    current_section = "General / Skills"
    evidence_list = []

    for skill in matched_skills:
        skill_lower = skill.lower()
        pattern = r'(?i)\b' + re.escape(skill_lower) + r'\b'
        
        found_quote = ""
        found_section = "Skills & Projects"
        confidence = 88

        # Scan paragraphs to find context sentence
        for p in paragraphs:
            if re.search(pattern, p):
                # Split into sentences
                sentences = re.split(r'(?<=[.!?])\s+', p)
                for s in sentences:
                    if re.search(pattern, s):
                        found_quote = s.strip()
                        break
                if found_quote:
                    # Estimate section
                    p_lower = p.lower()
                    if "project" in p_lower:
                        found_section = "Projects"
                        confidence = 94
                    elif "experience" in p_lower or "developer" in p_lower or "engineer" in p_lower:
                        found_section = "Experience"
                        confidence = 92
                    elif "education" in p_lower or "university" in p_lower:
                        found_section = "Education"
                        confidence = 85
                    else:
                        found_section = "Technical Skills"
                        confidence = 90
                    break

        if not found_quote:
            found_quote = f"Mentioned in resume as {skill}."
            found_section = "Skills"
            confidence = 80

        evidence_list.append({
            "skill": skill.title() if len(skill) > 3 else skill.upper(),
            "evidence_quote": found_quote[:200],
            "section_source": found_section,
            "confidence": confidence
        })

    return evidence_list


def calculate_match_score(extracted_skills: list, required_skills: list, core_skills: list) -> dict:
    """Calculate match percentage using weighted scoring."""
    extracted_set = set(s.lower() for s in extracted_skills)
    required_set = set(s.lower() for s in required_skills)
    core_set = set(s.lower() for s in core_skills)

    matched = extracted_set.intersection(required_set)
    missing = required_set - extracted_set

    # Weighted score: core skills = 2x weight
    core_matched = matched.intersection(core_set)
    non_core_matched = matched - core_set
    core_missing = missing.intersection(core_set)

    total_weight = len(core_set) * 2 + (len(required_set) - len(core_set))
    achieved_weight = len(core_matched) * 2 + len(non_core_matched)

    score = min(100, round((achieved_weight / max(total_weight, 1)) * 100))

    # Bonus for extra relevant skills
    extra_skills = extracted_set - required_set
    bonus = min(5, len(extra_skills) // 3)
    score = min(100, score + bonus)

    return {
        "score": score,
        "matched_skills": sorted(list(matched)),
        "missing_skills": sorted(list(missing)),
        "extra_skills": sorted(list(extra_skills)),
        "core_matched": sorted(list(core_matched)),
        "core_missing": sorted(list(core_missing)),
        "total_required": len(required_set),
        "total_matched": len(matched)
    }


def get_course_recommendations(missing_skills: list) -> list:
    """Get course recommendations for missing skills."""
    recommendations = []
    seen_titles = set()

    for skill in missing_skills[:8]:
        skill_lower = skill.lower()
        courses = COURSE_RECOMMENDATIONS.get(skill_lower, COURSE_RECOMMENDATIONS["default"])
        for course in courses[:1]:
            if course["title"] not in seen_titles:
                recommendations.append({
                    "skill": skill,
                    "title": course["title"],
                    "platform": course["platform"],
                    "url": course["url"],
                    "level": course["level"]
                })
                seen_titles.add(course["title"])

    return recommendations


def generate_ai_suggestions(score: int, missing_skills: list, matched_skills: list, job_role: str) -> list:
    """Generate localized improvement suggestions."""
    suggestions = []

    if score < 40:
        suggestions.append(f"Your profile needs development for {job_role}. Prioritize building core technical competencies first.")
    elif score < 60:
        suggestions.append(f"You have a solid base for {job_role}. Focus on the missing core skills to become an attractive candidate.")
    elif score < 80:
        suggestions.append(f"Strong match for {job_role}! Bridge key skill gaps and add metric-driven achievements to stand out.")
    else:
        suggestions.append(f"Outstanding match for {job_role}! Fine-tune leadership, system architecture, and impactful project highlights.")

    if missing_skills:
        top_missing = missing_skills[:3]
        suggestions.append(f"Priority skills to learn: {', '.join(top_missing)}. These are highly sought after by recruiters.")

    if len(matched_skills) > 5:
        suggestions.append("Quantify your achievements — include measurable impacts like 'boosted performance by 35%' or 'reduced downtime by 40%'.")

    suggestions.append("Use strong action verbs: 'Architected', 'Spearheaded', 'Optimized', 'Engineered', and 'Implemented'.")
    suggestions.append(f"Tailor your headline and summary to specifically target {job_role} with your top matching skills.")

    if score >= 60:
        suggestions.append("Include live portfolio links, case studies, or GitHub repositories demonstrating practical experience.")

    return suggestions


def get_ats_tips(job_role: str, missing_skills: list) -> list:
    """Get ATS keyword optimization tips."""
    tips = []
    keywords = ATS_KEYWORDS.get(job_role, [])

    if keywords:
        tips.append(f"Include essential ATS phrases: {', '.join(keywords[:3])}")
    tips.append("Use standard, single-column section headers: 'Experience', 'Technical Skills', 'Education', 'Projects'")
    tips.append("Avoid complex multi-column tables, text boxes, and embedded graphics that ATS parsers can misread")
    tips.append("Save and submit resumes as clean PDF or DOCX format for optimal ATS parsing")

    if missing_skills:
        tips.append(f"Create a dedicated 'Technical Skills' section explicitly listing: {', '.join(missing_skills[:4])}")

    return tips


def analyze_resume(file_bytes: bytes, filename: str, job_role: str) -> dict:
    """
    Main analysis pipeline.
    Uses Google Gemini AI if GEMINI_API_KEY is configured, with seamless offline NLP fallback.
    """
    text = extract_text_from_file(file_bytes, filename)
    if not text or len(text.strip()) < 30:
        raise ValueError("Could not extract meaningful text from the resume. Please ensure the document is not an empty or scanned image file.")

    if job_role not in JOB_ROLES:
        # If user provides custom role, use standard skills database or generic fallback
        role_data = {
            "required_skills": ["problem solving", "communication", "git", "project management"],
            "core_skills": ["communication", "git"],
            "description": f"Role requirements for {job_role}"
        }
    else:
        role_data = JOB_ROLES[job_role]

    # Try Gemini AI first
    if is_gemini_active():
        try:
            gemini_result = compare_resume_with_jd(text, f"Role: {job_role}\nDescription: {role_data['description']}\nRequired Skills: {', '.join(role_data['required_skills'])}", target_role=job_role)
            if gemini_result:
                # Merge into standard analysis structure
                matched = gemini_result.get("matched_skills", [])
                missing = gemini_result.get("missing_skills", [])
                extra = [s for s in role_data["required_skills"] if s.lower() not in [m.lower() for m in matched]]
                
                return {
                    "job_role": job_role,
                    "role_description": role_data["description"],
                    "extracted_skills": sorted(list(set([m.lower() for m in matched]))),
                    "matched_skills": sorted(list(set(matched))),
                    "missing_skills": sorted(list(set(missing))),
                    "extra_skills": gemini_result.get("weak_skills", []),
                    "core_matched": [s for s in role_data.get("core_skills", []) if s.lower() in [m.lower() for m in matched]],
                    "core_missing": [s for s in role_data.get("core_skills", []) if s.lower() not in [m.lower() for m in matched]],
                    "match_score": int(gemini_result.get("overall_match", 75)),
                    "resume_score": int(gemini_result.get("ats_score", 80)),
                    "total_required": len(role_data.get("required_skills", [])) or len(matched) + len(missing),
                    "total_matched": len(matched),
                    "word_count": len(text.split()),
                    "courses": get_course_recommendations(missing),
                    "suggestions": gemini_result.get("recommendations", []),
                    "ats_tips": gemini_result.get("resume_issues", get_ats_tips(job_role, missing)),
                    "text_preview": text[:500],
                    "ai_powered": True
                }
        except Exception as e:
            logger.warning("Gemini analyze failed, falling back to local NLP: %s", e)

    # Fallback to local NLP + TF-IDF engine
    all_skills = list(set(
        skill for role in JOB_ROLES.values()
        for skill in role["required_skills"]
    ))

    extracted_skills = extract_skills_from_text(text, all_skills)

    match_data = calculate_match_score(
        extracted_skills,
        role_data["required_skills"],
        role_data["core_skills"]
    )

    courses = get_course_recommendations(match_data["missing_skills"])
    suggestions = generate_ai_suggestions(
        match_data["score"],
        match_data["missing_skills"],
        match_data["matched_skills"],
        job_role
    )
    ats_tips = get_ats_tips(job_role, match_data["missing_skills"])

    word_count = len(text.split())
    resume_score = min(100, max(20,
        match_data["score"] * 0.6 +
        min(20, word_count / 25) +
        min(10, len(extracted_skills) * 0.5) +
        (10 if len(text) > 500 else 0)
    ))

    return {
        "job_role": job_role,
        "role_description": role_data["description"],
        "extracted_skills": sorted(extracted_skills),
        "matched_skills": match_data["matched_skills"],
        "missing_skills": match_data["missing_skills"],
        "extra_skills": match_data["extra_skills"],
        "core_matched": match_data["core_matched"],
        "core_missing": match_data["core_missing"],
        "match_score": match_data["score"],
        "resume_score": round(resume_score),
        "total_required": match_data["total_required"],
        "total_matched": match_data["total_matched"],
        "word_count": word_count,
        "courses": courses,
        "suggestions": suggestions,
        "ats_tips": ats_tips,
        "text_preview": text[:500],
        "ai_powered": False
    }


def compare_roles(file_bytes: bytes, filename: str) -> list:
    """Compare resume against all job roles quickly."""
    text = extract_text_from_file(file_bytes, filename)
    if not text or len(text.strip()) < 30:
        raise ValueError("Could not extract meaningful text from the resume.")

    all_skills = list(set(
        skill for role in JOB_ROLES.values()
        for skill in role["required_skills"]
    ))
    extracted_skills = extract_skills_from_text(text, all_skills)

    results = []
    for role, role_data in JOB_ROLES.items():
        match_data = calculate_match_score(
            extracted_skills,
            role_data["required_skills"],
            role_data["core_skills"]
        )
        results.append({
            "role": role,
            "score": match_data["score"],
            "matched": match_data["total_matched"],
            "total": match_data["total_required"]
        })

    return sorted(results, key=lambda x: x["score"], reverse=True)
