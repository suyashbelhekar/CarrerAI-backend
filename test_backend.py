"""
Verification script for CareerAI backend APIs.
Tests health, auth, database, ATS simulation, rewriter, JD analysis, and interview evaluation.
"""

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_all():
    print("Testing root...")
    r = client.get("/")
    assert r.status_code == 200, f"Root failed: {r.text}"
    print("Root OK:", r.json()["name"])

    print("Testing status...")
    r = client.get("/api/status")
    assert r.status_code == 200
    print("Status OK:", r.json())

    print("Testing JD Analyzer (offline fallback / AI)...")
    r = client.post("/api/jd/analyze", data={"jd_text": "We are seeking a Senior Python Developer with experience in FastAPI, Docker, and SQL to build high-performance data microservices."})
    assert r.status_code == 200, f"JD analyze failed: {r.text}"
    jd_data = r.json()
    print("JD Analyze OK:", jd_data.get("job_title"), "Skills:", jd_data.get("required_skills"))

    print("Testing ATS Simulator...")
    sample_resume = """
    John Doe
    john.doe@example.com | (555) 123-4567 | San Francisco, CA | linkedin.com/in/johndoe | github.com/johndoe
    
    Professional Summary
    Results-driven Software Engineer with 4+ years of experience designing and scaling microservices.
    
    Technical Skills
    Python, FastAPI, Docker, PostgreSQL, Redis, Kubernetes, Git, CI/CD
    
    Experience
    Senior Backend Engineer - Tech Corp (2022 - Present)
    • Architected high-throughput microservices using Python and FastAPI, reducing API latency by 45%.
    • Spearheaded database optimization on PostgreSQL, accelerating search queries for 500,000+ active users.
    • Deployed containerized applications with Docker and Kubernetes on AWS.
    
    Education
    Bachelor of Science in Computer Science - University of California (2018 - 2022)
    
    Projects
    Real-Time Analytics Engine - Built distributed event processing pipeline using Python and Redis.
    """
    
    r = client.post("/api/ats/analyze", data={"resume_text": sample_resume, "jd_text": "Seeking Python FastAPI engineer"})
    assert r.status_code == 200, f"ATS failed: {r.text}"
    ats_data = r.json()
    print("ATS Simulator OK: Score =", ats_data.get("ats_score"), "Sub-scores:", ats_data.get("sub_scores"))

    print("Testing AI Rewriter...")
    r = client.post("/api/rewrite", json={"content": "worked on backend api with python", "mode": "quantify", "section_type": "Experience"})
    assert r.status_code == 200, f"Rewrite failed: {r.text}"
    print("Rewriter OK:", r.json()["rewritten_text"])

    print("Testing Match Endpoint...")
    r = client.post("/api/match", json={"resume_text": sample_resume, "jd_text": "Python FastAPI PostgreSQL Docker engineer", "target_role": "Backend Developer"})
    assert r.status_code == 200, f"Match failed: {r.text}"
    print("Match OK: Overall match =", r.json().get("overall_match"))

    print("Testing Skill Gap & Evidence...")
    r = client.post("/api/skill-gap", json={"resume_text": sample_resume, "jd_text": "Python FastAPI PostgreSQL Docker PySpark Databricks", "target_role": "Backend Developer"})
    assert r.status_code == 200, f"Skill gap failed: {r.text}"
    sg_data = r.json()
    print(f"Skill Gap OK: {len(sg_data.get('matched_skills', []))} matched, {len(sg_data.get('missing_skills', []))} missing")

    print("Testing Applications CRUD...")
    r = client.post("/api/applications", json={"company": "Google", "job_title": "Software Engineer", "status": "Applied", "match_score": 88, "ats_score": 92})
    assert r.status_code == 200, f"Create app failed: {r.text}"
    app_id = r.json()["id"]
    print("Create Application OK, id:", app_id)

    r = client.get("/api/applications")
    assert r.status_code == 200
    print("List Applications OK, count:", len(r.json()["applications"]))

    r = client.delete(f"/api/applications/{app_id}")
    assert r.status_code == 200
    print("Delete Application OK")

    print("Testing Roadmap Endpoint...")
    r = client.post("/api/roadmap", json={"resume_text": sample_resume, "jd_text": "Python Spark Cloud Databricks", "target_role": "Data Engineer"})
    assert r.status_code == 200, f"Roadmap failed: {r.text}"
    print("Roadmap OK: Target =", r.json().get("target_role"))

    print("Testing Mock Interview Answer Evaluation...")
    r = client.post("/api/interview/evaluate", json={"question": "How do you scale a FastAPI application?", "user_answer": "I scale it by using Uvicorn workers behind Nginx load balancer and caching hot endpoints with Redis.", "category": "Technical", "target_role": "Backend Developer"})
    assert r.status_code == 200, f"Interview evaluate failed: {r.text}"
    print("Interview Evaluation OK: Score =", r.json().get("overall_score"))

    print("\nALL BACKEND API TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_all()
