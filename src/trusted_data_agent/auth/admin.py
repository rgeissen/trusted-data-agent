"""
Admin utilities and permission checks for Phase 4.

Provides admin-only functionality including user management,
credential oversight, and system administration.
"""

import logging
from functools import wraps
from typing import Optional

from quart import request, jsonify

logger = logging.getLogger("quart.app")


def get_current_user_from_request():
    """
    Get current user from request context.
    
    Returns:
        User object or None
    """
    try:
        from trusted_data_agent.auth.middleware import get_current_user
        return get_current_user()
    except Exception as e:
        logger.warning(f"Failed to get current user: {e}")
        return None


def is_admin(user) -> bool:
    """
    Check if user has admin privileges.
    
    Args:
        user: User object
        
    Returns:
        True if user is admin
    """
    if not user:
        return False
    return getattr(user, 'is_admin', False)


def require_admin(f):
    """
    Decorator to require admin privileges for a route.
    
    Usage:
        @rest_api_bp.route('/api/v1/admin/users')
        @require_admin
        async def list_users():
            ...
    """
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        user = get_current_user_from_request()
        
        if not user:
            return jsonify({
                "status": "error",
                "message": "Authentication required"
            }), 401
        
        if not is_admin(user):
            logger.warning(f"Non-admin user {user.username} attempted to access admin endpoint")
            return jsonify({
                "status": "error",
                "message": "Admin privileges required"
            }), 403
        
        return await f(*args, **kwargs)
    
    return decorated_function


def can_manage_user(admin_user, target_user_id: str) -> bool:
    """
    Check if admin can manage a specific user.
    
    Prevents admins from modifying their own admin status.
    
    Args:
        admin_user: Admin user object
        target_user_id: Target user ID to manage
        
    Returns:
        True if management is allowed
    """
    if not admin_user or not is_admin(admin_user):
        return False
    
    # Prevent self-modification of admin status
    if admin_user.id == target_user_id:
        logger.warning(f"Admin {admin_user.username} attempted to modify their own account")
        return False
    
    return True
