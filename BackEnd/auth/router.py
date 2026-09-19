from typing import Optional, List
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from auth.roles import Role, Permission
from auth.dependencies import CurrentUser, get_current_user, require_permission
from auth.service import AuthService

auth_router = APIRouter(prefix="/auth", tags=["Authentication & Access Control"])


class SignupRequest(BaseModel):
    email: str
    password: str
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""
    role: Optional[Role] = Role.MANAGEMENT


class LoginRequest(BaseModel):
    email: str
    password: str


class RoleUpdateRequest(BaseModel):
    role: Role


@auth_router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(request: SignupRequest):
    """
    Registers a new user in Supabase Auth and registers profile with specified role (default: management).
    """
    return AuthService.signup_user(
        email=request.email,
        password=request.password,
        first_name=request.first_name or "",
        last_name=request.last_name or "",
        role=request.role.value if request.role else Role.MANAGEMENT.value,
    )


@auth_router.post("/login")
def login(request: LoginRequest):
    """
    Authenticates with Supabase Auth and returns an access token, profile, and effective permissions.
    """
    return AuthService.login_user(
        email=request.email,
        password=request.password,
    )


@auth_router.get("/me")
def get_me(current_user: CurrentUser = Depends(get_current_user)):
    """
    Returns current authenticated user details and active permissions.
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "permissions": sorted(list(current_user.permissions)),
    }


@auth_router.get("/users", dependencies=[Depends(require_permission(Permission.USERS_VIEW))])
def list_users():
    """
    Lists all users. Requires 'users.view' permission (granted to admin, dev, management).
    """
    return AuthService.list_users()


@auth_router.patch(
    "/users/{user_id}/role",
    dependencies=[Depends(require_permission(Permission.USERS_MANAGE))],
)
def update_user_role(user_id: str, request: RoleUpdateRequest):
    """
    Changes a user's role. Requires 'users.manage' permission (granted to admin, dev).
    """
    return AuthService.update_user_role(user_id=user_id, new_role=request.role.value)
