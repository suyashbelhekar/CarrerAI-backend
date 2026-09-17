"""
FastAPI Backend for CareerAI — AI Career & Resume Intelligence Platform.
Integrates Google Gemini AI, persistent SQLite database, deterministic ATS simulator,
NLP skill extraction, resume builder sync, interview prep, and application tracking.
"""

import os
import io
import re
import json
import logging
import traceback
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Core application imports
from nlp_engine import (
    analyze_resume,
    compare_roles,
    extract_text_from_file,
    extract_skills_from_text,
    extract_skill_evidence_offline,
    is_gemini_available
)
from skill_db import JOB_ROLES
from auth import register_user, login_user, get_user_from_token
from report_gen import generate_report
from database import (
    db_create_user, db_get_user_by_email, db_update_user_profile,
    db_save_resume, db_get_latest_resume,
    db_save_resume_version, db_list_resume_versions, db_get_resume_version, db_delete_resume_version,
    db_save_job_description, db_list_job_descriptions, db_get_job_description, db_delete_job_description,
    db_save_analysis, db_list_analyses, db_get_latest_analysis,
    db_create_application, db_list_applications, db_update_application, db_delete_application,
    db_save_career_roadmap, db_get_career_roadmap, db_update_roadmap_progress,
    db_save_interview_session, db_list_interview_sessions
)
from gemini_service import (
    is_gemini_active,
    analyze_job_description as gemini_analyze_jd,
    compare_resume_with_jd as gemini_compare_resume_jd,
    identify_skill_gaps_and_evidence as gemini_skill_gaps,
    rewrite_resume_section as gemini_rewrite,
    generate_tailored_resume as gemini_tailor_resume,
    generate_career_roadmap as gemini_roadmap,
    generate_interview_questions as gemini_interview_questions,
    evaluate_mock_interview_answer as gemini_evaluate_answer
)
from ats_checker import run_ats_simulation

# Initialize FastAPI app
app = FastAPI(
    title="CareerAI — AI Career & Resume Intelligence Platform API",
    description="Centralized Gemini AI, ATS Simulator, NLP Engine, and Career Readiness Platform",
    version="3.0.0"
)

# Configure CORS
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:4173",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "https://ai-resume-analyzer-frontend.onrender.com",
    "https://suyashbelhekar.github.io"
]

frontend_url = os.getenv("FRONTEND_URL")
if frontend_url:
    allowed_origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Seamless local and deployed dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Auth Dependency ─────────────────────────────────────────────────────────

def get_optional_user(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1]
    return get_user_from_token(token)


def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    user = get_optional_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return user


# ── Pydantic Request Models ─────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    full_name: str
    email: str
    password: str
    confirm_password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class JDAnalyzeRequest(BaseModel):
    jd_text: str = Field(..., min_length=10)
    title: Optional[str] = ""
    company: Optional[str] = ""

class JDSaveRequest(BaseModel):
    title: str
    company: Optional[str] = ""
    raw_text: str
    parsed_data: Optional[dict] = None

class MatchRequest(BaseModel):
    resume_text: str = Field(..., min_length=20)
    jd_text: str = Field(..., min_length=10)
    target_role: Optional[str] = "Software Engineer"

class SkillGapRequest(BaseModel):
    resume_text: str = Field(..., min_length=20)
    jd_text: str = Field(..., min_length=10)
    target_role: Optional[str] = ""

class RewriteRequest(BaseModel):
    content: str = Field(..., min_length=5)
    section_type: str = "Experience Bullet"
    mode: str = "improve"  # improve | ats_optimize | make_technical | make_concise | quantify | professional
    target_jd: Optional[str] = ""

class TailoredResumeRequest(BaseModel):
    resume_data: dict
    jd_text: str = Field(..., min_length=10)

class ATSAnalyzeRequest(BaseModel):
    resume_text: str = Field(..., min_length=20)
    jd_text: Optional[str] = ""
    target_role: Optional[str] = ""

class RoadmapRequest(BaseModel):
    resume_text: str = Field(..., min_length=20)
    jd_text: str = Field(..., min_length=10)
    target_role: str

class RoadmapProgressRequest(BaseModel):
    completed_milestones: List[int]

class InterviewGenerateRequest(BaseModel):
    resume_text: str = Field(..., min_length=20)
    jd_text: str = Field(..., min_length=10)
    target_role: str

class InterviewEvaluateRequest(BaseModel):
    question: str
    user_answer: str = Field(..., min_length=3)
    category: Optional[str] = "Technical"
    target_role: Optional[str] = "Software Engineer"
    context: Optional[str] = ""

