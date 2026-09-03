from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def role_required(allowed_roles):
    """
    Decorator to check if user has required role
    Usage: @role_required(['admin', 'pharmacist'])
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped_view(request, *args, **kwargs):
            if request.user.role in allowed_roles or request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, 'You do not have permission to access this page.')
                return redirect('dashboard')
        return wrapped_view
    return decorator


def admin_required(view_func):
    """Decorator for admin-only views"""
    return role_required(['admin'])(view_func)


def pharmacist_or_admin(view_func):
    """Decorator for pharmacist and admin views"""
    return role_required(['admin', 'pharmacist'])(view_func)


def assistant_or_above(view_func):
    """Decorator for all authenticated users"""
    return role_required(['admin', 'pharmacist', 'assistant'])(view_func)