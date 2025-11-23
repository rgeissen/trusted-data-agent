# Phase 4 Quick Reference

## Credential Management

### Store Credentials
```python
from trusted_data_agent.core import configuration_service

result = await configuration_service.store_credentials_for_provider(
    user_id="user-uuid-123",
    provider="Amazon",
    credentials={
        "aws_access_key_id": "AKIA...",
        "aws_secret_access_key": "...",
        "aws_region": "us-west-2"
    }
)
# Returns: {"status": "success", "message": "Credentials stored securely for Amazon"}
```

### Retrieve Credentials
```python
result = await configuration_service.retrieve_credentials_for_provider(
    user_id="user-uuid-123",
    provider="Amazon"
)
# Returns: {"status": "success", "credentials": {...}}
```

### Delete Credentials
```python
result = await configuration_service.delete_credentials_for_provider(
    user_id="user-uuid-123",
    provider="Amazon"
)
# Returns: {"status": "success", "message": "Credentials deleted for Amazon"}
```

### List Providers
```python
result = await configuration_service.list_user_providers(user_id="user-uuid-123")
# Returns: {"status": "success", "providers": ["Amazon", "Google"]}
```

---

## Admin Permissions

### Protect Admin Route
```python
from quart import Blueprint
from trusted_data_agent.auth.admin import require_admin

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/api/v1/admin/sensitive-action', methods=['POST'])
@require_admin
async def sensitive_action():
    """Only admins can access this."""
    return jsonify({"status": "success"})
```

### Check Admin Status
```python
from trusted_data_agent.auth.admin import is_admin, get_current_user_from_request

user = get_current_user_from_request()
if is_admin(user):
    # User has admin privileges
    pass
```

### Validate User Management Permissions
```python
from trusted_data_agent.auth.admin import can_manage_user

admin_user = get_current_user_from_request()
if can_manage_user(admin_user, target_user_id):
    # Admin can manage this user
    # (Prevents self-modification)
    pass
```

---

## Audit Logging

### Get User Audit Logs
```python
from trusted_data_agent.auth import audit

logs = audit.get_user_audit_logs(
    user_id="user-uuid-123",
    limit=50,
    offset=0,
    action_filter="credential_change"  # Optional
)
# Returns: List of audit log dictionaries
```

### Log Admin Action
```python
audit.log_admin_action(
    admin_user_id="admin-uuid",
    action="user_update",
    target_user_id="user-uuid",
    details="Changed user role to admin"
)
```

### Log Credential Operation
```python
audit.log_credential_change(
    user_id="user-uuid",
    provider="Amazon",
    action="stored"  # or "deleted", "updated"
)
```

---

## API Endpoints Quick Reference

### Credential Management (All Users)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/credentials` | List providers with stored credentials |
| GET | `/api/v1/credentials/<provider>` | Check if credentials exist |
| POST | `/api/v1/credentials/<provider>` | Store credentials |
| DELETE | `/api/v1/credentials/<provider>` | Delete credentials |
| POST | `/api/v1/credentials/<provider>/test` | Test credentials |

### Audit Logs (All Users)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/auth/me/audit-logs` | Get own audit logs |

### User Management (Admin Only)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/users` | List all users |
| GET | `/api/v1/admin/users/<id>` | Get user details |
| PATCH | `/api/v1/admin/users/<id>` | Update user |
| DELETE | `/api/v1/admin/users/<id>` | Deactivate user |
| POST | `/api/v1/admin/users/<id>/unlock` | Unlock account |
| GET | `/api/v1/admin/stats` | System statistics |

---

## Environment Variables

```bash
# Required for Phase 4
TDA_AUTH_ENABLED=true
TDA_ENCRYPTION_KEY=<generate-secure-key>

# Recommended
TDA_RATE_LIMIT_ENABLED=true
TDA_AUDIT_LOGGING_ENABLED=true
```

### Generate Secure Encryption Key
```python
import secrets
print(secrets.token_urlsafe(32))
```

---

## Database Schema

### user_credentials
```sql
CREATE TABLE user_credentials (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    credentials_encrypted TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE (user_id, provider)
);
```