class ApplicationCreateRequest(BaseModel):
    company: str
    job_title: str
    job_location: Optional[str] = ""
    application_date: Optional[str] = ""
    status: Optional[str] = "Applied"
    resume_version_id: Optional[str] = ""
    match_score: Optional[int] = 0
    ats_score: Optional[int] = 0
    notes: Optional[str] = ""
    interview_date: Optional[str] = ""
    follow_up_date: Optional[str] = ""
    salary_range: Optional[str] = ""

class ApplicationUpdateRequest(BaseModel):
    company: Optional[str] = None
    job_title: Optional[str] = None
    job_location: Optional[str] = None
    application_date: Optional[str] = None
    status: Optional[str] = None
    resume_version_id: Optional[str] = None
    match_score: Optional[int] = None
    ats_score: Optional[int] = None
    notes: Optional[str] = None
    interview_date: Optional[str] = None
    follow_up_date: Optional[str] = None
    salary_range: Optional[str] = None

class ResumeVersionSaveRequest(BaseModel):
    id: Optional[str] = None
    title: str
    target_role: Optional[str] = ""
    target_jd_id: Optional[str] = ""
    resume_data: dict
    ats_score: Optional[int] = 0
    match_score: Optional[int] = 0

class ResumeVersionCompareRequest(BaseModel):
    version_id_1: str
    version_id_2: str


# ── System Health & Roles ───────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "name": "CareerAI API",
        "status": "online",
        "version": "3.0.0",
        "gemini_active": is_gemini_active(),
        "tagline": "Analyze. Improve. Prepare. Get Career Ready."
    }


@app.get("/api/status")
def get_status():
    """Return backend status including AI engine configuration."""
    return {
        "status": "online",
        "gemini_active": is_gemini_active(),
        "available_roles": len(JOB_ROLES),
        "database": "SQLite (career_ai.db)"
    }


@app.get("/api/roles")
def get_roles():
    """Return all available predefined job roles."""
    return {
        "roles": [
            {"id": role, "name": role, "description": data["description"]}
            for role, data in JOB_ROLES.items()
        ]
    }


# ── Authentication Endpoints ────────────────────────────────────────────────

@app.post("/api/auth/register")
def api_register(body: RegisterRequest):
    if not body.full_name.strip():
        raise HTTPException(status_code=400, detail="Full name is required.")
    if "@" not in body.email:
        raise HTTPException(status_code=400, detail="Enter a valid email address.")
    if body.password != body.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")
    try:
        return register_user(body.full_name, body.email, body.password)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.post("/api/auth/login")
def api_login(body: LoginRequest):
    if not body.email or not body.password:
        raise HTTPException(status_code=400, detail="Email and password are required.")
    try:
        return login_user(body.email, body.password)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.get("/api/auth/me")
def api_me(user: dict = Depends(get_current_user)):
    user_db = db_get_user_by_email(user["email"])
    profile_data = {}
    if user_db and user_db.get("profile_data"):
        try:
            profile_data = json.loads(user_db["profile_data"]) if isinstance(user_db["profile_data"], str) else user_db["profile_data"]
        except Exception:
            profile_data = {}
    return {
        "full_name": user["full_name"],
        "email": user["email"],
        "profile": profile_data
    }


@app.get("/api/auth/profile")
def api_get_profile(user: dict = Depends(get_current_user)):
    user_db = db_get_user_by_email(user["email"])
    profile_data = {}
    if user_db and user_db.get("profile_data"):
        try:
            profile_data = json.loads(user_db["profile_data"]) if isinstance(user_db["profile_data"], str) else user_db["profile_data"]
        except Exception:
            profile_data = {}
    return {
        "full_name": user["full_name"],
        "email": user["email"],
        "profile": profile_data
    }


@app.put("/api/auth/profile")
def api_update_profile(body: dict, user: dict = Depends(get_current_user)):
    db_update_user_profile(user["email"], body)
    return {"status": "success", "profile": body}


# ── 1. Job Description Analyzer ────────────────────────────────────────────

