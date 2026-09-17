"""
Centralized Google Gemini AI Service for CareerAI.
Uses the official google-genai SDK (gemini-2.5-flash) with structured JSON generation,
robust error handling, rate-limit resilience, and strict anti-hallucination guardrails.
"""

import os
import json
import logging
import re
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"


def is_gemini_active() -> bool:
    """Check if a valid GEMINI_API_KEY is configured in the environment."""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    return bool(key and key != "YOUR_GEMINI_API_KEY" and len(key) > 10)


def _get_client():
    """Get initialized google.genai Client."""
    if not is_gemini_active():
        return None
    try:
        from google import genai
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        return genai.Client(api_key=api_key)
    except Exception as e:
        logger.error("Failed to initialize google-genai client: %s", e)
        return None


def _clean_json_text(text: str) -> str:
    """Remove markdown fences and trim whitespace from AI output."""
    t = text.strip()
    if t.startswith("```json"):
        t = t[7:]
    elif t.startswith("```"):
        t = t[3:]
    if t.endswith("```"):
        t = t[:-3]
    return t.strip()


import time

def _call_gemini_json(prompt: str, temperature: float = 0.2) -> Optional[Dict[str, Any]]:
    """Execute Gemini call requesting strict application/json response with retry and model fallback."""
    client = _get_client()
    if not client:
        return None

    from google.genai import types

    # Try configured model first, cascade through stable models if 503/busy
    models_to_try = [GEMINI_MODEL]
    for fallback in ["gemini-2.5-flash", "gemini-2.5-pro"]:
        if fallback not in models_to_try:
            models_to_try.append(fallback)

    last_error = None
    for model_name in models_to_try:
        for attempt in range(2):  # Try twice per model in case of temporary 503
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=temperature,
                    )
                )
                if response and response.text:
                    cleaned = _clean_json_text(response.text)
                    return json.loads(cleaned)
            except Exception as e:
                last_error = e
                err_str = str(e)
                if "503" in err_str or "429" in err_str:
                    logger.warning("Gemini model %s transient error (attempt %d): %s. Backing off 1.5s...", model_name, attempt + 1, err_str)
                    time.sleep(1.5)
                    continue
                else:
                    logger.warning("Gemini model %s failed: %s. Trying fallback model.", model_name, err_str)
                    break

    logger.warning("All Gemini models failed. Last error: %s", last_error)
    return None


# ── 1. Job Description Analyzer ────────────────────────────────────────────

def analyze_job_description(jd_text: str) -> Optional[Dict[str, Any]]:
    """Extract structured requirements, skills, seniority, and responsibilities from a Job Description."""
    prompt = f"""
You are an expert Technical Recruiter and Job Description Parser. Analyze the following Job Description and extract structured information.

JOB DESCRIPTION:
\"\"\"{jd_text[:15000]}\"\"\"

Respond with a strictly valid JSON object with exact keys:
{{
  "job_title": "Identified job title or closest standard title",
  "company": "Company name if mentioned, otherwise empty string",
  "seniority_level": "Entry, Mid-Level, Senior, Lead, or Executive",
  "experience_years": "e.g. '3-5 years' or 'Not specified'",
  "education_requirements": ["list of required or preferred degrees/fields"],
  "required_skills": ["list of absolute must-have technical and domain skills"],
  "preferred_skills": ["list of nice-to-have or bonus skills"],
  "technologies": ["list of specific programming languages, libraries, databases, cloud tools, frameworks"],
  "certifications": ["list of required or preferred certifications if any"],
  "responsibilities": ["list of top 4-6 primary job responsibilities"],
  "keywords": ["list of top 10-15 high-value ATS search keywords"],
  "summary": "Concise 2-3 sentence overview of this role and what the company is seeking"
}}
"""
    result = _call_gemini_json(prompt, temperature=0.1)
    if result:
        result["ai_powered"] = True
    return result


# ── 2. Resume + JD Intelligence Multi-Dimensional Match ────────────────────

