"""
Authentication REST API routes.

Provides endpoints for user registration, login, logout, and profile management.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any

from quart import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError

from trusted_data_agent.auth.database import get_db_session
from trusted_data_agent.auth.models import User, AuthToken, AuditLog
from trusted_data_agent.auth.security import (
    hash_password,
    verify_password,
    generate_auth_token,
    revoke_token,
    check_user_lockout,
    record_failed_login,
    reset_failed_login_attempts
)
from trusted_data_agent.auth.validators import (
    validate_registration_data,
    validate_username,
    validate_email,
    sanitize_user_input
)
from trusted_data_agent.auth.middleware import (
    require_auth,
    require_admin,
    get_request_context,
    get_current_user
)
from trusted_data_agent.auth.rate_limiter import check_ip_login_limit, check_ip_register_limit
from trusted_data_agent.auth.audit import (
    log_audit_event as log_audit_event_detailed,
    log_login_success,
    log_login_failure,
    log_registration,
    log_rate_limit_exceeded
)

logger = logging.getLogger("quart.app")

# Create Blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/v1/auth')


def ensure_user_default_collection(user_id: str):
    """
    Ensure a user has a default collection.
    Creates one if it doesn't exist.
    """
    from trusted_data_agent.core.collection_db import get_collection_db
    
    collection_db = get_collection_db()
    
    # Check if user already has a default collection
    user_collections = collection_db.get_user_owned_collections(user_id)
    has_default = any(
        c.get('name') == 'Default Collection' 
        for c in user_collections
    )
    
    if not has_default:
        try:
            collection_db.create_default_collection(user_id)
            logger.info(f"Created default collection for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to create default collection for user {user_id}: {e}", exc_info=True)


def log_audit_event(user_id: str, action: str, details: str, success: bool = True):
    """Helper to log audit events"""
    try:
        context = get_request_context()
        with get_db_session() as session:
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                details=details,
                ip_address=context['ip_address'],
                user_agent=context['user_agent'],
                status='success' if success else 'failure'
            )
            session.add(audit_log)
            session.commit()
    except Exception as e:
        logger.error(f"Failed to log audit event: {e}", exc_info=True)


@auth_bp.route('/register', methods=['POST'])
async def register():
    """
    Register a new user account.
    
    Request Body:
        {
            "username": "john_doe",
            "email": "john@example.com",
            "password": "SecurePass123!",
            "display_name": "John Doe"  // optional
        }
    
    Response:
        201: User created successfully
        400: Validation errors
        409: Username or email already exists
        429: Rate limit exceeded
        500: Server error
    """
    try:
        # Check rate limit
        allowed, retry_after = check_ip_register_limit()
        if not allowed:
            log_rate_limit_exceeded('ip:' + request.remote_addr, '/api/v1/auth/register')
            return jsonify({
                'status': 'error',
                'message': 'Registration rate limit exceeded',
                'retry_after': retry_after
            }), 429
        
        data = await request.get_json()
        
        # Extract fields
        username = sanitize_user_input(data.get('username', ''), max_length=30)
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        display_name = sanitize_user_input(data.get('display_name', ''), max_length=100)
        
        # Validate all fields
        is_valid, errors = validate_registration_data(username, email, password)
        if not is_valid:
            return jsonify({
                'status': 'error',
                'message': 'Validation failed',
                'errors': errors
            }), 400
        
        # Hash password
        password_hash = hash_password(password)
        
        # Create user in database
        try:
            with get_db_session() as session:
                # Check for existing user
                existing_user = session.query(User).filter(
                    (User.username == username) | (User.email == email)
                ).first()
                
                if existing_user:
                    if existing_user.username == username:
                        return jsonify({
                            'status': 'error',
                            'message': 'Username already taken'
                        }), 409
                    else:
                        return jsonify({
                            'status': 'error',
                            'message': 'Email already registered'
                        }), 409
                
                # Create new user
                user = User(
                    username=username,
                    email=email,
                    password_hash=password_hash,
                    display_name=display_name or username
                )
                
                session.add(user)
                session.commit()
                session.refresh(user)
                
                user_id = user.id
                user_uuid = user.id
                user_username = user.username
        
        except IntegrityError as e:
            logger.error(f"Database integrity error during registration: {e}")
            return jsonify({
                'status': 'error',
                'message': 'Registration failed. Please try again.'
            }), 500
        
        # Log audit event
        log_audit_event(
            user_id=user_id,
            action='user_registered',
            details=f'New user {user_username} registered',
            success=True
        )
        
        logger.info(f"New user registered: {user_username} (uuid: {user_uuid})")
        
        # Create default collection for new user
        ensure_user_default_collection(user_uuid)
        
        return jsonify({
            'status': 'success',
            'message': 'User registered successfully',
            'user': {
                'id': user_id,
                'username': user_username,
                'user_uuid': user_uuid,
                'display_name': display_name or username
            }
        }), 201
    
    except Exception as e:
        logger.error(f"Registration error: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Server error during registration'
        }), 500


@auth_bp.route('/login', methods=['POST'])
async def login():
    """
    Authenticate user and return JWT token.
    
    Request Body:
        {
            "username": "john_doe",
            "password": "SecurePass123!"
        }
    
    Response:
        200: Login successful, returns token
        400: Missing credentials
        401: Invalid credentials or account locked
        429: Rate limit exceeded
        500: Server error
    """
    try:
        # Check rate limit
        allowed, retry_after = check_ip_login_limit()
        if not allowed:
            log_rate_limit_exceeded('ip:' + request.remote_addr, '/api/v1/auth/login')
            return jsonify({
                'status': 'error',
                'message': 'Login rate limit exceeded',
                'retry_after': retry_after
            }), 429
        
        data = await request.get_json()
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({
                'status': 'error',
                'message': 'Username and password are required'
            }), 400
        
        # Load user from database
        with get_db_session() as session:
            user = session.query(User).filter_by(username=username).first()
            
            if not user:
                # Don't reveal if user exists
                logger.info(f"Login attempt with non-existent username: {username}")
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid username or password'
                }), 401
            
            # Check if account is locked
            is_locked, lockout_minutes = check_user_lockout(user)
            if is_locked:
                log_audit_event(
                    user_id=user.id,
                    action='login_failed',
                    details=f'Login attempt while account locked',
                    success=False
                )
                return jsonify({
                    'status': 'error',
                    'message': f'Account temporarily locked. Try again in {lockout_minutes} minutes.'
                }), 401
            
            # Check if account is active
            if not user.is_active:
                logger.warning(f"Login attempt for inactive account: {username}")
                log_audit_event(
                    user_id=user.id,
                    action='login_failed',
                    details='Login attempt for inactive account',
                    success=False
                )
                return jsonify({
                    'status': 'error',
                    'message': 'Account is inactive. Please contact support.'
                }), 401
            
            # Verify password
            if not verify_password(password, user.password_hash):
                logger.info(f"Failed login attempt for user: {username}")
                record_failed_login(user)
                log_audit_event(
                    user_id=user.id,
                    action='login_failed',
                    details='Invalid password',
                    success=False
                )
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid username or password'
                }), 401
            
            # Password correct - reset failed login count
            reset_failed_login_attempts(user)
            
            # Update last login
            user.last_login_at = datetime.utcnow()
            session.commit()
            
            # Generate JWT token
            context = get_request_context()
            token, _ = generate_auth_token(
                user_id=user.id,
                username=user.username,
                ip_address=context['ip_address'],
                user_agent=context['user_agent']
            )
            
            # Detach user for response
            user_id = user.id
            user_username = user.username
            user_uuid = user.id
            user_display_name = user.display_name
            user_email = user.email
            user_is_admin = user.is_admin
        
        # Log audit event
        log_audit_event(
            user_id=user_id,
            action='login_success',
            details=f'User {user_username} logged in',
            success=True
        )
        
        logger.info(f"User logged in: {user_username}")
        
        # Ensure user has a default collection
        ensure_user_default_collection(user_uuid)
        
        return jsonify({
            'status': 'success',
            'message': 'Login successful',
            'token': token,
            'user': {
                'id': user_id,
                'username': user_username,
                'user_uuid': user_uuid,
                'display_name': user_display_name,
                'email': user_email,
                'is_admin': user_is_admin
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Server error during login'
        }), 500


@auth_bp.route('/logout', methods=['POST'])
@require_auth
async def logout(current_user):
    """
    Logout user by revoking their current token.
    
    Requires: Authorization header with Bearer token
    
    Response:
        200: Logout successful
        401: Not authenticated
        500: Server error
    """
    try:
        # Get token from header
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            
            # Revoke token
            revoke_token(token)
            
            # Log audit event
            log_audit_event(
                user_id=current_user.id,
                action='logout',
                details=f'User {current_user.username} logged out',
                success=True
            )
            
            logger.info(f"User logged out: {current_user.username}")
            
            return jsonify({
                'status': 'success',
                'message': 'Logout successful'
            }), 200
        
        return jsonify({
            'status': 'error',
            'message': 'No token to revoke'
        }), 400
    
    except Exception as e:
        logger.error(f"Logout error: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Server error during logout'
        }), 500


@auth_bp.route('/me', methods=['GET'])
@require_auth
async def get_current_user_info(current_user):
    """
    Get current authenticated user's profile information.
    
    Requires: Authorization header with Bearer token
    
    Response:
        200: User information
        401: Not authenticated
    """
    from trusted_data_agent.auth.admin import get_user_tier
    from trusted_data_agent.core.config import APP_STATE
    
    # Get license tier from APP_STATE
    license_info = APP_STATE.get('license_info') or {}
    license_tier = license_info.get('tier', 'Unknown')
    
    user_tier = get_user_tier(current_user)
    logger.info(f"[AuthMe] User {current_user.username}: tier={user_tier}, is_admin={current_user.is_admin}")
    
    return jsonify({
        'status': 'success',
        'user': {
            'id': current_user.id,
            'username': current_user.username,
            'user_uuid': current_user.id,
            'display_name': current_user.display_name,
            'email': current_user.email,
            'is_admin': current_user.is_admin,
            'profile_tier': user_tier,
            'license_tier': license_tier,
            'is_active': current_user.is_active,
            'created_at': current_user.created_at.isoformat(),
            'last_login_at': current_user.last_login_at.isoformat() if current_user.last_login_at else None
        }
    }), 200


@auth_bp.route('/me/features', methods=['GET'])
@require_auth
async def get_user_features_endpoint(current_user):
    """
    Get all features available to the current user based on their profile tier.
    
    Requires: Authorization header with Bearer token
    
    Response:
        200: {
            "status": "success",
            "profile_tier": "developer",
            "features": ["execute_prompts", "view_own_sessions", ...],
            "feature_groups": {
                "session_management": true,
                "rag_management": true,
                ...
            },
            "feature_count": 35
        }
        401: Not authenticated
    """
    from trusted_data_agent.auth.features import (
        get_user_features,
        get_user_tier,
        FEATURE_GROUPS,
        user_has_feature_group
    )
    
    tier = get_user_tier(current_user)
    features = get_user_features(current_user)
    feature_list = sorted([f.value for f in features])
    
    # Check feature group access
    feature_groups = {}
    for group_name in FEATURE_GROUPS.keys():
        feature_groups[group_name] = user_has_feature_group(current_user, group_name)
    
    return jsonify({
        'status': 'success',
        'profile_tier': tier,
        'features': feature_list,
        'feature_groups': feature_groups,
        'feature_count': len(feature_list)
    }), 200


@auth_bp.route('/me/panes', methods=['GET'])
@require_auth
async def get_user_panes(current_user):
    """
    Get pane visibility configuration for current user based on their tier.
    
    Returns list of panes visible to the user's tier level.
    
    Requires: Authorization header with Bearer token
    
    Response:
        200: Pane configuration
        401: Not authenticated
        500: Server error
    """
    try:
        from trusted_data_agent.auth.models import PaneVisibility
        
        with get_db_session() as session:
            # Get all pane configurations
            panes = session.query(PaneVisibility).order_by(PaneVisibility.display_order).all()
            
            # If no panes exist, use defaults
            if not panes:
                # Import the initialization function
                from trusted_data_agent.api.admin_routes import initialize_default_panes
                panes = initialize_default_panes(session)
            
            panes_data = [pane.to_dict() for pane in panes]
        
        logger.info(f"[PaneVisibility] Returning {len(panes_data)} panes for user {current_user.username} (tier: {current_user.profile_tier})")
        logger.debug(f"[PaneVisibility] Panes: {panes_data}")
        
        return jsonify({
            "status": "success",
            "panes": panes_data,
            "user_tier": current_user.profile_tier
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get panes for user: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@auth_bp.route('/refresh', methods=['POST'])
@require_auth
async def refresh_token(current_user):
    """
    Refresh JWT token (get a new one).
    
    Requires: Authorization header with Bearer token
    
    Response:
        200: New token issued
        401: Not authenticated
        500: Server error
    """
    try:
        # Revoke old token
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            old_token = auth_header[7:]
            revoke_token(old_token)
        
        # Generate new token
        context = get_request_context()
        new_token, _ = generate_auth_token(
            user_id=current_user.id,
            username=current_user.username,
            ip_address=context['ip_address'],
            user_agent=context['user_agent']
        )
        
        # Log audit event
        log_audit_event(
            user_id=current_user.id,
            action='token_refreshed',
            details=f'User {current_user.username} refreshed auth token',
            success=True
        )
        
        logger.info(f"Token refreshed for user: {current_user.username}")
        
        return jsonify({
            'status': 'success',
            'message': 'Token refreshed successfully',
            'token': new_token
        }), 200
    
    except Exception as e:
        logger.error(f"Token refresh error: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Server error during token refresh'
        }), 500


@auth_bp.route('/change-password', methods=['POST'])
@require_auth
async def change_password(current_user):
    """
    Change user's password.
    
    Request Body:
        {
            "current_password": "OldPass123!",
            "new_password": "NewPass456!"
        }
    
    Requires: Authorization header with Bearer token
    
    Response:
        200: Password changed successfully
        400: Validation errors
        401: Current password incorrect
        500: Server error
    """
    try:
        data = await request.get_json()
        
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')
        
        if not current_password or not new_password:
            return jsonify({
                'status': 'error',
                'message': 'Current password and new password are required'
            }), 400
        
        # Verify current password
        with get_db_session() as session:
            user = session.query(User).filter_by(id=current_user.id).first()
            
            if not verify_password(current_password, user.password_hash):
                log_audit_event(
                    user_id=current_user.id,
                    action='password_change_failed',
                    details='Incorrect current password',
                    success=False
                )
                return jsonify({
                    'status': 'error',
                    'message': 'Current password is incorrect'
                }), 401
            
            # Validate new password strength
            from trusted_data_agent.auth.security import validate_password_strength
            is_valid, errors = validate_password_strength(new_password)
            if not is_valid:
                return jsonify({
                    'status': 'error',
                    'message': 'New password does not meet requirements',
                    'errors': errors
                }), 400
            
            # Hash and update password
            user.password_hash = hash_password(new_password)
            session.commit()
        
        # Log audit event
        log_audit_event(
            user_id=current_user.id,
            action='password_changed',
            details=f'User {current_user.username} changed password',
            success=True
        )
        
        logger.info(f"Password changed for user: {current_user.username}")
        
        return jsonify({
            'status': 'success',
            'message': 'Password changed successfully'
        }), 200
    
    except Exception as e:
        logger.error(f"Password change error: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Server error during password change'
        }), 500


# Admin-only endpoint example
@auth_bp.route('/admin/users', methods=['GET'])
@require_admin
async def list_users(current_user):
    """
    List all users (admin only).
    
    Requires: Authorization header with Bearer token (admin user)
    
    Response:
        200: List of users
        401: Not authenticated
        403: Not authorized (not admin)
    """
    try:
        with get_db_session() as session:
            users = session.query(User).all()
            
            user_list = [
                {
                    'id': user.id,
                    'username': user.username,
                    'user_uuid': user.id,
                    'email': user.email,
                    'display_name': user.display_name,
                    'is_admin': user.is_admin,
                    'is_active': user.is_active,
                    'created_at': user.created_at.isoformat(),
                    'last_login_at': user.last_login_at.isoformat() if user.last_login_at else None
                }
                for user in users
            ]
        
        return jsonify({
            'status': 'success',
            'users': user_list,
            'total': len(user_list)
        }), 200
    
    except Exception as e:
        logger.error(f"List users error: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Server error listing users'
        }), 500


# ============================================================================
# Access Token Management Endpoints
# ============================================================================

@auth_bp.route("/tokens", methods=["POST"])
async def create_access_token():
    """
    Create a new access token for REST API authentication.
    
    Request body:
    {
        "name": "My API Token",
        "expires_in_days": 90  // optional, null = never expires
    }
    
    Returns:
    {
        "status": "success",
        "token": "tda_xxxxxxxx...",  // ONLY shown once!
        "token_id": "uuid",
        "name": "My API Token",
        "created_at": "2025-11-25T...",
        "expires_at": "2026-02-25T..." // or null
    }
    """
    from trusted_data_agent.auth.middleware import require_auth
    from trusted_data_agent.auth.security import create_access_token as create_token
    
    # Require authentication
    current_user = get_current_user()
    
    if not current_user:
        return jsonify({
            'status': 'error',
            'message': 'Authentication required'
        }), 401
    
    try:
        data = await request.get_json()
        
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Request body required'
            }), 400
        
        name = data.get('name', '').strip()
        expires_in_days = data.get('expires_in_days')
        
        if not name:
            return jsonify({
                'status': 'error',
                'message': 'Token name is required'
            }), 400
        
        if len(name) > 100:
            return jsonify({
                'status': 'error',
                'message': 'Token name must be 100 characters or less'
            }), 400
        
        # Validate expiration
        if expires_in_days is not None:
            if not isinstance(expires_in_days, int) or expires_in_days < 1:
                return jsonify({
                    'status': 'error',
                    'message': 'expires_in_days must be a positive integer'
                }), 400
        
        # Create token
        token_id, token = create_token(current_user.id, name, expires_in_days)
        
        # Get token details
        from trusted_data_agent.auth.models import AccessToken
        with get_db_session() as session:
            access_token = session.query(AccessToken).filter_by(id=token_id).first()
            token_data = access_token.to_dict()
        
        logger.info(f"User {current_user.username} created access token '{name}'")
        
        return jsonify({
            'status': 'success',
            'token': token,  # Full token - ONLY shown once!
            'token_id': token_id,
            'name': name,
            'token_prefix': token_data['token_prefix'],
            'created_at': token_data['created_at'],
            'expires_at': token_data['expires_at']
        }), 201
    
    except Exception as e:
        logger.error(f"Create access token error: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Failed to create access token'
        }), 500


@auth_bp.route("/tokens", methods=["GET"])
async def list_access_tokens():
    """
    List all access tokens for the authenticated user.
    
    Query parameters:
    - include_revoked: true/false (default: false)
    
    Returns:
    {
        "status": "success",
        "tokens": [
            {
                "id": "uuid",
                "name": "My Token",
                "token_prefix": "tda_abc12...",
                "created_at": "...",
                "last_used_at": "...",
                "expires_at": "..." or null,
                "revoked": false,
                "use_count": 42
            }
        ]
    }
    """
    from trusted_data_agent.auth.security import list_access_tokens as list_tokens
    
    current_user = get_current_user()
    
    if not current_user:
        return jsonify({
            'status': 'error',
            'message': 'Authentication required'
        }), 401
    
    try:
        include_revoked = request.args.get('include_revoked', 'false').lower() == 'true'
        
        tokens = list_tokens(current_user.id, include_revoked=include_revoked)
        
        return jsonify({
            'status': 'success',
            'tokens': tokens
        }), 200
    
    except Exception as e:
        logger.error(f"List access tokens error: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Failed to list access tokens'
        }), 500


@auth_bp.route("/tokens/<token_id>", methods=["DELETE"])
async def revoke_access_token(token_id: str):
    """
    Revoke an access token.
    
    Path parameter:
    - token_id: UUID of the token to revoke
    
    Returns:
    {
        "status": "success",
        "message": "Token revoked successfully"
    }
    """
    from trusted_data_agent.auth.security import revoke_access_token as revoke_token
    
    current_user = get_current_user()
    
    if not current_user:
        return jsonify({
            'status': 'error',
            'message': 'Authentication required'
        }), 401
    
    try:
        success = revoke_token(token_id, current_user.id)
        
        if not success:
            return jsonify({
                'status': 'error',
                'message': 'Token not found or already revoked'
            }), 404
        
        logger.info(f"User {current_user.username} revoked access token {token_id}")
        
        return jsonify({
            'status': 'success',
            'message': 'Token revoked successfully'
        }), 200
    
    except Exception as e:
        logger.error(f"Revoke access token error: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Failed to revoke access token'
        }), 500


@auth_bp.route('/admin/rate-limit-settings', methods=['GET'])
@require_admin
async def get_rate_limit_settings(current_user):
    """
    Get current rate limiting configuration settings.
    
    Admin only endpoint.
    
    Returns:
        200: Rate limiting settings
        401: Unauthorized
        403: Forbidden (not admin)
        500: Server error
    """
    from trusted_data_agent.auth.models import SystemSettings
    
    try:
        with get_db_session() as session:
            # Fetch all rate limit related settings
            rate_limit_keys = [
                'rate_limit_enabled',
                'rate_limit_user_prompts_per_hour',
                'rate_limit_user_prompts_per_day',
                'rate_limit_user_configs_per_hour',
                'rate_limit_ip_login_per_minute',
                'rate_limit_ip_register_per_hour',
                'rate_limit_ip_api_per_minute'
            ]
            
            settings = {}
            for key in rate_limit_keys:
                setting = session.query(SystemSettings).filter_by(setting_key=key).first()
                if setting:
                    settings[key] = {
                        'value': setting.setting_value,
                        'description': setting.description
                    }
            
            return jsonify({
                'status': 'success',
                'settings': settings
            }), 200
    
    except Exception as e:
        logger.error(f"Get rate limit settings error: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve rate limit settings'
        }), 500


@auth_bp.route('/admin/rate-limit-settings', methods=['PUT'])
@require_admin
async def update_rate_limit_settings():
    """
    Update rate limiting configuration settings.
    
    Admin only endpoint.
    
    Request Body:
        {
            "rate_limit_enabled": "true",
            "rate_limit_user_prompts_per_hour": "100",
            ...
        }
    
    Returns:
        200: Settings updated successfully
        400: Invalid request
        401: Unauthorized
        403: Forbidden (not admin)
        500: Server error
    """
    from trusted_data_agent.auth.models import SystemSettings
    
    current_user = get_current_user()
    
    try:
        data = await request.get_json()
        
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No settings provided'
            }), 400
        
        # Valid setting keys
        valid_keys = {
            'rate_limit_enabled',
            'rate_limit_user_prompts_per_hour',
            'rate_limit_user_prompts_per_day',
            'rate_limit_user_configs_per_hour',
            'rate_limit_ip_login_per_minute',
            'rate_limit_ip_register_per_hour',
            'rate_limit_ip_api_per_minute'
        }
        
        # Validate input
        invalid_keys = set(data.keys()) - valid_keys
        if invalid_keys:
            return jsonify({
                'status': 'error',
                'message': f'Invalid setting keys: {", ".join(invalid_keys)}'
            }), 400
        
        with get_db_session() as session:
            updated_settings = []
            
            for key, value in data.items():
                # Convert value to string
                value_str = str(value).lower() if key == 'rate_limit_enabled' else str(value)
                
                # Validate boolean for enabled flag
                if key == 'rate_limit_enabled' and value_str not in ('true', 'false'):
                    return jsonify({
                        'status': 'error',
                        'message': f'Invalid value for {key}: must be true or false'
                    }), 400
                
                # Validate integer for numeric settings
                if key != 'rate_limit_enabled':
                    try:
                        int_value = int(value_str)
                        if int_value < 0:
                            return jsonify({
                                'status': 'error',
                                'message': f'Invalid value for {key}: must be non-negative integer'
                            }), 400
                    except ValueError:
                        return jsonify({
                            'status': 'error',
                            'message': f'Invalid value for {key}: must be an integer'
                        }), 400
                
                # Update or create setting
                setting = session.query(SystemSettings).filter_by(setting_key=key).first()
                if setting:
                    setting.setting_value = value_str
                    setting.updated_at = datetime.now()
                else:
                    # Create new setting if it doesn't exist
                    setting = SystemSettings(
                        setting_key=key,
                        setting_value=value_str,
                        description=f'Rate limiting setting: {key}'
                    )
                    session.add(setting)
                
                updated_settings.append(key)
            
            session.commit()
            
            # Log the configuration change
            log_audit_event_detailed(
                user_id=current_user.id,
                action='update_rate_limit_settings',
                resource='system_settings',
                status='success',
                details=f'Updated settings: {", ".join(updated_settings)}'
            )
            
            logger.info(f"User {current_user.username} updated rate limit settings: {updated_settings}")
            
            return jsonify({
                'status': 'success',
                'message': 'Rate limit settings updated successfully',
                'updated_settings': updated_settings
            }), 200
    
    except Exception as e:
        logger.error(f"Update rate limit settings error: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Failed to update rate limit settings'
        }), 500