@app.post("/api/jd/analyze")
async def analyze_jd_endpoint(
    file: Optional[UploadFile] = File(None),
    jd_text: Optional[str] = Form(None)
):
    """Analyze a Job Description from raw text or uploaded document (PDF/DOCX/TXT)."""
    text = ""
    if file:
        file_bytes = await file.read()
        try:
            text = extract_text_from_file(file_bytes, file.filename)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to read JD file: {str(e)}")
    elif jd_text:
        text = jd_text.strip()
    
    if not text or len(text) < 10:
        raise HTTPException(status_code=400, detail="Please provide a valid Job Description.")

    # 1. Try Gemini AI analysis
    if is_gemini_active():
        try:
            result = gemini_analyze_jd(text)
            if result:
                result["raw_text"] = text
                return result
        except Exception as e:
            logger.warning("Gemini JD analyze failed: %s", e)

    # 2. Offline Fallback Parser
    all_skills = list(set(skill for role in JOB_ROLES.values() for skill in role["required_skills"]))
    extracted = extract_skills_from_text(text, all_skills)
    
    return {
        "job_title": "Target Role",
        "company": "",
        "seniority_level": "Mid-Level",
        "experience_years": "2+ years",
        "education_requirements": ["Bachelor's degree in Computer Science or related field"],
        "required_skills": extracted[:8] if extracted else ["Communication", "Problem Solving", "Git"],
        "preferred_skills": extracted[8:14] if len(extracted) > 8 else ["Agile", "Testing"],
        "technologies": extracted[:10],
        "certifications": [],
        "responsibilities": ["Develop and maintain software systems.", "Collaborate with cross-functional teams.", "Ensure code quality and test coverage."],
        "keywords": extracted[:12],
        "summary": text[:200] + ("..." if len(text) > 200 else ""),
        "raw_text": text,
        "ai_powered": False
    }


@app.post("/api/jd/save")
def save_jd_endpoint(body: JDSaveRequest, user: Optional[dict] = Depends(get_optional_user)):
    user_email = user["email"] if user else "guest@careerai.local"
    res = db_save_job_description(
        user_email=user_email,
        title=body.title,
        company=body.company or "",
        raw_text=body.raw_text,
        parsed_data=body.parsed_data
    )
    return res


@app.get("/api/jd/list")
def list_jds_endpoint(user: Optional[dict] = Depends(get_optional_user)):
    user_email = user["email"] if user else "guest@careerai.local"
    return {"job_descriptions": db_list_job_descriptions(user_email)}


@app.delete("/api/jd/{jd_id}")
def delete_jd_endpoint(jd_id: str, user: Optional[dict] = Depends(get_optional_user)):
    user_email = user["email"] if user else "guest@careerai.local"
    deleted = db_delete_job_description(jd_id, user_email)
    if not deleted:
        raise HTTPException(status_code=404, detail="Job description not found.")
    return {"status": "success", "id": jd_id}


# ── 2. Resume + JD Intelligence Match ───────────────────────────────────────

@app.post("/api/match")
def match_resume_jd_endpoint(body: MatchRequest, user: Optional[dict] = Depends(get_optional_user)):
    """Deep multi-dimensional alignment between resume and target JD."""
    user_email = user["email"] if user else "guest@careerai.local"

    if is_gemini_active():
        try:
            result = gemini_compare_resume_jd(body.resume_text, body.jd_text, body.target_role or "Target Role")
            if result:
                # Save analysis in background for history
                db_save_analysis(user_email, body.target_role or "Target Role", result)
                return result
        except Exception as e:
            logger.warning("Gemini compare failed: %s", e)

    # Offline NLP Fallback
    all_skills = list(set(skill for role in JOB_ROLES.values() for skill in role["required_skills"]))
    resume_skills = extract_skills_from_text(body.resume_text, all_skills)
    jd_skills = extract_skills_from_text(body.jd_text, all_skills)
    
    matched = list(set(resume_skills).intersection(set(jd_skills)))
    missing = list(set(jd_skills) - set(resume_skills))
    weak = list(set(resume_skills) - set(jd_skills))[:5]
    
    pct = min(100, max(20, round((len(matched) / max(len(jd_skills), 1)) * 100))) if jd_skills else 65

    result = {
        "overall_match": pct,
        "skill_match": pct,
        "experience_match": min(100, pct + 5),
        "project_match": max(30, pct - 5),
        "education_match": 85,
        "keyword_match": min(100, pct + 2),
        "ats_score": min(100, max(40, pct + 8)),
        "seniority_fit": "Good match for target requirements",
        "matched_skills": [s.title() for s in matched],
        "missing_skills": [s.title() for s in missing],
        "weak_skills": [s.title() for s in weak],
        "keywords_found": [s.title() for s in matched[:8]],
        "keywords_missing": [s.title() for s in missing[:8]],
        "resume_issues": ["Ensure all key technical competencies are supported with concrete project descriptions."],
        "recommendations": [
            f"Prioritize building evidence for: {', '.join([s.title() for s in missing[:3]])}" if missing else "Optimize formatting for ATS.",
            "Quantify your project achievements using specific performance metrics."
        ],
        "alignment_summary": f"Your profile shows a {pct}% alignment with this job description.",
        "ai_powered": False
    }

    db_save_analysis(user_email, body.target_role or "Target Role", result)
    return result


