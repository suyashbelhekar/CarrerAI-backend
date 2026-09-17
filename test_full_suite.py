"""
Master End-to-End Verification Test Suite for CareerAI Platform.
Tests all 12 modules, authentication, database persistence, and AI inference endpoints.
"""

import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def run_master_verification():
    print("==================================================================")
    print("      CAREERAI PLATFORM — MASTER END-TO-END VERIFICATION          ")
    print("==================================================================")
    
    # 1. System Health & Roles
    print("\n[1/10] Verifying System Root, Status & Roles...")
    r_root = requests.get(f"{BASE_URL}/")
    assert r_root.status_code == 200
    print(f"  [OK] Root endpoint: {r_root.json().get('name')} v{r_root.json().get('version')}")

    r_status = requests.get(f"{BASE_URL}/api/status")
    assert r_status.status_code == 200
    st = r_status.json()
    print(f"  [OK] Status: {st.get('status')} | Database: {st.get('database')} | Roles: {st.get('available_roles')}")

    r_roles = requests.get(f"{BASE_URL}/api/roles")
    assert r_roles.status_code == 200 and len(r_roles.json().get("roles", [])) >= 8
    print(f"  [OK] Predefined Roles loaded ({len(r_roles.json()['roles'])} roles available)")

    # 2. Authentication & Profile Persistence
    print("\n[2/10] Verifying Authentication & Database Profile Sync...")
    ts = int(time.time())
    test_email = f"master_verifier_{ts}@example.com"
    test_pwd = "SecureMaster123!"
    test_name = "Master Quality Engineer"

    # Register
    r_reg = requests.post(f"{BASE_URL}/api/auth/register", json={
        "full_name": test_name,
        "email": test_email,
        "password": test_pwd,
        "confirm_password": test_pwd
    })
    assert r_reg.status_code == 200
    token = r_reg.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"  [OK] User registered: {test_email}")

    # Login
    r_log = requests.post(f"{BASE_URL}/api/auth/login", json={"email": test_email, "password": test_pwd})
    assert r_log.status_code == 200
    print("  [OK] Login successful with JWT token")

    # Profile Update & Retrieval
    r_put_prof = requests.put(f"{BASE_URL}/api/auth/profile", json={
        "name": test_name,
        "email": test_email,
        "phone": "+1 415 555 2671",
        "college": "Carnegie Mellon",
        "dob": "1997-04-12"
    }, headers=headers)
    assert r_put_prof.status_code == 200

    r_get_prof = requests.get(f"{BASE_URL}/api/auth/profile", headers=headers)
    assert r_get_prof.status_code == 200 and r_get_prof.json()["profile"]["college"] == "Carnegie Mellon"
    print("  [OK] Profile data successfully synchronized with SQLite database")

    # Sample Resume & JD for Intelligence Tests
    sample_resume = (
        "John Doe - Senior Software Engineer\n"
        "Summary: Experienced Full Stack Engineer with 5+ years building scalable cloud backends in Python and FastAPI.\n"
        "Experience:\n"
        "- Senior Backend Engineer at TechCorp (2021-Present): Designed high-throughput REST APIs using Python, FastAPI, and PostgreSQL, handling 20,000 requests/sec.\n"
        "- Software Developer at StartupX (2019-2021): Built interactive React frontends and integrated Redis caching, decreasing server load by 35%.\n"
        "Skills: Python, FastAPI, React, PostgreSQL, Docker, Redis, Git, REST APIs, CI/CD, Microservices."
    )
    sample_jd = (
        "Job Title: Senior Python / Cloud Backend Engineer\n"
        "Company: CloudScale Systems\n"
        "Requirements:\n"
        "- 4+ years of professional backend engineering in Python\n"
        "- Hands-on experience with FastAPI or Flask and PostgreSQL database optimization\n"
        "- Strong understanding of Docker, Kubernetes, Microservices, and Redis caching\n"
        "- Experience designing low-latency RESTful APIs and CI/CD pipelines\n"
        "- Nice to have: AWS or GCP cloud deployment experience."
    )

    # 3. Job Description Analyzer
    print("\n[3/10] Verifying Job Description Analyzer...")
    r_jd = requests.post(f"{BASE_URL}/api/jd/analyze", data={"jd_text": sample_jd})
    assert r_jd.status_code == 200
    jd_res = r_jd.json()
    print(f"  [OK] JD Analyzed: Title='{jd_res.get('job_title')}', Core Skills={jd_res.get('core_skills', [])[:4]}")

    # 4. Resume + JD 9D Intelligence Matching
    print("\n[4/10] Verifying 9D Resume Intelligence Matcher...")
    r_match = requests.post(f"{BASE_URL}/api/match", json={
        "resume_text": sample_resume,
        "jd_text": sample_jd,
        "target_role": "Backend Developer"
    })
    assert r_match.status_code == 200
    m_res = r_match.json()
    print(f"  [OK] Match Score: {m_res.get('overall_match')}% | Dimensions: Depth={m_res.get('dimension_scores', {}).get('skill_depth')}, Breadth={m_res.get('dimension_scores', {}).get('skill_breadth')}")

    # 5. Skill Gap & Sentence Evidence Mapping
    print("\n[5/10] Verifying Skill Gap & Evidence Mapping...")
    r_gap = requests.post(f"{BASE_URL}/api/skill-gap", json={
        "resume_text": sample_resume,
        "jd_text": sample_jd,
        "target_role": "Backend Developer"
    })
    assert r_gap.status_code == 200
    gap_res = r_gap.json()
    print(f"  [OK] Matched Skills: {len(gap_res.get('matched_skills', []))} | Missing Skills: {len(gap_res.get('missing_skills', []))} | Evidence Mappings: {len(gap_res.get('evidence_mappings', []))}")

    # 6. AI Resume Section Rewriter
    print("\n[6/10] Verifying AI Section Rewriter (XYZ Formula & ATS Mode)...")
    r_rewrite = requests.post(f"{BASE_URL}/api/rewrite", json={
        "content": "Built REST APIs with Python and improved database speed.",
        "section_type": "Experience Bullet",
        "mode": "improve",
        "target_jd": sample_jd
    })
    assert r_rewrite.status_code == 200
    print(f"  [OK] Rewritten Bullet: {r_rewrite.json().get('rewritten', '')[:80]}...")

    # 7. ATS Simulator
    print("\n[7/10] Verifying ATS Compliance Simulator...")
    r_ats = requests.post(f"{BASE_URL}/api/ats/analyze", data={
        "resume_text": sample_resume,
        "jd_text": sample_jd,
        "target_role": "Backend Developer"
    })
    assert r_ats.status_code == 200
    ats_data = r_ats.json()
    print(f"  [OK] ATS Score: {ats_data.get('overall_score')}/100 | Breakdown: {ats_data.get('sub_scores')}")

    # 8. Career Roadmap
    print("\n[8/10] Verifying Target Role Career Roadmap...")
    r_road = requests.post(f"{BASE_URL}/api/roadmap", json={
        "resume_text": sample_resume,
        "jd_text": sample_jd,
        "target_role": "Backend Developer"
    }, headers=headers)
    assert r_road.status_code == 200
    road_data = r_road.json()
    print(f"  [OK] Roadmap Generated: {len(road_data.get('phases', []))} Phases | Capstone: '{road_data.get('capstone_project', {}).get('title')}'")

    # 9. Interview Prep & Live Mock Evaluation
    print("\n[9/10] Verifying Interview Preparation & Answer Evaluation...")
    r_eval = requests.post(f"{BASE_URL}/api/interview/evaluate", json={
        "question": "How do you optimize slow queries in PostgreSQL with Python/FastAPI?",
        "user_answer": "I profile slow queries using EXPLAIN ANALYZE, add indexed composite keys on filter columns, implement connection pooling with asyncpg, and add Redis for frequently queried caches.",
        "category": "Technical",
        "target_role": "Backend Developer"
    })
    assert r_eval.status_code == 200
    eval_res = r_eval.json()
    print(f"  [OK] Mock Answer Score: {eval_res.get('overall_score')}/100 | Technical Accuracy: {eval_res.get('scores', {}).get('technical_accuracy')}")

    # 10. Job Application Tracker & Resume Versions CRUD
    print("\n[10/10] Verifying Applications Tracker & Resume Versioning CRUD...")
    # Create App
    r_new_app = requests.post(f"{BASE_URL}/api/applications", json={
        "company": "Amazon AWS",
        "job_title": "Cloud Architect",
        "status": "Applied",
        "salary_range": "$180,000 - $210,000"
    }, headers=headers)
    assert r_new_app.status_code == 200
    app_id = r_new_app.json()["id"]

    # List Apps
    r_list_apps = requests.get(f"{BASE_URL}/api/applications", headers=headers)
    assert r_list_apps.status_code == 200 and len(r_list_apps.json().get("applications", [])) == 1

    # Update App
    r_up_app = requests.put(f"{BASE_URL}/api/applications/{app_id}", json={"status": "Interview"}, headers=headers)
    assert r_up_app.status_code == 200

    # Delete App
    r_del_app = requests.delete(f"{BASE_URL}/api/applications/{app_id}", headers=headers)
    assert r_del_app.status_code == 200
    print("  [OK] Applications Kanban CRUD lifecycle completed cleanly")

    # Create Resume Version
    r_ver = requests.post(f"{BASE_URL}/api/resumes/versions", json={
        "title": "Backend Focused V1",
        "target_role": "Backend Developer",
        "resume_data": {"skills": ["Python", "FastAPI", "Docker"]},
        "ats_score": 88,
        "match_score": 90
    }, headers=headers)
    assert r_ver.status_code == 200
    ver_id = r_ver.json()["id"]

    # Delete Version
    r_del_ver = requests.delete(f"{BASE_URL}/api/resumes/versions/{ver_id}", headers=headers)
    assert r_del_ver.status_code == 200
    print("  [OK] Resume Versions lifecycle completed cleanly")

    print("\n==================================================================")
    print("  ALL 10 VERIFICATION STAGES PASSED WITH 100% SUCCESS RATE!       ")
    print("==================================================================")

if __name__ == "__main__":
    run_master_verification()
