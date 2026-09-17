"""
Google Gemini AI Engine for Resume Skill Gap Analysis.
Uses the official google-genai SDK with gemini-2.5-flash for deep contextual resume evaluation.
"""

import os
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

def is_gemini_configured() -> bool:
    """Check if GEMINI_API_KEY is available."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    return bool(api_key and api_key != "YOUR_GEMINI_API_KEY")

def analyze_with_gemini(text: str, job_role: str, role_data: dict) -> Optional[Dict[str, Any]]:
    """
    Analyze resume text against job role using Gemini AI.
    Returns structured analysis dictionary or None if analysis fails.
    """
    if not is_gemini_configured():
        return None

    try:
        from google import genai
        from google.genai import types

        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        client = genai.Client(api_key=api_key)

        required_skills = role_data.get("required_skills", [])
        core_skills = role_data.get("core_skills", [])
        role_description = role_data.get("description", "")

        prompt = f"""
You are an expert ATS and Senior Technical Recruiter analyzing a candidate's resume for the role: "{job_role}".

ROLE DETAILS:
- Description: {role_description}
- Target Required Skills List: {json.dumps(required_skills)}
- Core Must-Have Skills: {json.dumps(core_skills)}

CANDIDATE RESUME TEXT:
\"\"\"{text[:20000]}\"\"\"

TASK:
Analyze the resume thoroughly and produce a JSON response with exact keys:
1. "extracted_skills": List of all relevant technical and professional skills detected in the resume.
2. "matched_skills": Subset of skills from the target required skills list that the candidate clearly possesses.
3. "missing_skills": Skills from the target required skills list that the candidate lacks or hasn't demonstrated.
4. "extra_skills": Additional valuable skills the candidate has that are beyond the target role's required list.
5. "core_matched": Core must-have skills from {json.dumps(core_skills)} that the candidate matches.
6. "core_missing": Core must-have skills that the candidate is missing.
7. "match_score": Integer from 0 to 100 representing how well the candidate fits the target role requirements.
8. "resume_score": Integer from 0 to 100 evaluating resume formatting, impact metrics, clarity, and overall strength.
9. "suggestions": List of 4-6 specific, actionable, highly personalized recommendations for improving their resume and profile.
10. "courses": List of 3-5 specific recommended courses for their top missing skills. Each item should have:
    - "skill": name of missing skill
    - "title": course title
    - "platform": "Coursera", "Udemy", "edX", or "YouTube"
    - "url": realistic URL or search link (e.g. "https://www.coursera.org/search?query=skill")
    - "level": "Beginner", "Intermediate", or "Advanced"
11. "ats_tips": List of 4-5 actionable tips to optimize this resume for ATS parsers and hiring managers.

Format your response STRICTLY as valid JSON without markdown fences.
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            )
        )

        response_text = response.text.strip()
        # Clean potential markdown wrappers if any
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]

        data = json.loads(response_text.strip())

        # Validate and enrich data
        word_count = len(text.split())
        matched = data.get("matched_skills", [])
        total_req = len(required_skills) if required_skills else len(matched) + len(data.get("missing_skills", []))

        result = {
            "job_role": job_role,
            "role_description": role_description,
            "extracted_skills": sorted(list(set(data.get("extracted_skills", [])))),
            "matched_skills": sorted(list(set(matched))),
            "missing_skills": sorted(list(set(data.get("missing_skills", [])))),
            "extra_skills": sorted(list(set(data.get("extra_skills", [])))),
            "core_matched": sorted(list(set(data.get("core_matched", [])))),
            "core_missing": sorted(list(set(data.get("core_missing", [])))),
            "match_score": int(data.get("match_score", 50)),
            "resume_score": int(data.get("resume_score", 70)),
            "total_required": total_req,
            "total_matched": len(matched),
            "word_count": word_count,
            "courses": data.get("courses", []),
            "suggestions": data.get("suggestions", []),
            "ats_tips": data.get("ats_tips", []),
            "text_preview": text[:500],
            "ai_powered": True
        }

        logger.info("Successfully analyzed resume using Gemini AI for role: %s", job_role)
        return result

    except Exception as e:
        logger.warning("Gemini AI analysis failed, falling back to local NLP engine: %s", str(e))
        return None