# ── 3. Skill Gap & Evidence Mapping ─────────────────────────────────────────

@app.post("/api/skill-gap")
def skill_gap_endpoint(body: SkillGapRequest):
    """Return matched skills with exact evidence quotes, and missing skills with project/evidence guidance."""
    if is_gemini_active():
        try:
            result = gemini_skill_gaps(body.resume_text, body.jd_text, body.target_role or "")
            if result:
                return result
        except Exception as e:
            logger.warning("Gemini skill gap failed: %s", e)

    # Offline NLP Evidence Mapper
    all_skills = list(set(skill for role in JOB_ROLES.values() for skill in role["required_skills"]))
    resume_skills = extract_skills_from_text(body.resume_text, all_skills)
    jd_skills = extract_skills_from_text(body.jd_text, all_skills)

    matched = list(set(resume_skills).intersection(set(jd_skills)))
    missing = list(set(jd_skills) - set(resume_skills))
    weak = list(set(resume_skills) - set(jd_skills))[:4]

    matched_evidence = extract_skill_evidence_offline(body.resume_text, matched)

    missing_items = []
    for s in missing:
        missing_items.append({
            "skill": s.title(),
            "importance": "High" if s in ["python", "sql", "react", "docker", "aws", "machine learning"] else "Medium",
            "why_it_matters": f"Essential skill specified in the target job description for {body.target_role or 'this position'}.",
            "recommended_learning": f"Master core fundamentals of {s.title()} on Coursera or official documentation.",
            "recommended_project": f"Build a practical hands-on application utilizing {s.title()}.",
            "resume_evidence_guideline": f"Add the project to your resume only after successfully developing and deploying it."
        })

    weak_items = []
    for w in weak:
        weak_items.append({
            "skill": w.title(),
            "reason": "Mentioned briefly without deep context or quantified impact.",
            "improvement_tip": f"Add specific bullet points detailing how you utilized {w.title()} in production."
        })

    return {
        "matched_skills": matched_evidence,
        "missing_skills": missing_items,
        "weak_skills": weak_items,
        "ai_powered": False
    }


# ── 4. AI Resume Rewriter ───────────────────────────────────────────────────

@app.post("/api/rewrite")
def rewrite_endpoint(body: RewriteRequest):
    """Rewrite a resume section or bullet point with 6 distinct professional modes."""
    if is_gemini_active():
        try:
            result = gemini_rewrite(body.content, body.section_type, body.mode, body.target_jd or "")
            if result:
                return result
        except Exception as e:
            logger.warning("Gemini rewrite failed: %s", e)

    # Offline Rule-based Rewriter
    original = body.content.strip()
    rewritten = original
    improvements = []
    placeholders = []
    keywords = []

    # Clean leading bullets
    clean_text = re.sub(r'^[•\-\*]\s*', '', original)

    if body.mode == "quantify":
        rewritten = f"Architected and deployed {clean_text} — resulting in [improved system performance by X%] and [reduced latency by Y%]."
        improvements.append("Structured into action-result formula with placeholders for measurable metrics.")
        placeholders.append("[improved system performance by X%]")
    elif body.mode == "make_technical":
        rewritten = f"Engineered scalable solution: {clean_text} utilizing modern design patterns, containerization, and automated CI/CD pipelines."
        improvements.append("Injected technical depth, architectural terminology, and engineering context.")
        keywords.append("scalable architecture")
    elif body.mode == "ats_optimize":
        rewritten = f"Spearheaded {clean_text} ensuring full compliance with industry standards, modular maintainability, and end-to-end test coverage."
        improvements.append("Aligned with standard ATS recruiter search queries and action verbs.")
    elif body.mode == "make_concise":
        # Shorten text
        rewritten = f"Led development of {clean_text}."
        improvements.append("Trimmed wordiness and emphasized core impact.")
    else:  # improve / professional
        rewritten = f"Spearheaded the design and implementation of {clean_text}, driving cross-functional collaboration and operational excellence."
        improvements.append("Elevated tone to executive-level professional clarity.")

    return {
        "original_text": original,
        "rewritten_text": rewritten,
        "mode": body.mode,
        "section_type": body.section_type,
        "improvements_made": improvements,
        "placeholders_used": placeholders,
        "keywords_injected": keywords,
        "ai_powered": False
    }


