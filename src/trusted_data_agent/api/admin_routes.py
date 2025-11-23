"""
REST API routes for Phase 4 admin and credential management features.

Includes:
- User management (admin only)
- Credential storage/retrieval
- Audit log access
- System administration
"""

import logging
from datetime import datetime, timezone

from quart import Blueprint, request, jsonify

from trusted_data_agent.auth.admin import require_admin, get_current_user_from_request, can_manage_user
from trusted_data_agent.auth.database import get_db_session
from trusted_data_agent.auth.models import User, AuditLog
from trusted_data_agent.auth import audit, encryption
from trusted_data_agent.auth.security import hash_password
from trusted_data_agent.core import configuration_service

admin_api_bp = Blueprint('admin_api', __name__)
logger = logging.getLogger("quart.app")


def _get_user_uuid_from_request():
    """
    Extract user ID from request (from auth token or header).
    
    IMPORTANT: Returns user.id (database primary key), NOT user.user_uuid.
    The user.id is required for foreign key constraints in user_credentials table.
    """
    user = get_current_user_from_request()
    if user:
        return user.id  # Return database ID, not user_uuid
    
    # Fallback to header (for non-auth mode compatibility)
    return request.headers.get("X-TDA-User-UUID")


# ==============================================================================
# CREDENTIAL MANAGEMENT ENDPOINTS
# ==============================================================================

@admin_api_bp.route("/v1/credentials", methods=["GET"])
async def list_credentials():
    """
    List all providers with stored credentials for current user.
    
    Returns:
    {
        "status": "success",
        "providers": ["Amazon", "Google"]
    }
    """
    user_uuid = _get_user_uuid_from_request()
    if not user_uuid:
        return jsonify({"status": "error", "message": "Authentication required"}), 401
    
    result = await configuration_service.list_user_providers(user_uuid)
    
    if result["status"] == "success":
        return jsonify(result), 200
    else:
        return jsonify(result), 500


@admin_api_bp.route("/v1/credentials/<provider>", methods=["GET", "POST", "DELETE"])
async def manage_provider_credentials(provider: str):
    """
    Manage credentials for a specific provider.
    
    GET: Check if credentials exist (doesn't return actual values)
    POST: Store new credentials
    DELETE: Delete stored credentials
    
    POST body:
    {
        "credentials": {
            "apiKey": "...",  // For Google, Anthropic, etc.
            "aws_access_key_id": "...",  // For Amazon
            "aws_secret_access_key": "...",
            "aws_region": "..."
        }
    }
    """
    user_uuid = _get_user_uuid_from_request()
    if not user_uuid:
        return jsonify({"status": "error", "message": "Authentication required"}), 401
    
    if request.method == "GET":
        # Check if credentials exist
        result = await configuration_service.retrieve_credentials_for_provider(user_uuid, provider)
        
        has_credentials = result.get("credentials") is not None
        return jsonify({
            "status": "success",
            "provider": provider,
            "has_credentials": has_credentials,
            "credential_keys": list(result["credentials"].keys()) if has_credentials else []
        }), 200
    
    elif request.method == "POST":
        # Store credentials
        data = await request.get_json()
        
        if not data or "credentials" not in data:
            return jsonify({
                "status": "error",
                "message": "Request body must contain 'credentials' field"
            }), 400
        
        result = await configuration_service.store_credentials_for_provider(
            user_uuid,
            provider,
            data["credentials"]
        )
        
        if result["status"] == "success":
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    
    elif request.method == "DELETE":
        # Delete credentials
        result = await configuration_service.delete_credentials_for_provider(user_uuid, provider)
        
        if result["status"] == "success":
            return jsonify(result), 200
        else:
            return jsonify(result), 404


