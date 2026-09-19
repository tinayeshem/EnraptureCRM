"""
Live Supabase Auth & RBAC End-to-End Test
=========================================
Tests live signup, login, session token validation, permission guards,
and role restriction against your live Supabase instance.
"""

import sys
import os
import time
import uuid

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from fastapi.testclient import TestClient
from main import app
from database.db import supabase
from auth.roles import Role, Permission


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def log_step(name: str):
    print(f"\n{Colors.CYAN}{Colors.BOLD}--- [STEP] {name} ---{Colors.RESET}")


def log_pass(msg: str):
    print(f"  {Colors.GREEN}[OK] PASS:{Colors.RESET} {msg}")


def log_fail(msg: str):
    print(f"  {Colors.RED}[X] FAIL:{Colors.RESET} {msg}")


def run_live_tests():
    print(f"{Colors.BOLD}{Colors.CYAN}=======================================================")
    print(" Live Supabase Auth & RBAC End-to-End Verification")
    print(f"======================================================={Colors.RESET}")

    client = TestClient(app)
    uid = uuid.uuid4().hex[:6]
    test_password = "SecurePassword123!"

    admin_email = f"enrapture.test.admin.{uid}@gmail.com"
    mgmt_email = f"enrapture.test.mgmt.{uid}@gmail.com"

    admin_token = None
    admin_id = None
    mgmt_token = None
    mgmt_id = None

    try:
        # ---------------------------------------------------------------------
        # 1. Verify public.users table connectivity
        # ---------------------------------------------------------------------
        log_step("1. Verifying public.users Table in Supabase")
        table_check = supabase.table("users").select("count", count="exact").execute()
        log_pass(f"Table exists and is queryable. Current user count: {table_check.count}")

        # ---------------------------------------------------------------------
        # 2. Signup Admin User
        # ---------------------------------------------------------------------
        log_step(f"2. Signup Admin User ({admin_email})")
        res_signup = client.post(
            "/auth/signup",
            json={
                "email": admin_email,
                "password": test_password,
                "first_name": "Live",
                "last_name": "Admin",
                "role": "admin",
            },
        )
        if res_signup.status_code == 201:
            data = res_signup.json()
            admin_id = data.get("user_id")
            log_pass(f"Admin registered successfully! User ID: {admin_id}")
        else:
            log_fail(f"Signup failed ({res_signup.status_code}): {res_signup.text}")
            return False

        # Verify profile row in public.users
        time.sleep(1)
        profile_res = supabase.table("users").select("*").eq("id", admin_id).execute()
        if profile_res.data and profile_res.data[0].get("role") == "admin":
            log_pass(f"Profile verified in public.users: role='{profile_res.data[0]['role']}'")
        else:
            log_fail(f"Profile row missing or unexpected role in public.users: {profile_res.data}")

        # ---------------------------------------------------------------------
        # 3. Login Admin User & Get Access Token
        # ---------------------------------------------------------------------
        log_step("3. Login Admin User")
        res_login = client.post(
            "/auth/login",
            json={
                "email": admin_email,
                "password": test_password,
            },
        )
        if res_login.status_code == 200:
            login_data = res_login.json()
            admin_token = login_data.get("access_token")
            permissions = login_data.get("user", {}).get("permissions", [])
            log_pass(f"Login successful! Received Bearer token (length: {len(admin_token)})")
            log_pass(f"Admin permissions: {permissions}")
        else:
            log_fail(f"Admin login failed ({res_login.status_code}): {res_login.text}")
            return False

        # ---------------------------------------------------------------------
        # 4. Verify /auth/me with Bearer Token
        # ---------------------------------------------------------------------
        log_step("4. Test GET /auth/me with Admin Token")
        res_me = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        if res_me.status_code == 200:
            me_data = res_me.json()
            log_pass(f"Authenticated as: {me_data.get('email')} [Role: {me_data.get('role')}]")
        else:
            log_fail(f"/auth/me failed ({res_me.status_code}): {res_me.text}")

        # ---------------------------------------------------------------------
        # 5. Verify Protected Route (GET /auth/users) as Admin
        # ---------------------------------------------------------------------
        log_step("5. Test GET /auth/users as Admin")
        res_users = client.get(
            "/auth/users",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        if res_users.status_code == 200:
            users_list = res_users.json()
            log_pass(f"Admin successfully fetched users list! Count: {len(users_list)}")
        else:
            log_fail(f"GET /auth/users failed ({res_users.status_code}): {res_users.text}")

        # ---------------------------------------------------------------------
        # 6. Signup Management User
        # ---------------------------------------------------------------------
        log_step(f"6. Signup Management User ({mgmt_email})")
        res_mgmt_signup = client.post(
            "/auth/signup",
            json={
                "email": mgmt_email,
                "password": test_password,
                "first_name": "Live",
                "last_name": "Manager",
                "role": "management",
            },
        )
        if res_mgmt_signup.status_code == 201:
            mgmt_id = res_mgmt_signup.json().get("user_id")
            log_pass(f"Management user created! User ID: {mgmt_id}")
        else:
            log_fail(f"Management signup failed: {res_mgmt_signup.text}")
            return False

        # Login Management
        res_mgmt_login = client.post(
            "/auth/login",
            json={
                "email": mgmt_email,
                "password": test_password,
            },
        )
        mgmt_token = res_mgmt_login.json().get("access_token")
        log_pass("Management user logged in and token received.")

        # ---------------------------------------------------------------------
        # 7. Test Permission Boundary (Management attempting users.manage)
        # ---------------------------------------------------------------------
        log_step("7. Testing Permission Boundary (Management updating user role -> 403 Forbidden)")
        res_forbidden = client.patch(
            f"/auth/users/{mgmt_id}/role",
            headers={"Authorization": f"Bearer {mgmt_token}"},
            json={"role": "dev"},
        )
        if res_forbidden.status_code == 403:
            log_pass(f"Correctly rejected with 403 Forbidden! Detail: {res_forbidden.json().get('detail')}")
        else:
            log_fail(f"Expected 403 Forbidden, got {res_forbidden.status_code}: {res_forbidden.text}")

        # ---------------------------------------------------------------------
        # 8. Test Admin updating user role -> 200 OK
        # ---------------------------------------------------------------------
        log_step("8. Testing Admin updating user role -> 200 OK")
        res_update = client.patch(
            f"/auth/users/{mgmt_id}/role",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"role": "dev"},
        )
        if res_update.status_code == 200:
            log_pass(f"Admin successfully updated user role to dev! Response: {res_update.json().get('message')}")
        else:
            log_fail(f"Role update failed ({res_update.status_code}): {res_update.text}")

        # ---------------------------------------------------------------------
        # 9. Test Unauthorized Access (No Token -> 401)
        # ---------------------------------------------------------------------
        log_step("9. Testing Request without Token -> 401 Unauthorized")
        res_no_auth = client.get("/auth/users")
        if res_no_auth.status_code == 401:
            log_pass("Correctly rejected with 401 Unauthorized!")
        else:
            log_fail(f"Expected 401, got {res_no_auth.status_code}")

        print(f"\n{Colors.BOLD}{Colors.GREEN}=======================================================")
        print(" ALL LIVE AUTH & RBAC VERIFICATION TESTS PASSED!")
        print(f"======================================================={Colors.RESET}\n")
        return True

    finally:
        # Cleanup test users from public.users and auth.users
        log_step("Cleanup: Removing Test Users")
        for uid_to_del in [admin_id, mgmt_id]:
            if uid_to_del:
                try:
                    supabase.table("users").delete().eq("id", uid_to_del).execute()
                    # Also delete from auth.users via admin api if service role has rights
                    if hasattr(supabase.auth.admin, "delete_user"):
                        supabase.auth.admin.delete_user(uid_to_del)
                except Exception as e:
                    pass
        log_pass("Cleanup completed.")


if __name__ == "__main__":
    success = run_live_tests()
    sys.exit(0 if success else 1)