def compare_resume_with_jd(resume_text: str, jd_text: str, target_role: str = "") -> Optional[Dict[str, Any]]:
    """
    Perform deep 9-dimension intelligence alignment between resume and target job description.
    Scores: Overall, Skill, Experience, Project, Education, Keyword, ATS.
    """
    prompt = f"""
You are a Principal Technical Recruiter and AI Career Auditor. Evaluate the candidate's resume thoroughly against the target Job Description.
Target Role Title: "{target_role}"

CANDIDATE RESUME:
\"\"\"{resume_text[:18000]}\"\"\"

TARGET JOB DESCRIPTION:
\"\"\"{jd_text[:15000]}\"\"\"

TASK:
Analyze all 9 dimensions of candidate fit:
1. Skill alignment
2. Experience alignment
3. Project alignment
4. Education alignment
5. Keyword alignment
6. Technology alignment
7. Responsibility alignment
8. Certification alignment
9. Seniority alignment

Provide honest, realistic scores from 0 to 100. Do NOT inflate scores.

Format your response STRICTLY as valid JSON with exact keys:
{{
  "overall_match": 78,
  "skill_match": 82,
  "experience_match": 75,
  "project_match": 80,
  "education_match": 90,
  "keyword_match": 72,
  "ats_score": 85,
  "seniority_fit": "Target is Mid-Level; candidate appears Mid-Level",
  "matched_skills": ["list of skills clearly present in resume and relevant to JD"],
  "missing_skills": ["critical skills from JD not found in resume"],
  "weak_skills": ["skills mentioned in resume but without sufficient depth/evidence"],
  "keywords_found": ["top ATS keywords from JD present in resume"],
  "keywords_missing": ["critical ATS keywords from JD missing from resume"],
  "resume_issues": [
    "Specific issue 1 (e.g. lack of quantified performance metrics in project X)",
    "Specific issue 2"
  ],
  "recommendations": [
    "Specific, actionable recommendation 1",
    "Specific, actionable recommendation 2",
    "Specific, actionable recommendation 3",
    "Specific, actionable recommendation 4"
  ],
  "alignment_summary": "Thorough 2-3 paragraph breakdown explaining the candidate's real-world competitiveness for this specific role."
}}
"""
    result = _call_gemini_json(prompt, temperature=0.15)
    if result:
        result["ai_powered"] = True
    return result


# ── 3. Skill Gap Analysis & Evidence Mapping ───────────────────────────────

def identify_skill_gaps_and_evidence(resume_text: str, jd_text: str, target_role: str = "") -> Optional[Dict[str, Any]]:
    """
    Identify matched, missing, and weak skills with evidence mapping (quotes, section sources, confidence)
    and actionable project & evidence guidance for missing skills.
    """
    prompt = f"""
You are an expert NLP Skill Extraction and Verification System.
Target Role: "{target_role}"

CANDIDATE RESUME:
\"\"\"{resume_text[:18000]}\"\"\"

TARGET JOB DESCRIPTION:
\"\"\"{jd_text[:15000]}\"\"\"

TASK:
1. Identify MATCHED SKILLS. For each matched skill, cite the EXACT quote/sentence from the resume, the section name (e.g. 'Projects -> CardioAI', 'Experience -> Tech Corp'), and confidence score (0-100).
2. Identify MISSING SKILLS required or favored by the JD. For each missing skill, explain why it matters, its importance ('High', 'Medium', 'Low'), a recommended learning topic, a practical project idea, and the exact evidence the candidate should only add after completing it.
3. Identify WEAK/PARTIAL SKILLS with constructive suggestions.

Format response strictly as JSON with exact keys:
{{
  "matched_skills": [
    {{
      "skill": "Python",
      "evidence_quote": "Developed machine learning models using Python and scikit-learn...",
      "section_source": "Projects -> CardioAI",
      "confidence": 95
    }}
  ],
  "missing_skills": [
    {{
      "skill": "PySpark",
      "importance": "High",
      "why_it_matters": "Required for large-scale ETL pipeline processing in target role.",
      "recommended_learning": "Apache Spark with Python on Databricks / Coursera",
      "recommended_project": "Build an end-to-end batch processing pipeline with PySpark and Azure Blob Storage.",
      "resume_evidence_guideline": "Add project to Projects section after building it. Do not claim without working implementation."
    }}
  ],
  "weak_skills": [
    {{
      "skill": "Docker",
      "reason": "Listed in skills section but not referenced in any project bullet points or experience.",
      "improvement_tip": "Mention specific containerization workflows in your existing projects."
    }}
  ]
}}
"""
    result = _call_gemini_json(prompt, temperature=0.1)
    if result:
        result["ai_powered"] = True
    return result


