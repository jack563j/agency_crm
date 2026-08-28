"""
Role-Based Access Control (RBAC) definitions and helpers for agency_crm.
"""
from functools import wraps
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

ROLE_ADMIN = "Admin"
ROLE_SALES = "Sales Representative"
ROLE_ACCOUNTANT = "Accountant"

ALL_ROLES = [ROLE_ADMIN, ROLE_SALES, ROLE_ACCOUNTANT]


def ensure_default_groups():
    """Ensures standard RBAC Groups exist in the database."""
    for role_name in ALL_ROLES:
        Group.objects.get_or_create(name=role_name)


def get_user_role(user) -> str:
    """Returns the primary role of a user."""
    if not user or not user.is_authenticated:
        return "Anonymous"
    if user.is_superuser or user.is_staff:
        return ROLE_ADMIN
    user_groups = set(user.groups.values_list("name", flat=True))
    if ROLE_ADMIN in user_groups:
        return ROLE_ADMIN
    if ROLE_ACCOUNTANT in user_groups:
        return ROLE_ACCOUNTANT
    if ROLE_SALES in user_groups:
        return ROLE_SALES
    return ROLE_SALES  # Default fallback for new team members


def is_admin(user) -> bool:
    return get_user_role(user) == ROLE_ADMIN


def is_sales_rep(user) -> bool:
    return get_user_role(user) == ROLE_SALES


def is_accountant(user) -> bool:
    return get_user_role(user) == ROLE_ACCOUNTANT


def role_required(allowed_roles):
    """Decorator for views to enforce required roles."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("login")
            user_role = get_user_role(request.user)
            if user_role in allowed_roles or request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied("You do not have permission to view this resource.")
        return _wrapped_view
    return decorator


def admin_required(view_func):
    return role_required([ROLE_ADMIN])(view_func)