# ── 5. Tailored Resume Generator ───────────────────────────────────────────

@app.post("/api/tailored-resume")
def tailored_resume_endpoint(body: TailoredResumeRequest):
    """Generate job-specific tailored resume adjustments directly integrated with Resume Builder."""
    if is_gemini_active():
        try:
            result = gemini_tailor_resume(body.resume_data, body.jd_text)
            if result:
                return result
        except Exception as e:
            logger.warning("Gemini tailor failed: %s", e)

    # Offline Tailor Fallback
    d = body.resume_data
    skills = d.get("skills", [])
    summary = d.get("summary", "")

    return {
        "tailored_summary": f"Target-focused professional: {summary}" if summary else "Results-driven engineering candidate equipped with strong problem-solving and software development skills.",
        "prioritized_skills": sorted(skills, key=lambda x: len(x), reverse=True),
        "optimized_experience": d.get("experience", []),
        "optimized_projects": d.get("projects", []),
        "key_changes_summary": [
            "Re-prioritized skills based on relevant keywords.",
            "Prepared summary alignment for target role."
        ],
        "ai_powered": False
    }


# ── 6. ATS Simulator ────────────────────────────────────────────────────────

@app.post("/api/ats/analyze")
async def ats_simulator_endpoint(
    file: Optional[UploadFile] = File(None),
    resume_text: Optional[str] = Form(None),
    jd_text: Optional[str] = Form(None),
    target_role: Optional[str] = Form(None)
):
    """Run full deterministic + semantic ATS simulation."""
    text = ""
    if file:
        file_bytes = await file.read()
        try:
            text = extract_text_from_file(file_bytes, file.filename)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to extract resume text: {str(e)}")
    elif resume_text:
        text = resume_text.strip()

    if not text or len(text) < 20:
        raise HTTPException(status_code=400, detail="Please upload or paste resume text.")

    res = run_ats_simulation(text, jd_text or "", target_role or "")
    return res


# ── 7. Career Roadmap ───────────────────────────────────────────────────────

@app.post("/api/roadmap")
def roadmap_endpoint(body: RoadmapRequest, user: Optional[dict] = Depends(get_optional_user)):
    """Generate a personalized AI Career Roadmap with milestones and Capstone Project blueprint."""
    user_email = user["email"] if user else "guest@careerai.local"

    if is_gemini_active():
        try:
            result = gemini_roadmap(body.resume_text, body.jd_text, body.target_role)
            if result:
                db_save_career_roadmap(user_email, body.target_role, result)
                return result
        except Exception as e:
            logger.warning("Gemini roadmap failed: %s", e)

    # Offline Roadmap Fallback
    roadmap_data = {
        "target_role": body.target_role,
        "current_readiness": "70%",
        "estimated_weeks": "6 Weeks",
        "roadmap_milestones": [
            {
                "id": 1,
                "week_label": "Week 1 - 2",
                "title": "Core Technical Mastery",
                "description": f"Solidify fundamental technologies required for {body.target_role}.",
                "skills_to_learn": [
                    {
                        "skill": "Advanced Architecture & Systems",
                        "why": "Core requirement for the target role.",
                        "difficulty": "Intermediate",
                        "practice_task": "Build and document a modular prototype.",
                        "evidence_goal": "Publish code repository to GitHub with clear README."
                    }
                ]
            },
            {
                "id": 2,
                "week_label": "Week 3 - 4",
                "title": "Cloud, Infrastructure & CI/CD",
                "description": "Deploy services using containerization and automated delivery pipelines.",
                "skills_to_learn": [
                    {
                        "skill": "Docker & Cloud Deployment",
                        "why": "Modern engineering teams expect production containerization experience.",
                        "difficulty": "Intermediate",
                        "practice_task": "Containerize your application and configure automated GitHub Actions.",
                        "evidence_goal": "Add live deployment link and Dockerfile to your portfolio."
                    }
                ]
            },
            {
                "id": 3,
                "week_label": "Week 5 - 6",
                "title": "Capstone Engineering Project",
                "description": "Integrate all target competencies into an end-to-end showcase project.",
                "skills_to_learn": [
                    {
                        "skill": "End-to-End System Integration",
                        "why": "Demonstrates full-lifecycle capability to hiring managers.",
                        "difficulty": "Advanced",
                        "practice_task": "Develop the complete capstone architecture detailed below.",
                        "evidence_goal": "Add verified project bullet to resume."
                    }
                ]
            }
        ],
        "capstone_project": {
            "title": f"Production-Grade {body.target_role} System",
            "problem_statement": "Design and build a scalable full-stack system meeting real-world industry standards.",
            "architecture": "Client UI -> REST/GraphQL API -> Distributed Backend -> Cache & DB -> Cloud CI/CD",
            "technologies": ["Python", "FastAPI", "React", "Docker", "PostgreSQL"],
            "expected_deliverable": "Live hosted web application with open-source GitHub repository and performance metrics.",
            "resume_bullet_template": f"Architected an end-to-end {body.target_role} platform utilizing Python and React, supporting responsive real-time data flows with 99.9% uptime."
        },
        "ai_powered": False
    }

    db_save_career_roadmap(user_email, body.target_role, roadmap_data)
    return roadmap_data