### audit_logs
```sql
CREATE TABLE audit_logs (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36),
    action VARCHAR(100) NOT NULL,
    resource VARCHAR(255),
    status VARCHAR(20) NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    details TEXT,
    metadata TEXT,
    timestamp TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

---

## Common Patterns

### Check if Credentials Exist Before Storing
```python
# In your route handler
providers_result = await configuration_service.list_user_providers(user_uuid)

if "Amazon" in providers_result.get("providers", []):
    # Credentials already exist - prompt user to update or delete first
    return jsonify({
        "status": "error",
        "message": "Credentials already exist. Delete first or use PATCH to update."
    }), 409
```

### Auto-Load Credentials in Configuration Flow
```python
async def configure_with_stored_credentials(user_uuid, provider, use_stored=True):
    """Configure service using stored credentials if available."""
    
    if use_stored:
        # Try to load stored credentials
        result = await configuration_service.retrieve_credentials_for_provider(
            user_uuid,
            provider
        )
        
        if result.get("credentials"):
            # Use stored credentials
            config_data = {
                "provider": provider,
                "credentials": result["credentials"],
                # ... other config
            }
            return await configuration_service.setup_and_categorize_services(config_data)
    
    # Fall back to manual credential input
    return {"status": "error", "message": "No stored credentials found"}
```

### Admin Dashboard Data Aggregation
```python
from trusted_data_agent.auth.database import get_db_session
from trusted_data_agent.auth.models import User
from datetime import datetime, timezone, timedelta

async def get_dashboard_data():
    """Aggregate data for admin dashboard."""
    with get_db_session() as session:
        now = datetime.now(timezone.utc)
        
        # User stats
        total = session.query(User).count()
        active = session.query(User).filter_by(is_active=True).count()
        
        # Recent activity
        day_ago = now - timedelta(days=1)
        recent_logins = session.query(User).filter(
            User.last_login_at >= day_ago
        ).count()
        
        return {
            "total_users": total,
            "active_users": active,
            "recent_logins_24h": recent_logins
        }
```

---

## Security Best Practices

1. **Always use HTTPS in production**
   - Credentials are encrypted at rest but transmitted over HTTP during API calls
   
2. **Rotate encryption key periodically**
   ```python
   from trusted_data_agent.auth import encryption
   encryption.rotate_encryption_key(old_key, new_key)
   ```

3. **Monitor admin actions**
   - Set up alerts for `admin_*` audit events
   - Review admin audit logs regularly

4. **Rate limit admin endpoints**
   ```python
   from trusted_data_agent.auth.rate_limiter import rate_limit
   
   @admin_bp.route('/api/v1/admin/users/<id>', methods=['PATCH'])
   @require_admin
   @rate_limit(limit=10, window=60)  # 10 updates per minute
   async def update_user(id):
       pass
   ```

5. **Validate credential test results**
   - Always test stored credentials before using in production
   - Handle expired/invalid credentials gracefully

---

## Troubleshooting

### "Credential encryption not available"
**Cause:** `TDA_AUTH_ENABLED=false` or auth module import failed  
**Fix:** Set `TDA_AUTH_ENABLED=true` and ensure auth dependencies installed

### "ENCRYPTION_KEY not set" warning
**Cause:** Missing `TDA_ENCRYPTION_KEY` environment variable  
**Fix:** Generate and set secure key:
```bash
export TDA_ENCRYPTION_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
```

### "Foreign key constraint failed"
**Cause:** Trying to store credentials for non-existent user  
**Fix:** Ensure user exists in database before storing credentials

### "Admin privileges required" (403)
**Cause:** Non-admin user accessing admin endpoint  
**Fix:** Ensure user has `is_admin=True` in database

### Credentials not loading in configuration
**Cause:** Auto-load feature not yet implemented in frontend  
**Fix:** Manually pass stored credentials or implement auto-load logic

---

## Testing Checklist

- [ ] Store credentials for each provider (Amazon, Google, Anthropic, etc.)
- [ ] Retrieve credentials successfully
- [ ] Delete credentials
- [ ] Test credential validation
- [ ] Non-admin cannot access admin endpoints (403)
- [ ] Admin can list users
- [ ] Admin can update user status
- [ ] Admin cannot modify own admin status
- [ ] Admin can unlock accounts
- [ ] All operations logged to audit table
- [ ] User can view own audit logs
- [ ] Credentials encrypted in database
- [ ] Different users have isolated credentials
