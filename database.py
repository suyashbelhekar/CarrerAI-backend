"""
CareerAI Persistent SQLite Database & Repository Layer.
Provides schema initialization, user-scoped data persistence, and helper CRUD operations
for users, resumes, resume versions, job descriptions, analyses, applications, roadmaps, and interview sessions.
"""

import sqlite3
import json
import time
import uuid
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "career_ai.db"
USERS_FILE = Path(__file__).parent / "users.json"


def get_connection() -> sqlite3.Connection:
    """Get a SQLite connection with row factory configured."""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database tables and indexes."""
    conn = get_connection()
    cursor = conn.cursor()

    # Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            profile_data TEXT,
            created_at REAL NOT NULL
        )
    """)

    # Resumes Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resumes (
            id TEXT PRIMARY KEY,
            user_email TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_text TEXT NOT NULL,
            word_count INTEGER DEFAULT 0,
            extracted_skills TEXT,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        )
    """)

    # Resume Versions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resume_versions (
            id TEXT PRIMARY KEY,
            user_email TEXT NOT NULL,
            title TEXT NOT NULL,
            target_role TEXT,
            target_jd_id TEXT,
            resume_data TEXT NOT NULL,
            ats_score INTEGER DEFAULT 0,
            match_score INTEGER DEFAULT 0,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        )
    """)

    # Job Descriptions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_descriptions (
            id TEXT PRIMARY KEY,
            user_email TEXT NOT NULL,
            title TEXT NOT NULL,
            company TEXT DEFAULT '',
            raw_text TEXT NOT NULL,
            parsed_data TEXT,
            created_at REAL NOT NULL
        )
    """)

    # Analyses Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id TEXT PRIMARY KEY,
            user_email TEXT NOT NULL,
            resume_id TEXT,
            target_role TEXT NOT NULL,
            jd_id TEXT,
            analysis_data TEXT NOT NULL,
            match_score INTEGER DEFAULT 0,
            ats_score INTEGER DEFAULT 0,
            created_at REAL NOT NULL
        )
    """)

    # Applications Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id TEXT PRIMARY KEY,
            user_email TEXT NOT NULL,
            company TEXT NOT NULL,
            job_title TEXT NOT NULL,
            job_location TEXT DEFAULT '',
            application_date TEXT NOT NULL,
            status TEXT NOT NULL,
            resume_version_id TEXT,
            match_score INTEGER DEFAULT 0,
            ats_score INTEGER DEFAULT 0,
            notes TEXT DEFAULT '',
            interview_date TEXT DEFAULT '',
            follow_up_date TEXT DEFAULT '',
            salary_range TEXT DEFAULT '',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        )
    """)

    # Career Roadmaps Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS career_roadmaps (
            id TEXT PRIMARY KEY,
            user_email TEXT NOT NULL,
            target_role TEXT NOT NULL,
            roadmap_data TEXT NOT NULL,
            completed_milestones TEXT DEFAULT '[]',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        )
    """)

    # Interview Sessions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interview_sessions (
            id TEXT PRIMARY KEY,
            user_email TEXT NOT NULL,
            target_role TEXT NOT NULL,
            questions_data TEXT NOT NULL,
            overall_score INTEGER DEFAULT 0,
            feedback TEXT DEFAULT '',
            created_at REAL NOT NULL
        )
    """)

    # Create indexes for fast lookup
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_resumes_user ON resumes(user_email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_versions_user ON resume_versions(user_email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jds_user ON job_descriptions(user_email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_analyses_user ON analyses(user_email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_apps_user ON applications(user_email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_roadmaps_user ON career_roadmaps(user_email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_interviews_user ON interview_sessions(user_email)")

    conn.commit()

    # Migrate from existing users.json if present and users table is empty
    cursor.execute("SELECT COUNT(*) as cnt FROM users")
    count = cursor.fetchone()["cnt"]
    if count == 0 and USERS_FILE.exists():
        try:
            legacy_users = json.loads(USERS_FILE.read_text())
            for email, data in legacy_users.items():
                cursor.execute(
                    "INSERT OR IGNORE INTO users (id, email, full_name, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), email.lower().strip(), data.get("full_name", ""), data.get("password_hash", ""), data.get("created_at", time.time()))
                )
            conn.commit()
            logger.info("Successfully migrated %d users from users.json to SQLite database", len(legacy_users))
        except Exception as e:
            logger.warning("Error migrating legacy users.json: %s", e)

    conn.close()


# Initialize on import
init_db()


# ── User CRUD ───────────────────────────────────────────────────────────────

def db_create_user(full_name: str, email: str, password_hash: str) -> dict:
    email = email.lower().strip()
    conn = get_connection()
    cursor = conn.cursor()
    user_id = str(uuid.uuid4())
    now = time.time()
    try:
        cursor.execute(
            "INSERT INTO users (id, email, full_name, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, email, full_name.strip(), password_hash, now)
        )
        conn.commit()
        return {"id": user_id, "email": email, "full_name": full_name.strip(), "created_at": now}
    finally:
        conn.close()


def db_get_user_by_email(email: str) -> Optional[dict]:
    if not email:
        return None
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),))
        row = cursor.fetchone()
        if not row:
            return None
        return dict(row)
    finally:
        conn.close()


def db_update_user_profile(email: str, profile_data: dict) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE users SET profile_data = ? WHERE email = ?",
            (json.dumps(profile_data), email.lower().strip())
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


# ── Resume CRUD ─────────────────────────────────────────────────────────────

def db_save_resume(user_email: str, file_name: str, file_text: str, extracted_skills: list = None) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    resume_id = str(uuid.uuid4())
    now = time.time()
    word_count = len(file_text.split())
    skills_json = json.dumps(extracted_skills or [])
    try:
        cursor.execute("""
            INSERT INTO resumes (id, user_email, file_name, file_text, word_count, extracted_skills, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (resume_id, user_email.lower().strip(), file_name, file_text, word_count, skills_json, now, now))
        conn.commit()
        return {
            "id": resume_id,
            "file_name": file_name,
            "word_count": word_count,
            "created_at": now
        }
    finally:
        conn.close()


