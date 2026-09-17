"""
Automated Test for Authentication, Registration, Login, Profile Persistence,
and User-Scoped Data Isolation in SQLite.
"""

import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def run_tests():
    print("=== STARTING AUTHENTICATION & DATA ISOLATION TEST SUITE ===")

    # 1. Register User A
    ts = int(time.time())
    email_a = f"alice_{ts}@example.com"
    pwd_a = "Secret123!"
    name_a = "Alice Developer"

    print(f"\n1. Testing Registration for {email_a}...")
    reg_res = requests.post(f"{BASE_URL}/api/auth/register", json={
        "full_name": name_a,
        "email": email_a,
        "password": pwd_a,
        "confirm_password": pwd_a
    })
    assert reg_res.status_code == 200, f"Registration failed: {reg_res.text}"
    token_a = reg_res.json()["token"]
    print("[OK] Registration OK. Token received.")

    # 2. Test Duplicate Email
    print("\n2. Testing Duplicate Email Handling...")
    dup_res = requests.post(f"{BASE_URL}/api/auth/register", json={
        "full_name": name_a,
        "email": email_a,
        "password": pwd_a,
        "confirm_password": pwd_a
    })
    assert dup_res.status_code == 409, f"Expected 409 Conflict, got {dup_res.status_code}"
    print("[OK] Duplicate rejection OK (409 Conflict).")

    # 3. Test Login
    print("\n3. Testing Login for User A...")
    # Incorrect password
    bad_login = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": email_a,
        "password": "wrongpassword"
    })
    assert bad_login.status_code == 401, f"Expected 401 Unauthorized, got {bad_login.status_code}"

    # Correct password
    login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": email_a,
        "password": pwd_a
    })
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token_a = login_res.json()["token"]
    print("[OK] Login OK. Valid token acquired.")

    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 4. Test /api/auth/me
    print("\n4. Testing /api/auth/me...")
    me_res = requests.get(f"{BASE_URL}/api/auth/me", headers=headers_a)
    assert me_res.status_code == 200, f"Auth me failed: {me_res.text}"
    me_data = me_res.json()
    assert me_data["email"] == email_a
    assert me_data["full_name"] == name_a
    print(f"[OK] Me endpoint OK: {me_data['full_name']} ({me_data['email']})")

    # 5. Test Profile Update & Retrieval in Database
    print("\n5. Testing Profile Persistence for User A...")
    profile_payload = {
        "name": name_a,
        "email": email_a,
        "phone": "+1 555 0199",
        "college": "Stanford University",
        "dob": "1998-05-15",
        "bio": "Senior ML & Full Stack Engineer"
    }
    put_res = requests.put(f"{BASE_URL}/api/auth/profile", json=profile_payload, headers=headers_a)
    assert put_res.status_code == 200, f"Update profile failed: {put_res.text}"

    get_prof_res = requests.get(f"{BASE_URL}/api/auth/profile", headers=headers_a)
    assert get_prof_res.status_code == 200, f"Get profile failed: {get_prof_res.text}"
    saved_prof = get_prof_res.json()["profile"]
    assert saved_prof["phone"] == "+1 555 0199"
    assert saved_prof["college"] == "Stanford University"
    print("[OK] Profile persisted and retrieved successfully from SQLite database.")

    # 6. Test User-Scoped Data Isolation with User B
    print("\n6. Testing User-Scoped Data Isolation between User A & User B...")
    # Create Application for User A
    app_res = requests.post(f"{BASE_URL}/api/applications", json={
        "company": "Google",
        "job_title": "Staff AI Engineer",
        "status": "Interview",
        "salary_range": "$220,000"
    }, headers=headers_a)
    assert app_res.status_code == 200, f"Create app failed: {app_res.text}"
    app_id = app_res.json()["id"]

    # Register User B
    email_b = f"bob_{ts}@example.com"
    pwd_b = "BobSecret123!"
    reg_b = requests.post(f"{BASE_URL}/api/auth/register", json={
        "full_name": "Bob Builder",
        "email": email_b,
        "password": pwd_b,
        "confirm_password": pwd_b
    })
    assert reg_b.status_code == 200
    token_b = reg_b.json()["token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User B lists applications -> must be empty (cannot see User A's application)
    apps_b_res = requests.get(f"{BASE_URL}/api/applications", headers=headers_b)
    assert apps_b_res.status_code == 200
    apps_b = apps_b_res.json()["applications"]
    assert len(apps_b) == 0, f"Data leakage! User B saw {len(apps_b)} applications belonging to User A."
    print("[OK] User B sees 0 applications (No data leakage).")

    # User A lists applications -> must contain Google
    apps_a_res = requests.get(f"{BASE_URL}/api/applications", headers=headers_a)
    assert apps_a_res.status_code == 200
    apps_a = apps_a_res.json()["applications"]
    assert len(apps_a) == 1
    assert apps_a[0]["company"] == "Google"
    print("[OK] User A sees their own 1 application.")

    # Clean up User A's application
    requests.delete(f"{BASE_URL}/api/applications/{app_id}", headers=headers_a)
    print("[OK] Cleaned up test records.")

    print("\nALL AUTHENTICATION AND DATA ISOLATION TESTS PASSED 100%!")

if __name__ == "__main__":
    run_tests()