@app.get("/api/roadmap")
def get_roadmap_endpoint(target_role: Optional[str] = None, user: Optional[dict] = Depends(get_optional_user)):
    user_email = user["email"] if user else "guest@careerai.local"
    res = db_get_career_roadmap(user_email, target_role)
    if not res:
        return {"roadmap": None}
    return res


@app.put("/api/roadmap/{roadmap_id}/progress")
def update_roadmap_progress_endpoint(roadmap_id: str, body: RoadmapProgressRequest, user: Optional[dict] = Depends(get_optional_user)):
    user_email = user["email"] if user else "guest@careerai.local"
    updated = db_update_roadmap_progress(roadmap_id, user_email, body.completed_milestones)
    return {"status": "success", "completed_milestones": body.completed_milestones}


# ── 8. AI Interview Prep & Mock Interview ───────────────────────────────────

@app.post("/api/interview/generate")
def interview_generate_endpoint(body: InterviewGenerateRequest):
    """Generate categorized interview questions with hints and answer frameworks."""
    if is_gemini_active():
        try:
            result = gemini_interview_questions(body.resume_text, body.jd_text, body.target_role)
            if result:
                return result
        except Exception as e:
            logger.warning("Gemini interview generation failed: %s", e)

    # Offline Interview Questions Fallback
    return {
        "target_role": body.target_role,
        "questions": [
            {
                "id": "q1",
                "category": "Technical",
                "question": f"Explain the architectural design of the most complex system or project you have built for {body.target_role}.",
                "why_asked": "Assesses system design thinking, modularity, and technical trade-off evaluation.",
                "hint": "Describe the data flow, choice of technologies, and how you handled potential bottlenecks.",
                "answer_framework": "1. High-level Architecture\n2. Key Component Decisions\n3. Scalability & Error Handling\n4. Results achieved"
            },
            {
                "id": "q2",
                "category": "Behavioral",
                "question": "Describe a scenario where you encountered a critical bug or production incident. How did you diagnose and resolve it?",
                "why_asked": "Tests root-cause analysis, composure under pressure, and systematic debugging methodology.",
                "hint": "Use the STAR framework (Situation, Task, Action, Result). Mention logging, metrics, and post-mortem prevention.",
                "answer_framework": "Situation: The context -> Task: What was broken -> Action: How you triaged -> Result: Impact and future prevention"
            },
            {
                "id": "q3",
                "category": "Project",
                "question": "Walk me through how you decided on the technology stack for your main resume project.",
                "why_asked": "Tests pragmatic engineering judgment rather than blindly picking trendy tools.",
                "hint": "Highlight speed of development, team familiarity, ecosystem support, and performance characteristics.",
                "answer_framework": "1. Project Requirements\n2. Evaluated Alternatives\n3. Trade-offs chosen\n4. Outcome"
            },
            {
                "id": "q4",
                "category": "Skill-Gap",
                "question": f"How do you plan to quickly bridge modern cloud and deployment practices for this {body.target_role} position?",
                "why_asked": "Tests growth mindset, proactive learning capability, and self-awareness.",
                "hint": "Mention hands-on sandbox projects, active learning resources, and containerization fundamentals.",
                "answer_framework": "1. Current baseline\n2. Active learning roadmap\n3. Practical project in progress\n4. Timeline to readiness"
            },
            {
                "id": "q5",
                "category": "HR",
                "question": f"What attracted you to this {body.target_role} position and what makes your background uniquely qualified?",
                "why_asked": "Evaluates genuine motivation, culture fit, and value proposition.",
                "hint": "Connect your top matching skills with the company's core mission.",
                "answer_framework": "1. Passion for the domain\n2. Specific skill match\n3. Impact you aim to deliver"
            }
        ],
        "ai_powered": False
    }


