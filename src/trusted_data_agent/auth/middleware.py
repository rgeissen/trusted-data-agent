"""
Authentication middleware for protecting routes.

Provides decorators for requiring authentication and authorization.
"""

import logging
from functools import wraps
from typing import Optional, Callable

from quart import request, jsonify
from werkzeug.exceptions import Unauthorized, Forbidden

from trusted_data_agent.auth.security import verify_auth_token
from trusted_data_agent.auth.database import get_db_session
from trusted_data_agent.auth.models import User

logger = logging.getLogger("quart.app")


def get_current_user() -> Optional[User]:
    """
    Extract and verify authentication token from request, return User object.
    
    Checks Authorization header for Bearer token.
    
    Returns:
        User object if authenticated, None otherwise
    """
    # Get token from Authorization header
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header[7:]  # Remove 'Bearer ' prefix
    
    # Verify token
    payload = verify_auth_token(token)
    if not payload:
        return None
    
    user_id = payload.get('user_id')
    if not user_id:
        return None
    
    # Load user from database
    try:
        with get_db_session() as session:
            user = session.query(User).filter_by(id=user_id).first()
            
            if not user:
                logger.warning(f"Token valid but user {user_id} not found")
                return None
            
            if not user.is_active:
                logger.warning(f"Inactive user {user_id} attempted to authenticate")
                return None
            
            # Detach from session to use outside context manager
            session.expunge(user)
            return user
    
    except Exception as e:
        logger.error(f"Error loading user during authentication: {e}", exc_info=True)
        return None


def require_auth(f: Callable) -> Callable:
    """
    Decorator to require authentication for a route.
    
    Usage:
        @app.route('/protected')
        @require_auth
        async def protected_route(current_user):
            return jsonify({'user': current_user.username})
    
    The decorated function will receive current_user as first argument.
    Returns 401 Unauthorized if not authenticated.
    """
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        current_user = get_current_user()
        
        if not current_user:
            logger.info(f"Unauthorized access attempt to {request.path}")
            return jsonify({
                'status': 'error',
                'message': 'Authentication required. Please login.'
            }), 401
        
        # Inject current_user as first argument
        return await f(current_user, *args, **kwargs)
    
    return decorated_function


def require_admin(f: Callable) -> Callable:
    """
    Decorator to require admin privileges for a route.
    
    Usage:
        @app.route('/admin/users')
        @require_admin
        async def admin_route(current_user):
            return jsonify({'users': get_all_users()})
    
    Returns 401 if not authenticated, 403 if not admin.
    """
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        current_user = get_current_user()
        
        if not current_user:
            logger.info(f"Unauthorized access attempt to {request.path}")
            return jsonify({
                'status': 'error',
                'message': 'Authentication required. Please login.'
            }), 401
        
        if not current_user.is_admin:
            logger.warning(f"Non-admin user {current_user.username} attempted to access {request.path}")
            return jsonify({
                'status': 'error',
                'message': 'Admin privileges required.'
            }), 403
        
        # Inject current_user as first argument
        return await f(current_user, *args, **kwargs)
    
    return decorated_function


def optional_auth(f: Callable) -> Callable:
    """
    Decorator for routes that work with or without authentication.
    
    Usage:
        @app.route('/api/data')
        @optional_auth
        async def data_route(current_user):
            if current_user:
                return personalized_data(current_user)
            else:
                return public_data()
    
    Always passes current_user (may be None) as first argument.
    """
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        current_user = get_current_user()
        
        # Inject current_user (may be None) as first argument
        return await f(current_user, *args, **kwargs)
    
    return decorated_function


def get_user_id_from_auth() -> Optional[str]:
    """
    Quick helper to get just the user_id from auth token.
    
    Returns:
        user_id string if authenticated, None otherwise
    """
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header[7:]
    payload = verify_auth_token(token)
    
    return payload.get('user_id') if payload else None


def get_request_context() -> dict:
    """
    Extract request context for audit logging.
    
    Returns:
        Dictionary with ip_address and user_agent
    """
    return {
        'ip_address': request.headers.get('X-Forwarded-For', request.remote_addr),
        'user_agent': request.headers.get('User-Agent', 'Unknown')
    }
