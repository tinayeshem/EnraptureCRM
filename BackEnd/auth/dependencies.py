import os
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from database.db import supabase
from auth.roles import Role, has_permission, get_role_permissions

# Security scheme for Swagger UI & Authorization header
security = HTTPBearer(auto_error=False)

# Optional global bypass flag for testing or isolated environments
AUTH_ENABLED = os.environ.get("AUTH_ENABLED", "true").lower() in ("true", "1", "yes")


class CurrentUser(BaseModel):
    id: str
    email: str
    role: str = Role.MANAGEMENT.value
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool = True

    def has_permission(self, permission: str) -> bool:
        return has_permission(self.role, permission)

    @property
    def permissions(self) -> set:
        return get_role_permissions(self.role)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> CurrentUser:
    """
    FastAPI dependency that validates the Bearer token with Supabase Auth,
    retrieves the user's role and details from public.users, and returns CurrentUser.
    """
    if not AUTH_ENABLED:
        # Development / test mode fallback if auth is explicitly disabled
        return CurrentUser(
            id="00000000-0000-0000-0000-000000000000",
            email="dev@local.test",
            role=Role.ADMIN.value,
            first_name="Local",
            last_name="Dev",
            is_active=True,
        )

    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # 1. Verify token with Supabase Auth
    try:
        auth_response = supabase.auth.get_user(token)
        if not auth_response or not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication token.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        auth_user = auth_response.user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = str(auth_user.id)
    email = auth_user.email or ""

    # 2. Fetch profile from public.users
    try:
        profile_res = (
            supabase.table("users")
            .select("*")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
    except Exception:
        profile_res = None

    if profile_res and profile_res.data:
        profile = profile_res.data[0]
        if not profile.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated.",
            )
        return CurrentUser(
            id=user_id,
            email=profile.get("email") or email,
            role=profile.get("role", Role.MANAGEMENT.value),
            first_name=profile.get("first_name"),
            last_name=profile.get("last_name"),
            is_active=profile.get("is_active", True),
        )

    # Fallback if profile row hasn't been synced to public.users yet
    user_metadata = getattr(auth_user, "user_metadata", {}) or {}
    role = user_metadata.get("role", Role.MANAGEMENT.value)
    first_name = user_metadata.get("first_name")
    last_name = user_metadata.get("last_name")

    # Attempt to lazily sync into public.users
    try:
        supabase.table("users").upsert({
            "id": user_id,
            "email": email,
            "role": role,
            "first_name": first_name or "",
            "last_name": last_name or "",
            "is_active": True,
        }).execute()
    except Exception:
        pass  # If table is not created yet or RLS blocks it, continue with token data

    return CurrentUser(
        id=user_id,
        email=email,
        role=role,
        first_name=first_name,
        last_name=last_name,
        is_active=True,
    )


def require_permission(required_permission: str):
    """
    Dependency factory to guard FastAPI endpoints by specific permission.
    Example:
        @app.post("/customer", dependencies=[Depends(require_permission("customer.create"))])
    """
    def permission_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not current_user.has_permission(required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: permission '{required_permission}' is required.",
            )
        return current_user

    return permission_checker


def require_role(*allowed_roles: str):
    """
    Dependency factory to guard FastAPI endpoints by allowed roles.
    Admin always passes.
    Example:
        @app.get("/admin-panel", dependencies=[Depends(require_role(Role.ADMIN, Role.DEV))])
    """
    allowed_values = {
        r.value if isinstance(r, Role) else str(r) for r in allowed_roles
    }

    def role_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role != Role.ADMIN.value and current_user.role not in allowed_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: role must be one of {sorted(list(allowed_values))}.",
            )
        return current_user

    return role_checker
