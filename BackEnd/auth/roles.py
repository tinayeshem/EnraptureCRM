from enum import Enum
from typing import Set, Dict


class Role(str, Enum):
    ADMIN = "admin"
    DEV = "dev"
    MANAGEMENT = "management"


# Granular Permissions
class Permission:
    # Users & Staff
    USERS_VIEW = "users.view"
    USERS_MANAGE = "users.manage"

    # Customer
    CUSTOMER_VIEW = "customer.view"
    CUSTOMER_CREATE = "customer.create"
    CUSTOMER_EDIT = "customer.edit"
    CUSTOMER_DELETE = "customer.delete"

    # Booking
    BOOKING_VIEW = "booking.view"
    BOOKING_CREATE = "booking.create"
    BOOKING_EDIT = "booking.edit"
    BOOKING_DELETE = "booking.delete"

    # Services (Room, Camp, Catering, Shuttle, Boat)
    SERVICES_VIEW = "services.view"
    SERVICES_CREATE = "services.create"
    SERVICES_EDIT = "services.edit"

    # Reviews
    REVIEW_VIEW = "review.view"
    REVIEW_CREATE = "review.create"
    REVIEW_MANAGE = "review.manage"

    # Reports & Analytics
    REPORTS_VIEW = "reports.view"
    REPORTS_MANAGE = "reports.manage"

    # System & Settings
    SYSTEM_DEBUG = "system.debug"
    SETTINGS_MANAGE = "settings.manage"


# Role to Permissions Mapping
ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    Role.ADMIN.value: {
        "*",  # Admin has access to everything
    },
    Role.DEV.value: {
        Permission.SYSTEM_DEBUG,
        Permission.SETTINGS_MANAGE,
        Permission.USERS_MANAGE,
        Permission.USERS_VIEW,
        "customer.*",
        "booking.*",
        "services.*",
        "review.*",
        "reports.*",
    },
    Role.MANAGEMENT.value: {
        Permission.REPORTS_VIEW,
        Permission.REPORTS_MANAGE,
        Permission.USERS_VIEW,
        "customer.*",
        "booking.*",
        "services.*",
        "review.*",
    },
}


def has_permission(role: str, required_permission: str) -> bool:
    """
    Evaluates whether a given role holds the required permission.
    Supports wildcards:
      - '*' grants all permissions.
      - 'domain.*' grants all permissions within that domain (e.g., 'customer.*' grants 'customer.create').
    """
    granted = ROLE_PERMISSIONS.get(role, set())

    # Full wildcard check
    if "*" in granted or required_permission in granted:
        return True

    # Domain wildcard check (e.g. "customer.*")
    if "." in required_permission:
        domain = required_permission.split(".")[0]
        if f"{domain}.*" in granted:
            return True

    return False


def get_role_permissions(role: str) -> Set[str]:
    """Returns the set of permissions assigned to a role."""
    return ROLE_PERMISSIONS.get(role, set())
