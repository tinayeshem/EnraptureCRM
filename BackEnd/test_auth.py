"""
Comprehensive Test Suite for Supabase Auth, RBAC & Permissions
==============================================================
Tests role hierarchy, permission evaluation, wildcard matching,
FastAPI Bearer authentication, and endpoint authorization guards.
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from fastapi.testclient import TestClient
from main import app
from auth.roles import (
    Role,
    Permission,
    has_permission,
    get_role_permissions,
    ROLE_PERMISSIONS,
)
from auth.dependencies import (
    CurrentUser,
    get_current_user,
    require_permission,
    require_role,
)


class TestRolesAndPermissions(unittest.TestCase):
    """Verifies RBAC rules and wildcard permission evaluations for admin, dev, management."""

    def test_admin_has_all_permissions(self):
        """Admin should have wildcard '*' access matching any permission."""
        self.assertTrue(has_permission(Role.ADMIN.value, Permission.USERS_MANAGE))
        self.assertTrue(has_permission(Role.ADMIN.value, Permission.CUSTOMER_DELETE))
        self.assertTrue(has_permission(Role.ADMIN.value, Permission.SYSTEM_DEBUG))
        self.assertTrue(has_permission(Role.ADMIN.value, "arbitrary.future.permission"))

    def test_dev_permissions(self):
        """Dev should have technical tools, user management, and CRM domain access."""
        self.assertTrue(has_permission(Role.DEV.value, Permission.SYSTEM_DEBUG))
        self.assertTrue(has_permission(Role.DEV.value, Permission.SETTINGS_MANAGE))
        self.assertTrue(has_permission(Role.DEV.value, Permission.USERS_MANAGE))
        self.assertTrue(has_permission(Role.DEV.value, Permission.CUSTOMER_CREATE))
        self.assertTrue(has_permission(Role.DEV.value, Permission.CUSTOMER_DELETE))
        self.assertTrue(has_permission(Role.DEV.value, Permission.BOOKING_CREATE))

    def test_management_permissions(self):
        """Management should have reports, staff view, and CRM operations, but not system debug or user management."""
        self.assertTrue(has_permission(Role.MANAGEMENT.value, Permission.REPORTS_VIEW))
        self.assertTrue(has_permission(Role.MANAGEMENT.value, Permission.REPORTS_MANAGE))
        self.assertTrue(has_permission(Role.MANAGEMENT.value, Permission.USERS_VIEW))
        self.assertTrue(has_permission(Role.MANAGEMENT.value, Permission.CUSTOMER_CREATE))
        self.assertTrue(has_permission(Role.MANAGEMENT.value, Permission.BOOKING_CREATE))
        # Denied
        self.assertFalse(has_permission(Role.MANAGEMENT.value, Permission.SYSTEM_DEBUG))
        self.assertFalse(has_permission(Role.MANAGEMENT.value, Permission.USERS_MANAGE))

    def test_current_user_model_has_permission(self):
        user = CurrentUser(
            id="test-123",
            email="manager@crm.com",
            role=Role.MANAGEMENT.value,
        )
        self.assertTrue(user.has_permission("customer.create"))
        self.assertTrue(user.has_permission("reports.view"))
        self.assertFalse(user.has_permission("system.debug"))


class TestFastApiAuthorizationEndpoints(unittest.TestCase):
    """Verifies HTTP 401 / 403 status codes and dependency enforcement."""

    def setUp(self):
        self.client = TestClient(app)

    def test_unauthenticated_request_fails(self):
        """Accessing protected CRM endpoint without token returns 401."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 401)
        self.assertIn("detail", response.json())

    def test_invalid_token_fails(self):
        """Accessing with invalid Bearer token returns 401."""
        with patch("auth.dependencies.supabase.auth.get_user") as mock_get_user:
            mock_get_user.side_effect = Exception("Invalid JWT signature")
            response = self.client.get(
                "/",
                headers={"Authorization": "Bearer invalid_token_123"},
            )
            self.assertEqual(response.status_code, 401)

    def test_authenticated_permission_denied(self):
        """User with role 'management' accessing 'users.manage' receives 403 Forbidden."""
        mgr_user = CurrentUser(
            id="user-123",
            email="manager@crm.com",
            role=Role.MANAGEMENT.value,
        )

        app.dependency_overrides[get_current_user] = lambda: mgr_user
        try:
            response = self.client.patch(
                "/auth/users/user-2/role",
                json={"role": "dev"},
            )
            self.assertEqual(response.status_code, 403)
            self.assertIn("users.manage", response.json()["detail"])
        finally:
            app.dependency_overrides.clear()

    def test_authenticated_permission_granted(self):
        """User with role 'management' accessing 'users.view' succeeds."""
        mgr_user = CurrentUser(
            id="mgr-123",
            email="manager@crm.com",
            role=Role.MANAGEMENT.value,
        )

        app.dependency_overrides[get_current_user] = lambda: mgr_user
        with patch("auth.service.AuthService.list_users") as mock_list:
            mock_list.return_value = [{"id": "1", "email": "a@crm.com"}]
            try:
                response = self.client.get("/auth/users")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), [{"id": "1", "email": "a@crm.com"}])
            finally:
                app.dependency_overrides.clear()

    def test_auth_me_endpoint(self):
        """GET /auth/me returns current user profile and sorted permissions."""
        user = CurrentUser(
            id="user-abc",
            email="manager@crm.com",
            role=Role.MANAGEMENT.value,
            first_name="Jane",
            last_name="Doe",
        )

        app.dependency_overrides[get_current_user] = lambda: user
        try:
            response = self.client.get("/auth/me")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["id"], "user-abc")
            self.assertEqual(data["email"], "manager@crm.com")
            self.assertEqual(data["role"], "management")
            self.assertIn("customer.*", data["permissions"])
            self.assertIn("reports.view", data["permissions"])
            self.assertTrue(user.has_permission("customer.create"))
        finally:
            app.dependency_overrides.clear()

    def test_role_update_restricted_to_admin_or_dev(self):
        """PATCH /auth/users/{user_id}/role requires users.manage permission."""
        mgr_user = CurrentUser(
            id="mgr-1",
            email="manager@crm.com",
            role=Role.MANAGEMENT.value,
        )
        admin_user = CurrentUser(
            id="admin-1",
            email="admin@crm.com",
            role=Role.ADMIN.value,
        )

        # 1. Denied for management
        app.dependency_overrides[get_current_user] = lambda: mgr_user
        try:
            response = self.client.patch(
                "/auth/users/user-2/role",
                json={"role": "dev"},
            )
            self.assertEqual(response.status_code, 403)
        finally:
            app.dependency_overrides.clear()

        # 2. Allowed for admin
        app.dependency_overrides[get_current_user] = lambda: admin_user
        with patch("auth.service.AuthService.update_user_role") as mock_update:
            mock_update.return_value = {
                "message": "Role updated to 'dev' successfully",
                "user": {"id": "user-2", "role": "dev"},
            }
            try:
                response = self.client.patch(
                    "/auth/users/user-2/role",
                    json={"role": "dev"},
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["user"]["role"], "dev")
            finally:
                app.dependency_overrides.clear()


if __name__ == "__main__":
    print("\n=======================================================")
    print(" Running Supabase Auth & RBAC Permissions Test Suite")
    print("=======================================================\n")
    unittest.main(verbosity=2)