@app.post("/api/interview/evaluate")
def interview_evaluate_endpoint(body: InterviewEvaluateRequest):
    """Evaluate a candidate's mock interview answer across 5 scoring dimensions."""
    if is_gemini_active():
        try:
            result = gemini_evaluate_answer(
                body.question,
                body.user_answer,
                body.category or "Technical",
                body.target_role or "Software Engineer",
                body.context or ""
            )
            if result:
                return result
        except Exception as e:
            logger.warning("Gemini evaluate failed: %s", e)

    # Offline Answer Evaluator
    words = body.user_answer.split()
    word_count = len(words)
    
    score = min(100, max(30, int(word_count * 1.2) + 40))
    if word_count < 15:
        score = 45
    elif word_count > 60:
        score = min(95, score)

    return {
        "overall_score": score,
        "scores": {
            "technical_accuracy": min(100, score + 2),
            "relevance": min(100, score + 4),
            "clarity": min(100, score - 2),
            "structure": min(100, score - 5),
            "completeness": min(100, score)
        },
        "strengths": [
            "Addressed the primary intent of the question directly.",
            "Demonstrated clear communication style."
        ],
        "weaknesses": [
            "Could include deeper technical nuance or quantifiable business impact.",
            "Consider structuring answers explicitly using the STAR method (Situation, Task, Action, Result)." if word_count < 40 else "Ensure concise summary at the end."
        ],
        "improvement_tips": [
            "Start with a direct thesis statement before expanding into technical specifics.",
            "Highlight measurable results: e.g. 'This reduced query latency by 40%'."
        ],
        "sample_ideal_response_snippet": f"For {body.category} questions, a top answer establishes context in 1 sentence, details 2-3 specific architectural actions, and concludes with verified impact.",
        "ai_powered": False
    }


# ── 9. Job Application Tracker (Kanban / CRUD) ──────────────────────────────

@app.get("/api/applications")
def list_applications_endpoint(user: Optional[dict] = Depends(get_optional_user)):
    user_email = user["email"] if user else "guest@careerai.local"
    apps = db_list_applications(user_email)
    return {"applications": apps}


@app.post("/api/applications")
def create_application_endpoint(body: ApplicationCreateRequest, user: Optional[dict] = Depends(get_optional_user)):
    user_email = user["email"] if user else "guest@careerai.local"
    new_app = db_create_application(user_email, body.dict())
    return new_app