# ── 4. AI Resume Rewriter ──────────────────────────────────────────────────

def rewrite_resume_section(content: str, section_type: str, mode: str, target_jd: str = "") -> Optional[Dict[str, Any]]:
    """
    Rewrite a resume section or bullet point according to a specific mode:
    'improve', 'ats_optimize', 'make_technical', 'make_concise', 'quantify', 'professional'.
    STRICT RULE: Never fabricate companies, achievements, or fake metrics. Use placeholders like [X%] if needed.
    """
    mode_instructions = {
        "improve": "Enhance clarity, dynamic action verbs, tone, and professional impact while strictly preserving all facts.",
        "ats_optimize": "Inject relevant industry keywords and standard ATS terminology naturally aligned with the target job.",
        "make_technical": "Highlight architectural patterns, technical depth, technologies, and engineering methodologies.",
        "make_concise": "Eliminate filler words, passive voice, and redundancies for maximum punchy brevity.",
        "quantify": "Restructure sentences into the XYZ formula (Accomplished [X] as measured by [Y], by doing [Z]). If metrics are not in original, insert honest placeholders like '[increased by X%]' instead of making up numbers.",
        "professional": "Transform into executive-level, polished corporate phrasing suitable for top-tier hiring managers."
    }

    instruction = mode_instructions.get(mode, mode_instructions["improve"])
    escaped_content = content.replace('"', '\\"')

    prompt = f"""
You are an expert Resume Editor and Executive Career Coach.
SECTION TYPE: {section_type}
EDIT MODE: {mode} ({instruction})

TARGET JOB CONTEXT (Optional):
\"\"\"{target_jd[:5000]}\"\"\"

ORIGINAL CANDIDATE TEXT:
\"\"\"{content}\"\"\"

CRITICAL ANTI-HALLUCINATION RULES:
1. NEVER fabricate fake metrics, fake companies, fake job titles, or fake degrees.
2. If suggesting metric quantification, use placeholders such as "[e.g. improved latency by X%]" or "[reduced downtime by X hours]".
3. Maintain 100% truthfulness to the candidate's actual experience.

Respond with valid JSON:
{{
  "original_text": "{escaped_content}",
  "rewritten_text": "The improved version of the text",
  "mode": "{mode}",
  "section_type": "{section_type}",
  "improvements_made": [
    "Bullet explaining what was improved",
    "Bullet explaining keyword or verb adjustment"
  ],
  "placeholders_used": ["List of placeholders used if any, or empty array"],
  "keywords_injected": ["List of high-impact keywords incorporated"]
}}
"""
    result = _call_gemini_json(prompt, temperature=0.25)
    if result:
        result["ai_powered"] = True
    return result


# ── 5. Tailored Resume Generator ───────────────────────────────────────────

def generate_tailored_resume(resume_data: dict, jd_text: str) -> Optional[Dict[str, Any]]:
    """
    Generate tailored resume adjustments based on existing resume data and target JD.
    Re-orders skills and projects by relevance, crafts a targeted summary, and optimizes bullet points.
    """
    resume_json_str = json.dumps(resume_data, indent=2)

    prompt = f"""
You are an expert ATS Resume Strategist. Tailor the candidate's existing resume data to maximize relevance for the target Job Description.

CANDIDATE EXISTING RESUME DATA:
{resume_json_str[:15000]}

TARGET JOB DESCRIPTION:
\"\"\"{jd_text[:10000]}\"\"\"

TASK:
1. Craft a highly targeted Professional Summary that connects the candidate's real experience directly to the target role.
2. Prioritize skills order: place skills most relevant to the JD first.
3. Optimize experience and project bullet points for ATS keyword alignment without fabricating experience.
4. Keep the same structure: personal, summary, skills, experience, education, projects, certifications.

Format response strictly as valid JSON matching the structure:
{{
  "tailored_summary": "New targeted summary string",
  "prioritized_skills": ["List of skills in order of JD relevance"],
  "optimized_experience": [
    {{
      "id": 1,
      "company": "Company Name",
      "role": "Role Title",
      "startDate": "...",
      "endDate": "...",
      "current": false,
      "description": "Optimized bullet points aligned with JD keywords"
    }}
  ],
  "optimized_projects": [
    {{
      "id": 1,
      "name": "Project Name",
      "tech": "Tech stack string",
      "link": "...",
      "description": "Optimized description highlighting relevant features"
    }}
  ],
  "key_changes_summary": [
    "Summary of tailored adjustment 1",
    "Summary of tailored adjustment 2"
  ]
}}
"""
    result = _call_gemini_json(prompt, temperature=0.2)
    if result:
        result["ai_powered"] = True
    return result


