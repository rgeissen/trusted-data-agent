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

@admin_api_bp.route("/v1/admin/users", methods=["GET"])
@require_admin
async def list_users():
    """
    List all users (admin only).
    
    Query params:
    - limit: Number of records (default 50)
    - offset: Skip records (default 0)
    - search: Search by username or email
    - active_only: Filter active users (default false)
    
    Returns:
    {
        "status": "success",
        "users": [...],
        "total": 25
    }
    """
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
            
            user_list = []
            for user in users:
                user_list.append({
                    'id': user.id,
                    'user_uuid': user.user_uuid,
                    'username': user.username,
                    'email': user.email,
                    'display_name': user.display_name,
                    'is_active': user.is_active,
                    'is_admin': user.is_admin,
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
                    changes.append(f"is_admin={user.is_admin}")
                
                if 'display_name' in data:
                    user.display_name = data['display_name']
                    changes.append(f"display_name={user.display_name}")
                
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
            
            return jsonify({
                "status": "success",
                "stats": {
                    "total_users": total_users,
                    "active_users": active_users,
                    "admin_users": admin_users,
                    "locked_users": locked_users,
                    "recent_logins_24h": recent_logins,
                    "recent_registrations_7d": recent_registrations,
                    "recent_audit_events_24h": recent_audits
                }
            }), 200
            
    except Exception as e:
        logger.error(f"Failed to get stats: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500