def db_get_latest_resume(user_email: str) -> Optional[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT * FROM resumes WHERE user_email = ? ORDER BY created_at DESC LIMIT 1",
            (user_email.lower().strip(),)
        )
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        res["extracted_skills"] = json.loads(res.get("extracted_skills") or "[]")
        return res
    finally:
        conn.close()


# ── Resume Versions CRUD ────────────────────────────────────────────────────

def db_save_resume_version(
    user_email: str,
    title: str,
    resume_data: dict,
    target_role: str = "",
    target_jd_id: str = "",
    ats_score: int = 0,
    match_score: int = 0,
    version_id: str = None
) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    now = time.time()
    v_id = version_id or str(uuid.uuid4())
    data_json = json.dumps(resume_data)

    try:
        if version_id:
            cursor.execute("""
                UPDATE resume_versions
                SET title = ?, target_role = ?, target_jd_id = ?, resume_data = ?, ats_score = ?, match_score = ?, updated_at = ?
                WHERE id = ? AND user_email = ?
            """, (title, target_role, target_jd_id, data_json, ats_score, match_score, now, v_id, user_email.lower().strip()))
        else:
            cursor.execute("""
                INSERT INTO resume_versions (id, user_email, title, target_role, target_jd_id, resume_data, ats_score, match_score, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (v_id, user_email.lower().strip(), title, target_role, target_jd_id, data_json, ats_score, match_score, now, now))
        conn.commit()
        return {
            "id": v_id,
            "title": title,
            "target_role": target_role,
            "ats_score": ats_score,
            "match_score": match_score,
            "updated_at": now
        }
    finally:
        conn.close()


def db_list_resume_versions(user_email: str) -> List[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id, user_email, title, target_role, target_jd_id, ats_score, match_score, created_at, updated_at FROM resume_versions WHERE user_email = ? ORDER BY updated_at DESC",
            (user_email.lower().strip(),)
        )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def db_get_resume_version(version_id: str, user_email: str) -> Optional[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT * FROM resume_versions WHERE id = ? AND user_email = ?",
            (version_id, user_email.lower().strip())
        )
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        res["resume_data"] = json.loads(res.get("resume_data") or "{}")
        return res
    finally:
        conn.close()


def db_delete_resume_version(version_id: str, user_email: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM resume_versions WHERE id = ? AND user_email = ?",
            (version_id, user_email.lower().strip())
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


# ── Job Descriptions CRUD ───────────────────────────────────────────────────

def db_save_job_description(user_email: str, title: str, company: str, raw_text: str, parsed_data: dict = None) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    jd_id = str(uuid.uuid4())
    now = time.time()
    parsed_json = json.dumps(parsed_data or {})
    try:
        cursor.execute("""
            INSERT INTO job_descriptions (id, user_email, title, company, raw_text, parsed_data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (jd_id, user_email.lower().strip(), title, company, raw_text, parsed_json, now))
        conn.commit()
        return {
            "id": jd_id,
            "title": title,
            "company": company,
            "created_at": now,
            "parsed_data": parsed_data or {}
        }
    finally:
        conn.close()


def db_list_job_descriptions(user_email: str) -> List[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id, user_email, title, company, created_at, parsed_data FROM job_descriptions WHERE user_email = ? ORDER BY created_at DESC",
            (user_email.lower().strip(),)
        )
        results = []
        for r in cursor.fetchall():
            d = dict(r)
            d["parsed_data"] = json.loads(d.get("parsed_data") or "{}")
            results.append(d)
        return results
    finally:
        conn.close()


def db_get_job_description(jd_id: str, user_email: str) -> Optional[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT * FROM job_descriptions WHERE id = ? AND user_email = ?",
            (jd_id, user_email.lower().strip())
        )
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        res["parsed_data"] = json.loads(res.get("parsed_data") or "{}")
        return res
    finally:
        conn.close()


def db_delete_job_description(jd_id: str, user_email: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM job_descriptions WHERE id = ? AND user_email = ?", (jd_id, user_email.lower().strip()))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


# ── Analyses CRUD ───────────────────────────────────────────────────────────

def db_save_analysis(user_email: str, target_role: str, analysis_data: dict, resume_id: str = None, jd_id: str = None) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    analysis_id = str(uuid.uuid4())
    now = time.time()
    match_score = analysis_data.get("match_score", analysis_data.get("overall_match", 0))
    ats_score = analysis_data.get("ats_score", analysis_data.get("resume_score", 0))
    try:
        cursor.execute("""
            INSERT INTO analyses (id, user_email, resume_id, target_role, jd_id, analysis_data, match_score, ats_score, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (analysis_id, user_email.lower().strip(), resume_id, target_role, jd_id, json.dumps(analysis_data), match_score, ats_score, now))
        conn.commit()
        return {
            "id": analysis_id,
            "target_role": target_role,
            "match_score": match_score,
            "ats_score": ats_score,
            "created_at": now
        }
    finally:
        conn.close()


def db_list_analyses(user_email: str, limit: int = 10) -> List[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id, user_email, target_role, match_score, ats_score, created_at FROM analyses WHERE user_email = ? ORDER BY created_at DESC LIMIT ?",
            (user_email.lower().strip(), limit)
        )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def db_get_latest_analysis(user_email: str) -> Optional[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT * FROM analyses WHERE user_email = ? ORDER BY created_at DESC LIMIT 1",
            (user_email.lower().strip(),)
        )
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        res["analysis_data"] = json.loads(res.get("analysis_data") or "{}")
        return res
    finally:
        conn.close()


# ── Applications CRUD ───────────────────────────────────────────────────────

def db_create_application(user_email: str, app_data: dict) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    app_id = str(uuid.uuid4())
    now = time.time()
    try:
        cursor.execute("""
            INSERT INTO applications (
                id, user_email, company, job_title, job_location, application_date,
                status, resume_version_id, match_score, ats_score, notes,
                interview_date, follow_up_date, salary_range, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            app_id,
            user_email.lower().strip(),
            app_data.get("company", "").strip(),
            app_data.get("job_title", "").strip(),
            app_data.get("job_location", ""),
            app_data.get("application_date", time.strftime("%Y-%m-%d")),
            app_data.get("status", "Applied"),
            app_data.get("resume_version_id", ""),
            int(app_data.get("match_score", 0)),
            int(app_data.get("ats_score", 0)),
            app_data.get("notes", ""),
            app_data.get("interview_date", ""),
            app_data.get("follow_up_date", ""),
            app_data.get("salary_range", ""),
            now,
            now
        ))
        conn.commit()
        return {"id": app_id, **app_data, "created_at": now, "updated_at": now}
    finally:
        conn.close()


def db_list_applications(user_email: str) -> List[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT * FROM applications WHERE user_email = ? ORDER BY updated_at DESC",
            (user_email.lower().strip(),)
        )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def db_update_application(app_id: str, user_email: str, updates: dict) -> Optional[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    now = time.time()
    try:
        cursor.execute("SELECT * FROM applications WHERE id = ? AND user_email = ?", (app_id, user_email.lower().strip()))
        existing = cursor.fetchone()
        if not existing:
            return None

        fields = []
        params = []
        allowed_keys = [
            "company", "job_title", "job_location", "application_date", "status",
            "resume_version_id", "match_score", "ats_score", "notes",
            "interview_date", "follow_up_date", "salary_range"
        ]

        for k in allowed_keys:
            if k in updates:
                fields.append(f"{k} = ?")
                params.append(updates[k])

        fields.append("updated_at = ?")
        params.append(now)
        params.extend([app_id, user_email.lower().strip()])

        sql = f"UPDATE applications SET {', '.join(fields)} WHERE id = ? AND user_email = ?"
        cursor.execute(sql, params)
        conn.commit()

        cursor.execute("SELECT * FROM applications WHERE id = ?", (app_id,))
        return dict(cursor.fetchone())
    finally:
        conn.close()


def db_delete_application(app_id: str, user_email: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM applications WHERE id = ? AND user_email = ?", (app_id, user_email.lower().strip()))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


# ── Career Roadmaps CRUD ────────────────────────────────────────────────────

def db_save_career_roadmap(user_email: str, target_role: str, roadmap_data: dict) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    now = time.time()
    try:
        # Check if one already exists for this role
        cursor.execute(
            "SELECT id FROM career_roadmaps WHERE user_email = ? AND target_role = ?",
            (user_email.lower().strip(), target_role)
        )
        existing = cursor.fetchone()
        if existing:
            roadmap_id = existing["id"]
            cursor.execute("""
                UPDATE career_roadmaps
                SET roadmap_data = ?, updated_at = ?
                WHERE id = ?
            """, (json.dumps(roadmap_data), now, roadmap_id))
        else:
            roadmap_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO career_roadmaps (id, user_email, target_role, roadmap_data, completed_milestones, created_at, updated_at)
                VALUES (?, ?, ?, ?, '[]', ?, ?)
            """, (roadmap_id, user_email.lower().strip(), target_role, json.dumps(roadmap_data), now, now))
        conn.commit()
        return {
            "id": roadmap_id,
            "target_role": target_role,
            "roadmap_data": roadmap_data,
            "created_at": now
        }
    finally:
        conn.close()


def db_get_career_roadmap(user_email: str, target_role: str = None) -> Optional[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if target_role:
            cursor.execute(
                "SELECT * FROM career_roadmaps WHERE user_email = ? AND target_role = ? ORDER BY updated_at DESC LIMIT 1",
                (user_email.lower().strip(), target_role)
            )
        else:
            cursor.execute(
                "SELECT * FROM career_roadmaps WHERE user_email = ? ORDER BY updated_at DESC LIMIT 1",
                (user_email.lower().strip(),)
            )
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        res["roadmap_data"] = json.loads(res.get("roadmap_data") or "{}")
        res["completed_milestones"] = json.loads(res.get("completed_milestones") or "[]")
        return res
    finally:
        conn.close()


def db_update_roadmap_progress(roadmap_id: str, user_email: str, completed_milestones: list) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    now = time.time()
    try:
        cursor.execute("""
            UPDATE career_roadmaps
            SET completed_milestones = ?, updated_at = ?
            WHERE id = ? AND user_email = ?
        """, (json.dumps(completed_milestones), now, roadmap_id, user_email.lower().strip()))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


# ── Interview Sessions CRUD ─────────────────────────────────────────────────

def db_save_interview_session(user_email: str, target_role: str, questions_data: list, overall_score: int = 0, feedback: str = "") -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    session_id = str(uuid.uuid4())
    now = time.time()
    try:
        cursor.execute("""
            INSERT INTO interview_sessions (id, user_email, target_role, questions_data, overall_score, feedback, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (session_id, user_email.lower().strip(), target_role, json.dumps(questions_data), overall_score, feedback, now))
        conn.commit()
        return {
            "id": session_id,
            "target_role": target_role,
            "overall_score": overall_score,
            "created_at": now
        }
    finally:
        conn.close()


def db_list_interview_sessions(user_email: str, limit: int = 10) -> List[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id, user_email, target_role, overall_score, feedback, created_at FROM interview_sessions WHERE user_email = ? ORDER BY created_at DESC LIMIT ?",
            (user_email.lower().strip(), limit)
        )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()