# ── 6. ATS Simulator (Semantic Evaluation) ─────────────────────────────────

def generate_ats_analysis(resume_text: str, jd_text: str = "") -> Optional[Dict[str, Any]]:
    """
    Generate semantic ATS simulation evaluating readability, section headers, keyword alignment,
    critical issues, warnings, and suggestions.
    """
    prompt = f"""
You are an advanced Applicant Tracking System (ATS) Parser and Hiring Algorithm.
Simulate an ATS parsing and scoring run on this resume.

RESUME TEXT:
\"\"\"{resume_text[:18000]}\"\"\"

TARGET JD (Optional):
\"\"\"{jd_text[:10000]}\"\"\"

TASK:
Analyze:
- Keyword coverage and placement
- Section header standardness (Experience, Education, Skills, Projects)
- Formatting readability
- Bullet point strength and clarity
- Contact info completeness
- Red flags (missing dates, vague responsibilities, excessive jargon)

Format response as strictly valid JSON:
{{
  "ats_score": 87,
  "sub_scores": {{
    "keywords": 88,
    "structure": 92,
    "readability": 85,
    "jd_alignment": 80,
    "formatting": 90
  }},
  "critical_issues": [
    "Any critical blocking issue (e.g. Missing contact email or missing clear Experience section header)"
  ],
  "warnings": [
    "Warnings that might reduce score (e.g. Project descriptions lack specific tooling details)"
  ],
  "suggestions": [
    "Helpful tips to push ATS score to 95+"
  ],
  "parsed_sections_detected": ["Summary", "Experience", "Skills", "Education", "Projects"],
  "readability_level": "Professional / Clear",
  "word_count_status": "Optimal (450 words)"
}}
"""
    result = _call_gemini_json(prompt, temperature=0.15)
    if result:
        result["ai_powered"] = True
    return result


# ── 7. AI Career Roadmap ───────────────────────────────────────────────────

def generate_career_roadmap(resume_text: str, jd_text: str, target_role: str = "") -> Optional[Dict[str, Any]]:
    """
    Generate a personalized weekly/milestone learning roadmap based on resume, target role, and skill gaps.
    Includes milestone tasks, difficulty ratings, practice projects, and a Capstone Project blueprint.
    """
    prompt = f"""
You are a Principal Engineering Mentor and Career Architect.
Create a step-by-step career development roadmap for this candidate to successfully transition into or excel at the target role: "{target_role}".

CANDIDATE RESUME:
\"\"\"{resume_text[:15000]}\"\"\"

TARGET JOB DESCRIPTION:
\"\"\"{jd_text[:12000]}\"\"\"

TASK:
1. Formulate 4 to 6 logical learning milestones (e.g. Week 1-2, Week 3-4, etc.).
2. For each milestone, detail the exact skill, why it matters, difficulty level ('Beginner', 'Intermediate', 'Advanced'), practical learning steps, and verifiable portfolio evidence to build.
3. Design a comprehensive Capstone Project that connects all the missing core competencies together.

Format response strictly as valid JSON:
{{
  "target_role": "{target_role}",
  "current_readiness": "72%",
  "estimated_weeks": "6-8 Weeks",
  "roadmap_milestones": [
    {{
      "id": 1,
      "week_label": "Week 1 - 2",
      "title": "Advanced SQL & Data Modeling",
      "description": "Master complex window functions, CTEs, and star-schema dimensional modeling.",
      "skills_to_learn": [
        {{
          "skill": "Advanced SQL",
          "why": "Crucial for writing performant analytical queries.",
          "difficulty": "Intermediate",
          "practice_task": "Solve 15 LeetCode Database Medium/Hard problems.",
          "evidence_goal": "Publish SQL schema and optimization case study on GitHub."
        }}
      ]
    }}
  ],
  "capstone_project": {{
    "title": "Real-Time Cloud Analytics & ETL Pipeline",
    "problem_statement": "Ingest and process 1M+ streaming records to deliver real-time metrics dashboards.",
    "architecture": "Kafka / EventHub -> PySpark -> Databricks -> PostgreSQL / Snowflake -> Streamlit / PowerBI",
    "technologies": ["Python", "PySpark", "Databricks", "SQL", "Docker"],
    "expected_deliverable": "Working GitHub repository with CI/CD and architecture diagram.",
    "resume_bullet_template": "Architected an end-to-end data pipeline processing 1M+ events using PySpark and Databricks, reducing reporting latency by 45%."
  }}
}}
"""
    result = _call_gemini_json(prompt, temperature=0.2)
    if result:
        result["ai_powered"] = True
    return result