@admin_api_bp.route("/v1/credentials/<provider>/test", methods=["POST"])
async def test_provider_credentials(provider: str):
    """
    Test stored credentials by attempting a connection.
    
    Returns:
    {
        "status": "success"/"error",
        "message": "Credentials are valid" or error details
    }
    """
    user_uuid = _get_user_uuid_from_request()
    if not user_uuid:
        return jsonify({"status": "error", "message": "Authentication required"}), 401
    
    # Retrieve stored credentials
    cred_result = await configuration_service.retrieve_credentials_for_provider(user_uuid, provider)
    
    if not cred_result.get("credentials"):
        return jsonify({
            "status": "error",
            "message": f"No stored credentials found for {provider}"
        }), 404
    
    # Test the credentials by attempting a lightweight operation
    # This reuses validation logic from setup_and_categorize_services
    try:
        credentials = cred_result["credentials"]
        
        if provider == "Google":
            import google.generativeai as genai
            genai.configure(api_key=credentials.get("apiKey"))
            # Try listing models
            list(genai.list_models())
            
        elif provider == "Anthropic":
            from anthropic import AsyncAnthropic
            client = AsyncAnthropic(api_key=credentials.get("apiKey"))
            await client.models.list()
            
        elif provider == "Amazon":
            import boto3
            client = boto3.client(
                'bedrock-runtime',
                aws_access_key_id=credentials.get("aws_access_key_id"),
                aws_secret_access_key=credentials.get("aws_secret_access_key"),
                region_name=credentials.get("aws_region")
            )
            # List foundation models as test
            client.list_foundation_models()
            
        else:
            return jsonify({
                "status": "error",
                "message": f"Credential testing not yet implemented for {provider}"
            }), 501
        
        return jsonify({
            "status": "success",
            "message": f"{provider} credentials are valid"
        }), 200
        
    except Exception as e:
        logger.error(f"Credential test failed for {provider}: {e}")
        return jsonify({
            "status": "error",
            "message": f"Credential test failed: {str(e)}"
        }), 400


# ==============================================================================
# AUDIT LOG ENDPOINTS
# ==============================================================================

@admin_api_bp.route("/v1/auth/me/audit-logs", methods=["GET"])
async def get_my_audit_logs():
    """
    Get current user's audit logs.
    
    Query params:
    - limit: Number of records (default 100)
    - offset: Skip records (default 0)
    - action: Filter by action type
    
    Returns:
    {
        "status": "success",
        "logs": [...],
        "total": 150
    }
    """
    user_uuid = _get_user_uuid_from_request()
    if not user_uuid:
        return jsonify({"status": "error", "message": "Authentication required"}), 401
    
    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))
    action_filter = request.args.get('action')
    
    logs = audit.get_user_audit_logs(user_uuid, limit=limit, offset=offset, action_filter=action_filter)
    
    return jsonify({
        "status": "success",
        "logs": logs,
        "total": len(logs)
    }), 200


# ==============================================================================
# ADMIN USER MANAGEMENT ENDPOINTS
# ==============================================================================