@app.put("/api/applications/{app_id}")
def update_application_endpoint(app_id: str, body: ApplicationUpdateRequest, user: Optional[dict] = Depends(get_optional_user)):
    user_email = user["email"] if user else "guest@careerai.local"
    updates = {k: v for k, v in body.dict().items() if v is not None}
    updated = db_update_application(app_id, user_email, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Application not found.")
    return updated


@app.delete("/api/applications/{app_id}")
def delete_application_endpoint(app_id: str, user: Optional[dict] = Depends(get_optional_user)):
    user_email = user["email"] if user else "guest@careerai.local"
    deleted = db_delete_application(app_id, user_email)
    if not deleted:
        raise HTTPException(status_code=404, detail="Application not found.")
    return {"status": "success", "id": app_id}


# ── 10. Resume Version Management & Comparison ──────────────────────────────

@app.get("/api/resumes/versions")
def list_resume_versions_endpoint(user: Optional[dict] = Depends(get_optional_user)):
    user_email = user["email"] if user else "guest@careerai.local"
    versions = db_list_resume_versions(user_email)
    return {"versions": versions}


@app.post("/api/resumes/versions")
def save_resume_version_endpoint(body: ResumeVersionSaveRequest, user: Optional[dict] = Depends(get_optional_user)):
    user_email = user["email"] if user else "guest@careerai.local"
    res = db_save_resume_version(
        user_email=user_email,
        title=body.title,
        resume_data=body.resume_data,
        target_role=body.target_role or "",
        target_jd_id=body.target_jd_id or "",
        ats_score=body.ats_score or 0,
        match_score=body.match_score or 0,
        version_id=body.id
    )
    return res


@app.get("/api/resumes/versions/{version_id}")
def get_resume_version_endpoint(version_id: str, user: Optional[dict] = Depends(get_optional_user)):
    user_email = user["email"] if user else "guest@careerai.local"
    res = db_get_resume_version(version_id, user_email)
    if not res:
        raise HTTPException(status_code=404, detail="Resume version not found.")
    return res


@app.delete("/api/resumes/versions/{version_id}")
def delete_resume_version_endpoint(version_id: str, user: Optional[dict] = Depends(get_optional_user)):
    user_email = user["email"] if user else "guest@careerai.local"
    deleted = db_delete_resume_version(version_id, user_email)
    if not deleted:
        raise HTTPException(status_code=404, detail="Resume version not found.")
    return {"status": "success", "id": version_id}


@app.post("/api/resumes/compare-versions")
def compare_resume_versions_endpoint(body: ResumeVersionCompareRequest, user: Optional[dict] = Depends(get_optional_user)):
    user_email = user["email"] if user else "guest@careerai.local"
    v1 = db_get_resume_version(body.version_id_1, user_email)
    v2 = db_get_resume_version(body.version_id_2, user_email)

    if not v1 or not v2:
        raise HTTPException(status_code=404, detail="One or both resume versions not found.")

    v1_data = v1.get("resume_data", {})
    v2_data = v2.get("resume_data", {})

    v1_skills = set(s.lower() for s in v1_data.get("skills", []))
    v2_skills = set(s.lower() for s in v2_data.get("skills", []))

    added_skills = list(v2_skills - v1_skills)
    removed_skills = list(v1_skills - v2_skills)

    ats_diff = v2.get("ats_score", 0) - v1.get("ats_score", 0)
    match_diff = v2.get("match_score", 0) - v1.get("match_score", 0)

    return {
        "version_1": {
            "id": v1["id"],
            "title": v1["title"],
            "ats_score": v1["ats_score"],
            "match_score": v1["match_score"],
            "skills_count": len(v1_skills),
            "updated_at": v1["updated_at"]
        },
        "version_2": {
            "id": v2["id"],
            "title": v2["title"],
            "ats_score": v2["ats_score"],
            "match_score": v2["match_score"],
            "skills_count": len(v2_skills),
            "updated_at": v2["updated_at"]
        },
        "improvement": {
            "ats_score_change": ats_diff,
            "match_score_change": match_diff,
            "added_skills": [s.title() for s in added_skills],
            "removed_skills": [s.title() for s in removed_skills],
            "summary_changed": v1_data.get("summary", "") != v2_data.get("summary", ""),
            "experience_count_v1": len(v1_data.get("experience", [])),
            "experience_count_v2": len(v2_data.get("experience", []))
        }
    }


# ── Preserved Analysis & Comparison Routes ──────────────────────────────────

@app.post("/api/analyze")
async def analyze(
    file: UploadFile = File(...),
    job_role: str = Form(...)
):
    """Analyze resume against a specific job role (preserved for backward compatibility)."""
    if not file.filename.lower().endswith((".pdf", ".docx", ".doc", ".txt")):
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, and TXT files are supported.")

    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File size exceeds 10MB limit.")

    try:
        result = analyze_resume(file_bytes, file.filename, job_role)
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("Analysis error: %s\n%s", str(e), traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/api/compare")
async def compare(file: UploadFile = File(...)):
    """Compare resume against all job roles (preserved)."""
    if not file.filename.lower().endswith((".pdf", ".docx", ".doc", ".txt")):
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, and TXT files are supported.")

    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 10MB limit.")

    try:
        results = compare_roles(file_bytes, file.filename)
        return {"comparisons": results}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("Comparison error: %s\n%s", str(e), traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


@app.post("/api/report")
async def download_report(
    file: Optional[UploadFile] = File(None),
    job_role: Optional[str] = Form("Software Engineer"),
    analysis_json: Optional[str] = Form(None)
):
    """Generate and download PDF report."""
    analysis = None
    if analysis_json:
        try:
            analysis = json.loads(analysis_json)
        except Exception:
            pass

    if not analysis and file:
        file_bytes = await file.read()
        try:
            analysis = analyze_resume(file_bytes, file.filename, job_role)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Analysis failed: {str(e)}")

    if not analysis:
        raise HTTPException(status_code=400, detail="Valid resume file or analysis data required.")

    try:
        pdf_bytes = generate_report(analysis)
        filename_safe = (analysis.get("job_role", "CareerAI") or "Report").replace(' ', '_')
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=CareerAI_Report_{filename_safe}.pdf"}
        )
    except Exception as e:
        logger.error("Report error: %s\n%s", str(e), traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


if __name__ == "__main__":
    raw_port = os.getenv("PORT", "10000")
    try:
        port = int(raw_port)
    except ValueError:
        port = 10000
    host = os.getenv("HOST", "0.0.0.0")
    print(f"Starting CareerAI server on http://{host}:{port}")
    uvicorn.run("main:app", host=host, port=port)
