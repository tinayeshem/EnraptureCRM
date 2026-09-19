from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status
from database.db import supabase
from auth.roles import Role, get_role_permissions


class AuthService:
    @staticmethod
    def signup_user(
        email: str,
        password: str,
        first_name: str = "",
        last_name: str = "",
        role: str = Role.MANAGEMENT.value,
    ) -> Dict[str, Any]:
        """Registers a user via Supabase Auth and creates their profile in public.users."""
        if role not in [r.value for r in Role]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role '{role}'. Allowed roles: {[r.value for r in Role]}",
            )

        try:
            signup_res = supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "first_name": first_name,
                        "last_name": last_name,
                        "role": role,
                    }
                },
            })
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Signup failed: {str(e)}",
            )

        if not signup_res.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Signup failed: Supabase did not return user information.",
            )

        user_id = str(signup_res.user.id)

        # Upsert profile into public.users
        try:
            supabase.table("users").upsert({
                "id": user_id,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "role": role,
                "is_active": True,
            }).execute()
        except Exception:
            pass  # If table is not created yet or handled by trigger

        access_token = None
        if signup_res.session and signup_res.session.access_token:
            access_token = signup_res.session.access_token

        return {
            "message": "User registered successfully",
            "user_id": user_id,
            "email": email,
            "role": role,
            "access_token": access_token,
        }

    @staticmethod
    def login_user(email: str, password: str) -> Dict[str, Any]:
        """Authenticates user with email and password via Supabase Auth."""
        try:
            auth_res = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password,
            })
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid email or password: {str(e)}",
            )

        if not auth_res.session or not auth_res.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials.",
            )

        user_id = str(auth_res.user.id)
        email = auth_res.user.email or ""

        # Fetch profile
        role = Role.MANAGEMENT.value
        first_name = ""
        last_name = ""
        try:
            prof = supabase.table("users").select("*").eq("id", user_id).execute()
            if prof.data:
                user_data = prof.data[0]
                role = user_data.get("role", Role.MANAGEMENT.value)
                first_name = user_data.get("first_name", "")
                last_name = user_data.get("last_name", "")
                if not user_data.get("is_active", True):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="User account is deactivated.",
                    )
            else:
                metadata = getattr(auth_res.user, "user_metadata", {}) or {}
                role = metadata.get("role", Role.MANAGEMENT.value)
                first_name = metadata.get("first_name", "")
                last_name = metadata.get("last_name", "")
        except HTTPException:
            raise
        except Exception:
            pass

        return {
            "access_token": auth_res.session.access_token,
            "token_type": "bearer",
            "expires_in": auth_res.session.expires_in,
            "user": {
                "id": user_id,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "role": role,
                "permissions": sorted(list(get_role_permissions(role))),
            },
        }

    @staticmethod
    def list_users() -> List[Dict[str, Any]]:
        """Retrieves all users from public.users."""
        try:
            res = supabase.table("users").select("*").order("created_at", desc=True).execute()
            return res.data or []
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch users: {str(e)}",
            )

    @staticmethod
    def update_user_role(user_id: str, new_role: str) -> Dict[str, Any]:
        """Updates a user's role in public.users."""
        if new_role not in [r.value for r in Role]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role '{new_role}'. Allowed roles: {[r.value for r in Role]}",
            )

        try:
            res = (
                supabase.table("users")
                .update({"role": new_role})
                .eq("id", user_id)
                .execute()
            )
            if not res.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User with ID '{user_id}' not found in public.users.",
                )
            return {
                "message": f"Role updated to '{new_role}' successfully",
                "user": res.data[0],
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update user role: {str(e)}",
            )