@admin_api_bp.route("/v1/admin/users", methods=["GET", "POST"])
@require_admin
async def manage_users():
    """
    Manage users (admin only).
    
    GET - List all users:
    Query params:
    - limit: Number of records (default 50)
    - offset: Skip records (default 0)
    - search: Search by username or email
    - active_only: Filter active users (default false)
    
    POST - Create new user:
    Body:
    {
        "username": "newuser",
        "email": "user@example.com",
        "password": "password123",
        "display_name": "New User",
        "profile_tier": "user"
    }
    
    Returns:
    {
        "status": "success",
        "users": [...] or "user": {...},
        "total": 25
    }
    """
    if request.method == "POST":
        # Create new user
        admin_user = get_current_user_from_request()
        data = await request.get_json()
        
        required_fields = ['username', 'email', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    "status": "error",
                    "message": f"Missing required field: {field}"
                }), 400
        
        try:
            import uuid
            
            with get_db_session() as session:
                # Check if username already exists
                existing = session.query(User).filter_by(username=data['username']).first()
                if existing:
                    return jsonify({
                        "status": "error",
                        "message": "Username already exists"
                    }), 400
                
                # Check if email already exists
                existing_email = session.query(User).filter_by(email=data['email']).first()
                if existing_email:
                    return jsonify({
                        "status": "error",
                        "message": "Email already exists"
                    }), 400
                
                # Create new user
                new_user = User(
                    id=str(uuid.uuid4()),
                    user_uuid=str(uuid.uuid4()),
                    username=data['username'],
                    email=data['email'],
                    password_hash=hash_password(data['password']),
                    display_name=data.get('display_name', data['username']),
                    full_name=data.get('full_name'),
                    profile_tier=data.get('profile_tier', 'user'),
                    is_admin=(data.get('profile_tier', 'user') == 'admin'),
                    is_active=True,
                    failed_login_attempts=0,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                
                session.add(new_user)
                session.commit()
                
                # Log admin action
                audit.log_admin_action(
                    admin_user.id,
                    "user_create",
                    new_user.id,
                    f"Created user {new_user.username}"
                )
                
                return jsonify({
                    "status": "success",
                    "message": "User created successfully",
                    "user": {
                        "id": new_user.id,
                        "username": new_user.username,
                        "email": new_user.email,
                        "display_name": new_user.display_name,
                        "profile_tier": new_user.profile_tier
                    }
                }), 201
                
        except Exception as e:
            logger.error(f"Failed to create user: {e}", exc_info=True)
            return jsonify({"status": "error", "message": str(e)}), 500
    
    # GET - List users
    limit = int(request.args.get('limit', 50))
    offset = int(request.args.get('offset', 0))
    search = request.args.get('search')
    active_only = request.args.get('active_only', 'false').lower() == 'true'
    
    try:
        with get_db_session() as session:
            query = session.query(User)
            
            if active_only:
                query = query.filter_by(is_active=True)
            
            if search:
                query = query.filter(
                    (User.username.ilike(f'%{search}%')) |
                    (User.email.ilike(f'%{search}%'))
                )
            
            total = query.count()
            users = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
            
            # Get current user for comparison
            current_user = get_current_user_from_request()
            
            user_list = []
            for user in users:
                # Get feature count for this user's tier
                from trusted_data_agent.auth.features import get_user_features
                user_features = get_user_features(user)
                
                user_list.append({
                    'id': user.id,
                    'user_uuid': user.user_uuid,
                    'username': user.username,
                    'email': user.email,
                    'display_name': user.display_name,
                    'is_active': user.is_active,
                    'is_admin': user.is_admin,
                    'profile_tier': user.profile_tier,
                    'feature_count': len(user_features),
                    'is_current_user': current_user and user.id == current_user.id,
                    'created_at': user.created_at.isoformat(),
                    'last_login_at': user.last_login_at.isoformat() if user.last_login_at else None,
                    'failed_login_attempts': user.failed_login_attempts
                })
            
            return jsonify({
                "status": "success",
                "users": user_list,
                "total": total,
                "limit": limit,
                "offset": offset
            }), 200
            
    except Exception as e:
        logger.error(f"Failed to list users: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@admin_api_bp.route("/v1/admin/users/<user_id>", methods=["GET", "PATCH", "DELETE"])
@require_admin
async def manage_user(user_id: str):
    """
    Manage a specific user (admin only).
    
    GET: Get user details with audit history
    PATCH: Update user (activate/deactivate, change role)
    DELETE: Soft delete user
    
    PATCH body:
    {
        "is_active": true/false,
        "is_admin": true/false,
        "display_name": "New Name"
    }
    """
    admin_user = get_current_user_from_request()
    
    if request.method == "GET":
        try:
            with get_db_session() as session:
                user = session.query(User).filter_by(id=user_id).first()
                
                if not user:
                    return jsonify({"status": "error", "message": "User not found"}), 404
                
                # Get recent audit logs
                audit_logs = audit.get_user_audit_logs(user.user_uuid, limit=20)
                
                # Get stored credential providers
                providers = encryption.list_user_providers(user.user_uuid)
                
                return jsonify({
                    "status": "success",
                    "user": {
                        'id': user.id,
                        'user_uuid': user.user_uuid,
                        'username': user.username,
                        'email': user.email,
                        'display_name': user.display_name,
                        'full_name': user.full_name,
                        'is_active': user.is_active,
                        'is_admin': user.is_admin,
                        'profile_tier': user.profile_tier,
                        'created_at': user.created_at.isoformat(),
                        'updated_at': user.updated_at.isoformat(),
                        'last_login_at': user.last_login_at.isoformat() if user.last_login_at else None,
                        'failed_login_attempts': user.failed_login_attempts,
                        'locked_until': user.locked_until.isoformat() if user.locked_until else None,
                        'stored_providers': providers
                    },
                    "recent_audit_logs": audit_logs
                }), 200
                
        except Exception as e:
            logger.error(f"Failed to get user: {e}", exc_info=True)
            return jsonify({"status": "error", "message": str(e)}), 500
    
    elif request.method == "PATCH":
        # Prevent self-modification
        if not can_manage_user(admin_user, user_id):
            return jsonify({
                "status": "error",
                "message": "Cannot modify your own admin status"
            }), 403
        
        data = await request.get_json()
        
        try:
            with get_db_session() as session:
                user = session.query(User).filter_by(id=user_id).first()
                
                if not user:
                    return jsonify({"status": "error", "message": "User not found"}), 404
                
                changes = []
                
                if 'is_active' in data:
                    user.is_active = bool(data['is_active'])
                    changes.append(f"is_active={user.is_active}")
                
                if 'is_admin' in data:
                    user.is_admin = bool(data['is_admin'])
                    # Sync profile_tier with is_admin for backward compatibility
                    if user.is_admin:
                        user.profile_tier = 'admin'
                    changes.append(f"is_admin={user.is_admin}")
                
                if 'profile_tier' in data:
                    from trusted_data_agent.auth.admin import PROFILE_TIER_USER, PROFILE_TIER_DEVELOPER, PROFILE_TIER_ADMIN
                    new_tier = data['profile_tier'].lower()
                    valid_tiers = [PROFILE_TIER_USER, PROFILE_TIER_DEVELOPER, PROFILE_TIER_ADMIN]
                    if new_tier in valid_tiers:
                        user.profile_tier = new_tier
                        # Sync is_admin flag
                        user.is_admin = (new_tier == PROFILE_TIER_ADMIN)
                        changes.append(f"profile_tier={new_tier}")
                
                if 'display_name' in data:
                    user.display_name = data['display_name']
                    changes.append(f"display_name={user.display_name}")
                
                if 'email' in data:
                    # Check if email is already taken by another user
                    existing = session.query(User).filter_by(email=data['email']).first()
                    if existing and existing.id != user_id:
                        return jsonify({
                            "status": "error",
                            "message": "Email already in use"
                        }), 400
                    user.email = data['email']
                    changes.append(f"email={user.email}")
                
                if 'username' in data:
                    # Check if username is already taken by another user
                    existing = session.query(User).filter_by(username=data['username']).first()
                    if existing and existing.id != user_id:
                        return jsonify({
                            "status": "error",
                            "message": "Username already in use"
                        }), 400
                    user.username = data['username']
                    changes.append(f"username={user.username}")
                
                if 'password' in data and data['password']:
                    # Admin can reset user password
                    user.password_hash = hash_password(data['password'])
                    changes.append("password=***")
                
                user.updated_at = datetime.now(timezone.utc)
                
                # Log admin action
                audit.log_admin_action(
                    admin_user.id,
                    "user_update",
                    user.id,
                    f"Updated user: {', '.join(changes)}"
                )
                
                return jsonify({
                    "status": "success",
                    "message": f"User updated: {', '.join(changes)}"
                }), 200
                
        except Exception as e:
            logger.error(f"Failed to update user: {e}", exc_info=True)
            return jsonify({"status": "error", "message": str(e)}), 500
    
    elif request.method == "DELETE":
        # Prevent self-deletion
        if not can_manage_user(admin_user, user_id):
            return jsonify({
                "status": "error",
                "message": "Cannot delete your own account"
            }), 403
        
        try:
            with get_db_session() as session:
                user = session.query(User).filter_by(id=user_id).first()
                
                if not user:
                    return jsonify({"status": "error", "message": "User not found"}), 404
                
                # Soft delete by deactivating
                user.is_active = False
                user.updated_at = datetime.now(timezone.utc)
                
                # Log admin action
                audit.log_admin_action(
                    admin_user.id,
                    "user_delete",
                    user.id,
                    f"Deactivated user {user.username}"
                )
                
                return jsonify({
                    "status": "success",
                    "message": f"User {user.username} deactivated"
                }), 200
                
        except Exception as e:
            logger.error(f"Failed to delete user: {e}", exc_info=True)
            return jsonify({"status": "error", "message": str(e)}), 500


@admin_api_bp.route("/v1/admin/users/<user_id>/unlock", methods=["POST"])
@require_admin
async def unlock_user(user_id: str):
    """
    Unlock a locked user account (admin only).
    
    Returns:
    {
        "status": "success",
        "message": "User unlocked"
    }
    """
    admin_user = get_current_user_from_request()
    
    try:
        with get_db_session() as session:
            user = session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return jsonify({"status": "error", "message": "User not found"}), 404
            
            user.failed_login_attempts = 0
            user.locked_until = None
            user.updated_at = datetime.now(timezone.utc)
            
            # Log admin action
            audit.log_admin_action(
                admin_user.id,
                "user_unlock",
                user.id,
                f"Unlocked user {user.username}"
            )
            
            return jsonify({
                "status": "success",
                "message": f"User {user.username} unlocked"
            }), 200
            
    except Exception as e:
        logger.error(f"Failed to unlock user: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@admin_api_bp.route("/v1/admin/users/<user_id>/tier", methods=["PATCH"])
@require_admin
async def change_user_tier(user_id: str):
    """
    Change user's profile tier (admin only).
    
    Profile tiers:
    - user: Basic access (default)
    - developer: Advanced features (RAG, templates, testing)
    - admin: Full system access
    
    POST body:
    {
        "profile_tier": "developer"
    }
    
    Returns:
    {
        "status": "success",
        "message": "User promoted to developer tier",
        "user": {
            "id": "...",
            "username": "...",
            "profile_tier": "developer"
        }
    }
    """
    from trusted_data_agent.auth.admin import PROFILE_TIER_USER, PROFILE_TIER_DEVELOPER, PROFILE_TIER_ADMIN
    
    admin_user = get_current_user_from_request()
    
    # Prevent self-modification
    if not can_manage_user(admin_user, user_id):
        return jsonify({
            "status": "error",
            "message": "Cannot modify your own profile tier"
        }), 403
    
    data = await request.get_json()
    
    if not data or 'profile_tier' not in data:
        return jsonify({
            "status": "error",
            "message": "Request body must contain 'profile_tier' field"
        }), 400
    
    new_tier = data['profile_tier'].lower()
    valid_tiers = [PROFILE_TIER_USER, PROFILE_TIER_DEVELOPER, PROFILE_TIER_ADMIN]
    
    if new_tier not in valid_tiers:
        return jsonify({
            "status": "error",
            "message": f"Invalid profile tier. Must be one of: {', '.join(valid_tiers)}"
        }), 400
    
    try:
        with get_db_session() as session:
            user = session.query(User).filter_by(id=user_id).first()
            
            if not user:
                return jsonify({"status": "error", "message": "User not found"}), 404
            
            old_tier = user.profile_tier
            user.profile_tier = new_tier
            
            # Sync is_admin flag for backward compatibility
            user.is_admin = (new_tier == PROFILE_TIER_ADMIN)
            
            user.updated_at = datetime.now(timezone.utc)
            
            # Log admin action
            audit.log_admin_action(
                admin_user.id,
                "tier_change",
                user.id,
                f"Changed profile tier: {old_tier} -> {new_tier}"
            )
            
            action = "promoted" if valid_tiers.index(new_tier) > valid_tiers.index(old_tier) else "changed"
            
            return jsonify({
                "status": "success",
                "message": f"User {action} to {new_tier} tier",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "profile_tier": user.profile_tier,
                    "is_admin": user.is_admin
                }
            }), 200
            
    except Exception as e:
        logger.error(f"Failed to change user tier: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@admin_api_bp.route("/v1/admin/stats", methods=["GET"])
@require_admin
async def get_admin_stats():
    """
    Get system statistics (admin only).
    
    Returns:
    {
        "status": "success",
        "stats": {
            "total_users": 25,
            "active_users": 20,
            "admin_users": 2,
            "locked_users": 1,
            "recent_logins_24h": 15,
            "recent_registrations_7d": 5
        }
    }
    """
    try:
        from datetime import timedelta
        
        with get_db_session() as session:
            now = datetime.now(timezone.utc)
            day_ago = now - timedelta(days=1)
            week_ago = now - timedelta(days=7)
            
            total_users = session.query(User).count()
            active_users = session.query(User).filter_by(is_active=True).count()
            admin_users = session.query(User).filter_by(is_admin=True).count()
            locked_users = session.query(User).filter(User.locked_until > now).count()
            
            recent_logins = session.query(User).filter(User.last_login_at >= day_ago).count()
            recent_registrations = session.query(User).filter(User.created_at >= week_ago).count()
            
            # Recent audit events
            recent_audits = session.query(AuditLog).filter(AuditLog.timestamp >= day_ago).count()
            
            # Profile tier distribution
            from sqlalchemy import func
            tier_counts = session.query(
                User.profile_tier, 
                func.count(User.id)
            ).group_by(User.profile_tier).all()
            
            tier_distribution = {tier: count for tier, count in tier_counts}
            
            return jsonify({
                "status": "success",
                "stats": {
                    "total_users": total_users,
                    "active_users": active_users,
                    "admin_users": admin_users,
                    "locked_users": locked_users,
                    "recent_logins_24h": recent_logins,
                    "recent_registrations_7d": recent_registrations,
                    "recent_audit_events_24h": recent_audits,
                    "tier_distribution": tier_distribution
                }
            }), 200
            
    except Exception as e:
        logger.error(f"Failed to get stats: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


# ==============================================================================
# FEATURE MANAGEMENT ENDPOINTS
# ==============================================================================

@admin_api_bp.route("/v1/admin/features", methods=["GET"])
@require_admin
async def get_all_features():
    """
    Get all features with their tier mappings and metadata.
    
    Returns:
    {
        "status": "success",
        "features": [
            {
                "name": "execute_prompts",
                "display_name": "Execute Prompts",
                "required_tier": "user",
                "category": "Core Execution",
                "description": "Execute AI prompts"
            },
            ...
        ],
        "feature_count_by_tier": {
            "user": 19,
            "developer": 25,
            "admin": 22
        }
    }
    """
    try:
        from trusted_data_agent.auth.features import (
            Feature, FEATURE_TIER_MAP, get_feature_info
        )
        from trusted_data_agent.auth.admin import PROFILE_TIER_USER, PROFILE_TIER_DEVELOPER, PROFILE_TIER_ADMIN
        
        feature_info = get_feature_info()
        
        # Count features by tier (features exclusive to that tier)
        tier_counts = {
            PROFILE_TIER_USER: 0,
            PROFILE_TIER_DEVELOPER: 0,
            PROFILE_TIER_ADMIN: 0
        }
        
        for feature_name, tier in FEATURE_TIER_MAP.items():
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        
        return jsonify({
            "status": "success",
            "features": feature_info,
            "feature_count_by_tier": tier_counts
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get features: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@admin_api_bp.route("/v1/admin/features/<feature_name>/tier", methods=["PATCH"])
@require_admin
async def update_feature_tier(feature_name: str):
    """
    Update the required tier for a specific feature.
    
    Request body:
    {
        "required_tier": "developer"  // "user", "developer", or "admin"
    }
    
    Returns:
    {
        "status": "success",
        "feature": "create_rag_collections",
        "old_tier": "developer",
        "new_tier": "admin"
    }
    """
    try:
        from trusted_data_agent.auth.features import Feature, FEATURE_TIER_MAP
        from trusted_data_agent.auth.admin import (
            PROFILE_TIER_USER, PROFILE_TIER_DEVELOPER, PROFILE_TIER_ADMIN, TIER_HIERARCHY
        )
        
        data = await request.get_json()
        new_tier = data.get("required_tier")
        
        if not new_tier or new_tier not in TIER_HIERARCHY:
            return jsonify({
                "status": "error",
                "message": f"Invalid tier. Must be one of: {', '.join(TIER_HIERARCHY)}"
            }), 400
        
        # Find the feature
        feature_enum = None
        for f in Feature:
            if f.value == feature_name:
                feature_enum = f
                break
        
        if not feature_enum:
            return jsonify({
                "status": "error",
                "message": f"Feature '{feature_name}' not found"
            }), 404
        
        old_tier = FEATURE_TIER_MAP.get(feature_enum)
        
        # Update the feature tier mapping (in-memory)
        FEATURE_TIER_MAP[feature_enum] = new_tier
        
        # Log the change
        current_user = get_current_user_from_request()
        audit.log_audit_event(
            user_id=current_user.id if current_user else None,
            action='feature_tier_changed',
            details=f"Changed feature '{feature_name}' tier from '{old_tier}' to '{new_tier}'",
            success=True,
            resource=f'/api/v1/admin/features/{feature_name}/tier',
            metadata={
                "feature": feature_name,
                "old_tier": old_tier,
                "new_tier": new_tier
            }
        )
        
        return jsonify({
            "status": "success",
            "feature": feature_name,
            "old_tier": old_tier,
            "new_tier": new_tier,
            "message": "Feature tier updated successfully"
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to update feature tier: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@admin_api_bp.route("/v1/admin/features/reset", methods=["POST"])
@require_admin
async def reset_feature_tiers():
    """
    Reset all feature tiers to their default values.
    
    Returns:
    {
        "status": "success",
        "message": "Feature tiers reset to defaults",
        "reset_count": 66
    }
    """
    try:
        from trusted_data_agent.auth.features import Feature, FEATURE_TIER_MAP, get_default_feature_tier_map
        
        # Get default mappings
        default_map = get_default_feature_tier_map()
        
        # Reset all features
        reset_count = 0
        for feature, default_tier in default_map.items():
            if FEATURE_TIER_MAP.get(feature) != default_tier:
                FEATURE_TIER_MAP[feature] = default_tier
                reset_count += 1
        
        # Log the reset
        current_user = get_current_user_from_request()
        audit.log_audit_event(
            user_id=current_user.id if current_user else None,
            action='features_reset',
            details=f"Reset all feature tiers to defaults ({reset_count} changes)",
            success=True,
            resource='/api/v1/admin/features/reset',
            metadata={"reset_count": reset_count}
        )
        
        return jsonify({
            "status": "success",
            "message": "Feature tiers reset to defaults",
            "reset_count": reset_count
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to reset feature tiers: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


# ==============================================================================
# PANE VISIBILITY MANAGEMENT
# ==============================================================================

@admin_api_bp.route('/v1/admin/panes', methods=['GET'])
@require_admin
async def get_panes():
    """
    Get all pane visibility configurations.
    
    Returns list of panes with tier visibility settings.
    
    Example Response:
    {
        "status": "success",
        "panes": [
            {
                "id": "uuid",
                "pane_id": "conversation",
                "pane_name": "Conversations",
                "visible_to_user": true,
                "visible_to_developer": true,
                "visible_to_admin": true,
                "description": "Chat interface for conversations",
                "display_order": 1
            },
            ...
        ]
    }
    """
    try:
        from trusted_data_agent.auth.models import PaneVisibility
        
        with get_db_session() as session:
            # Get all pane configurations
            panes = session.query(PaneVisibility).order_by(PaneVisibility.display_order).all()
            
            # If no panes exist, initialize with defaults
            if not panes:
                panes = initialize_default_panes(session)
            
            panes_data = [pane.to_dict() for pane in panes]
        
        return jsonify({
            "status": "success",
            "panes": panes_data
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get panes: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@admin_api_bp.route('/v1/admin/panes/<pane_id>/visibility', methods=['PATCH'])
@require_admin
async def update_pane_visibility(pane_id: str):
    """
    Update visibility settings for a specific pane.
    
    Request Body:
    {
        "visible_to_user": true,
        "visible_to_developer": true,
        "visible_to_admin": true
    }
    
    Returns updated pane configuration.
    """
    try:
        from trusted_data_agent.auth.models import PaneVisibility
        
        data = await request.get_json()
        
        with get_db_session() as session:
            # Get pane
            pane = session.query(PaneVisibility).filter_by(pane_id=pane_id).first()
            if not pane:
                return jsonify({
                    "status": "error",
                    "message": f"Pane '{pane_id}' not found"
                }), 404
            
            # Update visibility flags
            if 'visible_to_user' in data:
                pane.visible_to_user = bool(data['visible_to_user'])
            if 'visible_to_developer' in data:
                pane.visible_to_developer = bool(data['visible_to_developer'])
            if 'visible_to_admin' in data:
                pane.visible_to_admin = bool(data['visible_to_admin'])
            
            # Admin pane must always be visible to admins
            if pane_id == 'admin':
                pane.visible_to_admin = True
            
            pane_dict = pane.to_dict()
        
        # Log the change
        current_user = get_current_user_from_request()
        audit.log_audit_event(
            user_id=current_user.id if current_user else None,
            action='pane_visibility_updated',
            details=f"Updated visibility for pane '{pane_id}'",
            success=True,
            resource=f'/api/v1/admin/panes/{pane_id}/visibility',
            metadata=pane_dict
        )
        
        return jsonify({
            "status": "success",
            "pane": pane_dict
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to update pane visibility: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@admin_api_bp.route('/v1/admin/panes/reset', methods=['POST'])
@require_admin
async def reset_panes():
    """
    Reset all pane visibility settings to defaults.
    
    Default Configuration:
    - admin: admin only
    - developer: developer + admin
    - user: all tiers
    
    Returns:
    {
        "status": "success",
        "message": "Pane visibility reset to defaults",
        "panes": [...]
    }
    """
    try:
        from trusted_data_agent.auth.models import PaneVisibility
        
        with get_db_session() as session:
            # Delete all existing panes
            session.query(PaneVisibility).delete()
            session.commit()
            
            # Recreate with defaults
            panes = initialize_default_panes(session)
            panes_data = [pane.to_dict() for pane in panes]
        
        # Log the reset
        current_user = get_current_user_from_request()
        audit.log_audit_event(
            user_id=current_user.id if current_user else None,
            action='panes_reset',
            details="Reset all pane visibility to defaults",
            success=True,
            resource='/api/v1/admin/panes/reset'
        )
        
        return jsonify({
            "status": "success",
            "message": "Pane visibility reset to defaults",
            "panes": panes_data
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to reset panes: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


def initialize_default_panes(session):
    """
    Initialize pane visibility with default configuration.
    
    Default Configuration:
    - Conversations: all tiers
    - Marketplace: all tiers
    - Credentials: all tiers
    - Executions: developer + admin
    - RAG Maintenance: developer + admin
    - Administration: admin only
    
    Args:
        session: SQLAlchemy session
        
    Returns:
        List of created PaneVisibility objects
    """
    from trusted_data_agent.auth.models import PaneVisibility
    
    default_panes = [
        {
            'pane_id': 'conversation',
            'pane_name': 'Conversations',
            'description': 'Chat interface for conversations',
            'display_order': 1,
            'visible_to_user': True,
            'visible_to_developer': True,
            'visible_to_admin': True
        },
        {
            'pane_id': 'executions',
            'pane_name': 'Executions',
            'description': 'Execution dashboard and history',
            'display_order': 2,
            'visible_to_user': False,
            'visible_to_developer': True,
            'visible_to_admin': True
        },
        {
            'pane_id': 'rag-maintenance',
            'pane_name': 'RAG Maintenance',
            'description': 'Manage RAG collections and templates',
            'display_order': 3,
            'visible_to_user': False,
            'visible_to_developer': True,
            'visible_to_admin': True
        },
        {
            'pane_id': 'marketplace',
            'pane_name': 'Marketplace',
            'description': 'Browse and install RAG templates',
            'display_order': 4,
            'visible_to_user': True,
            'visible_to_developer': True,
            'visible_to_admin': True
        },
        {
            'pane_id': 'credentials',
            'pane_name': 'Credentials',
            'description': 'Configure LLM and MCP credentials',
            'display_order': 5,
            'visible_to_user': True,
            'visible_to_developer': True,
            'visible_to_admin': True
        },
        {
            'pane_id': 'admin',
            'pane_name': 'Administration',
            'description': 'User and system administration',
            'display_order': 6,
            'visible_to_user': False,
            'visible_to_developer': False,
            'visible_to_admin': True
        }
    ]
    
    panes = []
    for pane_data in default_panes:
        pane = PaneVisibility(**pane_data)
        session.add(pane)
        panes.append(pane)
    
    session.commit()
    
    return panes