# ── 8. AI Interview Prep & Mock Interview Engine ───────────────────────────

def generate_interview_questions(resume_text: str, jd_text: str, target_role: str = "") -> Optional[Dict[str, Any]]:
    """
    Generate targeted interview questions across categories:
    Technical, Behavioral, Project, HR, Situational, Skill-Gap.
    Includes hints and answer frameworks.
    """
    prompt = f"""
You are a Lead Hiring Manager and Technical Interviewer conducting interviews for: "{target_role}".

CANDIDATE RESUME:
\"\"\"{resume_text[:15000]}\"\"\"

TARGET JOB DESCRIPTION:
\"\"\"{jd_text[:12000]}\"\"\"

Generate 8 to 12 targeted interview questions customized to the candidate's actual projects and identified skill gaps.
Categories:
- "Technical"
- "Behavioral"
- "Project"
- "HR"
- "Situational"
- "Skill-Gap"

Format response strictly as valid JSON:
{{
  "target_role": "{target_role}",
  "questions": [
    {{
      "id": "q1",
      "category": "Technical",
      "question": "How would you design an ETL pipeline that handles schema evolution without downtime?",
      "why_asked": "Tests data engineering design patterns required in the job description.",
      "hint": "Mention dead-letter queues, Avro/Parquet schema registries, and idempotent writes.",
      "answer_framework": "1. Situation/Context\\n2. Architecture approach\\n3. Handling edge cases\\n4. Monitoring"
    }}
  ]
}}
"""
    result = _call_gemini_json(prompt, temperature=0.2)
    if result:
        result["ai_powered"] = True
    return result


def evaluate_mock_interview_answer(
    question: str,
    user_answer: str,
    category: str = "Technical",
    target_role: str = "",
    context: str = ""
) -> Optional[Dict[str, Any]]:
    """
    Evaluate a candidate's answer to a mock interview question.
    Scores: Technical accuracy, Relevance, Clarity, Structure, Completeness.
    Provides strengths, weaknesses, and improvement suggestions.
    """
    prompt = f"""
You are a Senior Interviewer evaluating a candidate's response in a mock interview.
TARGET ROLE: {target_role}
QUESTION CATEGORY: {category}
QUESTION: "{question}"
CANDIDATE'S ANSWER:
\"\"\"{user_answer}\"\"\"

Evaluate the answer objectively.
Scores are from 0 to 100.
Format response strictly as valid JSON:
{{
  "overall_score": 82,
  "scores": {{
    "technical_accuracy": 85,
    "relevance": 80,
    "clarity": 85,
    "structure": 78,
    "completeness": 80
  }},
  "strengths": [
    "Identified the core technical constraint effectively",
    "Structured explanation logically"
  ],
  "weaknesses": [
    "Did not mention error handling or edge cases"
  ],
  "improvement_tips": [
    "Use the STAR framework (Situation, Task, Action, Result) to make behavioral answers more compelling",
    "Quantify the outcome or impact of your solution"
  ],
  "sample_ideal_response_snippet": "A concise 2-3 sentence example illustrating how a top-tier candidate would answer."
}}
"""
    result = _call_gemini_json(prompt, temperature=0.2)
    if result:
        result["ai_powered"] = True
    return result
