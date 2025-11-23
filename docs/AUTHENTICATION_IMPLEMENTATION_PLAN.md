# Authentication & Multi-User System - Implementation Plan

## Overview
Transform TDA from single-user to production-ready multi-user platform with authentication, authorization, and security.

**Estimated Time:** 6-8 days  
**Phases:** 4 phases (can be implemented incrementally)

---

## Phase 1: Core Authentication Infrastructure (Day 1-2)

### 1.1 User Database Schema
**File:** `src/trusted_data_agent/auth/database.py`

```python
# User table structure
users:
  - id (UUID, primary key)
  - username (string, unique, indexed)
  - email (string, unique, indexed)
  - password_hash (string, bcrypt)
  - full_name (string, optional)
  - created_at (timestamp)
  - updated_at (timestamp)
  - last_login_at (timestamp)
  - is_active (boolean, default: true)
  - is_admin (boolean, default: false)
  - failed_login_attempts (int, default: 0)
  - locked_until (timestamp, nullable)

# Session tokens table
auth_tokens:
  - id (UUID, primary key)
  - user_id (UUID, foreign key -> users)
  - token_hash (string, indexed)
  - expires_at (timestamp)
  - created_at (timestamp)
  - ip_address (string)
  - user_agent (string)
  - revoked (boolean, default: false)
```

**Implementation:**
- Use SQLite for development, PostgreSQL-compatible
- SQLAlchemy ORM for database abstraction
- Alembic for migrations

**Files to create:**
```
src/trusted_data_agent/auth/
├── __init__.py
├── database.py          # Database models and connection
├── models.py            # User, AuthToken models (SQLAlchemy)
└── migrations/          # Alembic migration scripts
    └── versions/
```

### 1.2 Password Hashing & Token Management
**File:** `src/trusted_data_agent/auth/security.py`

```python
Functions to implement:
- hash_password(password: str) -> str
  # Use bcrypt with salt rounds=12
  
- verify_password(password: str, password_hash: str) -> bool
  # Constant-time comparison
  
- generate_auth_token(user_id: str) -> str
  # JWT with 24-hour expiry, HS256 algorithm
  # Payload: {user_id, username, exp, iat, jti}
  
- verify_auth_token(token: str) -> dict | None
  # Validate JWT, check expiry, return payload
  
- revoke_token(token: str) -> bool
  # Mark token as revoked in database
  
- cleanup_expired_tokens() -> int
  # Remove expired tokens (scheduled task)
```

**Dependencies to add:**
```bash
pip install bcrypt pyjwt python-dotenv
```

**Environment variables:**
```bash
# Add to .env or environment
TDA_JWT_SECRET_KEY=<generate-random-256-bit-key>
TDA_JWT_EXPIRY_HOURS=24
TDA_PASSWORD_MIN_LENGTH=8
TDA_MAX_LOGIN_ATTEMPTS=5
TDA_LOCKOUT_DURATION_MINUTES=15
```

### 1.3 Authentication Endpoints
**File:** `src/trusted_data_agent/api/auth_routes.py`

```python
Endpoints to implement:

POST /api/v1/auth/register
  Body: {username, email, password, full_name?}
  Returns: {user_id, username, email, message}
  
POST /api/v1/auth/login
  Body: {username, password}
  Returns: {token, user_id, username, expires_at}
  
POST /api/v1/auth/logout
  Headers: Authorization: Bearer <token>
  Returns: {message}
  
GET /api/v1/auth/me
  Headers: Authorization: Bearer <token>
  Returns: {user_id, username, email, full_name, created_at}
  
POST /api/v1/auth/refresh
  Headers: Authorization: Bearer <token>
  Returns: {token, expires_at}
  
POST /api/v1/auth/change-password
  Headers: Authorization: Bearer <token>
  Body: {old_password, new_password}
  Returns: {message}
```

**Rate limiting:**
```python
# Apply to login/register endpoints
- 5 attempts per minute per IP
- 20 attempts per hour per IP
```

### 1.4 Authentication Middleware
**File:** `src/trusted_data_agent/auth/middleware.py`

```python
@require_auth decorator:
  - Extract token from Authorization header
  - Verify token validity
  - Load user from database
  - Inject user_id into request context
  - Handle errors (401 Unauthorized)

@require_admin decorator:
  - Extends @require_auth
  - Check is_admin flag
  - Return 403 Forbidden if not admin

Optional decorators:
@optional_auth - Proceed with or without auth
@rate_limit(requests=10, window=60) - Rate limiting
```

**Integration points:**
```python
# Update existing endpoints
routes.py: Add @require_auth to:
  - /api/configure
  - /api/prompt-executor
  - /api/sessions
  - /api/new-session
  
rest_routes.py: Add @require_auth to:
  - /api/v1/configure
  - /api/v1/execute-prompt
  - /api/v1/sessions
```

---

## Phase 2: UI Integration (Day 3)

### 2.1 Login/Register Pages
**Files to create:**
```
templates/
├── login.html           # Login form
├── register.html        # Registration form
└── profile.html         # User profile page

static/js/
└── auth.js             # Authentication client
```

**login.html:**
```html
Features:
- Username/password form
- "Remember me" checkbox
- "Forgot password" link (Phase 3)
- "Register" link
- Error message display
- Auto-redirect after login
```

**register.html:**
```html
Features:
- Username, email, password fields
- Password confirmation
- Password strength indicator
- Terms acceptance checkbox
- Validation messages
```

### 2.2 Authentication JavaScript Client
**File:** `static/js/auth.js`

```javascript
Functions to implement:

async login(username, password, remember)
  - POST to /api/v1/auth/login
  - Store token in localStorage/sessionStorage
  - Redirect to main page
  
async register(username, email, password, fullName)
  - POST to /api/v1/auth/register
  - Auto-login after registration
  
async logout()
  - POST to /api/v1/auth/logout
  - Clear token from storage
  - Redirect to login page
  
async getCurrentUser()
  - GET /api/v1/auth/me
  - Return user info or null
  
getAuthToken()
  - Retrieve token from storage
  
isAuthenticated()
  - Check if valid token exists
  
async refreshToken()
  - POST to /api/v1/auth/refresh
  - Update stored token
```

### 2.3 Update API Client
**File:** `static/js/api.js`

```javascript
Changes needed:

1. Add token to all requests:
   headers: {
     'Authorization': `Bearer ${getAuthToken()}`,
     'Content-Type': 'application/json'
   }

2. Handle 401 responses:
   - Try token refresh once
   - Redirect to login if refresh fails
   
3. Remove manual X-TDA-User-UUID header:
   - Server extracts user_id from token
```

### 2.4 Update Main UI
**File:** `static/js/main.js`

```javascript
On page load:
1. Check if authenticated
2. If not, redirect to /login
3. If yes, load user profile
4. Add logout button to navbar
5. Display username in header
```

**File:** `templates/index.html`

```html
Add to navbar:
- User dropdown menu:
  - Username display
  - Profile link
  - Settings link
  - Logout button
```

---

## Phase 3: Security Hardening (Day 4-5)

### 3.1 Per-User Credential Encryption
**File:** `src/trusted_data_agent/auth/encryption.py`

```python
Current problem:
- API keys stored in APP_CONFIG (shared)
- All users see same credentials

Solution:
- Encrypt credentials per user
- Store in user_credentials table

Table: user_credentials
  - id (UUID)
  - user_id (UUID, foreign key)
  - provider (string: Amazon, Google, etc.)
  - credentials_encrypted (text, AES-256)
  - created_at (timestamp)
  - updated_at (timestamp)

Functions:
- encrypt_credentials(user_id, provider, credentials_dict) -> str
- decrypt_credentials(user_id, provider) -> dict
- delete_credentials(user_id, provider) -> bool
```

**Encryption approach:**
```python
# Use Fernet (symmetric encryption)
from cryptography.fernet import Fernet

# Key derivation from master secret + user_id
# Store encrypted credentials in database
# Decrypt on-demand during LLM calls
```

### 3.2 Update Configuration Service
**File:** `src/trusted_data_agent/core/configuration_service.py`

```python
Changes:
1. Store credentials in user_credentials table
2. Don't store in APP_CONFIG (security risk)
3. Load credentials on-demand per request
4. Update setup_and_categorize_services():
   - Extract user_id from auth token
   - Load user's encrypted credentials
   - Create temporary LLM instance
   - Don't persist credentials in memory
```

### 3.3 Rate Limiting
**File:** `src/trusted_data_agent/auth/rate_limiter.py`

```python
Implement:
- Token bucket algorithm
- Per-user limits:
  - 100 prompts per hour
  - 1000 prompts per day
  - 10 configurations per hour
  
- Per-IP limits (anonymous):
  - 5 login attempts per minute
  - 3 registrations per hour

Storage:
- Use Redis if available, else in-memory dict
- Clean up expired entries periodically
```

### 3.4 Input Validation & Sanitization
**File:** `src/trusted_data_agent/auth/validators.py`

```python
Validators:
- validate_username(username: str) -> bool
  # 3-30 chars, alphanumeric + underscore
  
- validate_email(email: str) -> bool
  # RFC 5322 compliant
  
- validate_password(password: str) -> tuple[bool, list[str]]
  # Min 8 chars, complexity requirements
  # Return (valid, [error_messages])
  
- sanitize_user_input(text: str) -> str
  # Remove SQL injection attempts
  # Remove XSS attempts
```

### 3.5 Audit Logging
**File:** `src/trusted_data_agent/auth/audit.py`

```python
Table: audit_logs
  - id (UUID)
  - user_id (UUID, nullable for anonymous)
  - action (string: login, logout, configure, execute, etc.)
  - resource (string: endpoint path)
  - status (string: success, failure)
  - ip_address (string)
  - user_agent (string)
  - details (JSON, optional)
  - timestamp (timestamp)

Log events:
- Authentication attempts (success/failure)
- Configuration changes
- Prompt executions
- Session access
- API calls
- Admin actions
```

---

## Phase 4: Advanced Features (Day 6-8)

### 4.1 User Management API
**File:** `src/trusted_data_agent/api/admin_routes.py`

```python
Admin endpoints:

GET /api/v1/admin/users
  - List all users (paginated)
  - Requires @require_admin
  
GET /api/v1/admin/users/{user_id}
  - Get user details
  
PUT /api/v1/admin/users/{user_id}
  - Update user (activate/deactivate, make admin)
  
DELETE /api/v1/admin/users/{user_id}
  - Delete user and all data
  
GET /api/v1/admin/audit-logs
  - View audit logs (filterable)
  
GET /api/v1/admin/stats
  - System statistics (users, sessions, usage)
```

### 4.2 User Preferences
**File:** `src/trusted_data_agent/api/user_routes.py`

```python
Table: user_preferences
  - user_id (UUID, primary key)
  - theme (string: light, dark)
  - default_profile_id (UUID, nullable)
  - notification_enabled (boolean)
  - preferences_json (JSON for extensibility)
  
Endpoints:
GET /api/v1/user/preferences
PUT /api/v1/user/preferences
```

### 4.3 Usage Quotas
**File:** `src/trusted_data_agent/auth/quotas.py`

```python
Table: user_quotas
  - user_id (UUID)
  - quota_type (string: prompts, tokens, sessions)
  - limit_value (int)
  - period (string: hourly, daily, monthly)
  - current_usage (int)
  - reset_at (timestamp)

Functions:
- check_quota(user_id, quota_type) -> bool
- increment_usage(user_id, quota_type, amount)
- reset_quotas() # Scheduled task
```

### 4.4 Admin Dashboard UI
**Files to create:**
```
templates/admin/
├── dashboard.html      # Overview stats
├── users.html          # User management
├── audit.html          # Audit log viewer
└── settings.html       # System settings

static/js/admin/
├── dashboard.js
├── userManagement.js
└── auditViewer.js
```

### 4.5 Password Reset Flow
**Files:** 
- `src/trusted_data_agent/auth/password_reset.py`
- `templates/forgot_password.html`
- `templates/reset_password.html`

```python
Table: password_reset_tokens
  - id (UUID)
  - user_id (UUID)
  - token_hash (string)
  - expires_at (timestamp, 1 hour)
  - used (boolean)

Flow:
1. User requests reset (email/username)
2. Generate reset token, send email
3. User clicks link with token
4. Validate token, show reset form
5. Update password, invalidate token
```

---

## Implementation Order (Recommended)

### Week 1: Core Authentication
```
Day 1: Database & Models
  ✓ Create auth module structure
  ✓ Define User and AuthToken models
  ✓ Set up SQLite database
  ✓ Create initial migration
  
Day 2: Security & Endpoints
  ✓ Implement password hashing
  ✓ Implement JWT token generation
  ✓ Create auth endpoints (register, login, logout)
  ✓ Add authentication middleware
  
Day 3: UI Integration
  ✓ Create login/register pages
  ✓ Implement auth.js client
  ✓ Update main UI with authentication
  ✓ Add logout functionality
  
Day 4: Security Hardening
  ✓ Implement credential encryption
  ✓ Add rate limiting
  ✓ Input validation
  ✓ Audit logging
  
Day 5: Testing & Polish
  ✓ Write authentication tests
  ✓ Test multi-user scenarios
  ✓ Fix bugs and edge cases
  ✓ Documentation
```

### Week 2: Advanced Features (Optional)
```
Day 6-7: Admin Features
  ✓ User management API
  ✓ Admin dashboard UI
  ✓ Usage quotas
  
Day 8: Password Reset & Polish
  ✓ Password reset flow
  ✓ Email notifications
  ✓ Final testing
```

---

## Database Migration Strategy

### Initial Setup
```bash
# Create auth database
python -m trusted_data_agent.auth.database init

# Run migrations
python -m trusted_data_agent.auth.database migrate
```

### Backwards Compatibility
```python
# Support both authenticated and legacy modes
if os.environ.get('TDA_AUTH_ENABLED', 'false') == 'true':
    # Use authentication
    require_auth_middleware()
else:
    # Legacy mode: use X-TDA-User-UUID header
    legacy_user_middleware()
```

---

## Configuration Changes

### New Environment Variables
```bash
# Authentication
TDA_AUTH_ENABLED=true                    # Enable authentication
TDA_JWT_SECRET_KEY=<256-bit-random-key>  # JWT signing key
TDA_JWT_EXPIRY_HOURS=24                  # Token expiry
TDA_PASSWORD_MIN_LENGTH=8                # Min password length
TDA_MAX_LOGIN_ATTEMPTS=5                 # Lockout threshold
TDA_LOCKOUT_DURATION_MINUTES=15          # Lockout duration

# Database
TDA_AUTH_DB_URL=sqlite:///./tda_auth.db  # Auth database URL
# For production: postgresql://user:pass@host/dbname

# Security
TDA_ENCRYPTION_KEY=<256-bit-random-key>  # Credential encryption key
TDA_RATE_LIMIT_ENABLED=true              # Enable rate limiting
TDA_AUDIT_LOGGING_ENABLED=true           # Enable audit logs

# Email (for password reset - Phase 4)
TDA_EMAIL_ENABLED=false                  # Enable email
TDA_SMTP_HOST=smtp.gmail.com
TDA_SMTP_PORT=587
TDA_SMTP_USER=your-email@gmail.com
TDA_SMTP_PASSWORD=your-app-password
```

### Update requirements.txt
```txt
# Add new dependencies
bcrypt>=4.1.0
pyjwt>=2.8.0
sqlalchemy>=2.0.0
alembic>=1.12.0
python-dotenv>=1.0.0
cryptography>=41.0.0
email-validator>=2.1.0

# Optional (for production)
redis>=5.0.0                    # Rate limiting
psycopg2-binary>=2.9.0          # PostgreSQL
gunicorn>=21.2.0                # Production server
```

---

## Testing Strategy

### Unit Tests
```bash
test/auth/
├── test_password_hashing.py
├── test_token_generation.py
├── test_user_registration.py
├── test_authentication.py
├── test_rate_limiting.py
└── test_encryption.py
```

### Integration Tests
```bash
test/integration/
├── test_auth_flow.py           # Full login/logout flow
├── test_multi_user.py          # Multiple users simultaneously
├── test_credential_isolation.py # User A can't see User B's creds
└── test_rate_limits.py         # Verify rate limiting works
```

### Security Tests
```bash
test/security/
├── test_sql_injection.py       # SQL injection attempts
├── test_xss.py                 # XSS attempts
├── test_token_tampering.py     # JWT tampering
└── test_brute_force.py         # Login brute force
```

---

## Rollout Plan

### Stage 1: Development Testing
```bash
# Run with authentication in dev mode
export TDA_AUTH_ENABLED=true
export TDA_CONFIGURATION_PERSISTENCE=false
python -m trusted_data_agent.main
```

### Stage 2: Beta Testing
```bash
# Enable for selected users
# Run in parallel with legacy mode
# Collect feedback
```

### Stage 3: Production Migration
```bash
# Migrate existing users:
1. Export user data from tda_sessions/
2. Create user accounts (assign UUIDs)
3. Migrate credentials to encrypted storage
4. Enable authentication globally
5. Deprecate legacy mode
```

---

## Success Metrics

✅ **Phase 1 Complete When:**
- Users can register and login
- JWT tokens are generated and validated
- Protected endpoints require authentication
- Existing multi-user isolation works with auth

✅ **Phase 2 Complete When:**
- Login/register UI fully functional
- Users can login and use all features
- Logout works correctly
- UI shows current user

✅ **Phase 3 Complete When:**
- Credentials are encrypted per user
- Rate limiting prevents abuse
- All inputs are validated
- Audit logs capture all actions

✅ **Phase 4 Complete When:**
- Admin can manage users
- Usage quotas prevent overuse
- Password reset flow works
- Production-ready deployment

---

## Risk Mitigation

### Backwards Compatibility
```python
# Keep legacy mode during transition
if not TDA_AUTH_ENABLED:
    # Old behavior: trust X-TDA-User-UUID header
    user_uuid = request.headers.get('X-TDA-User-UUID')
else:
    # New behavior: require authentication
    user_uuid = get_authenticated_user_id()
```

### Data Migration
```python
# Script to migrate existing users
def migrate_existing_users():
    # Read tda_sessions/* directories
    # Create user accounts for each UUID
    # Assign temporary passwords
    # Send password reset emails
```

### Fallback Plan
```python
# If auth has issues, can disable quickly
export TDA_AUTH_ENABLED=false
# System reverts to legacy mode
```

---

## Next Steps

**To start implementation:**

1. **Review this plan** - Adjust based on your requirements
2. **Set up development branch** - `git checkout -b feature/authentication`
3. **Start with Phase 1, Day 1** - Create database models
4. **Incremental commits** - Small, testable changes
5. **Test thoroughly** - Each phase before moving to next

**First command to run:**
```bash
# Create auth module structure
mkdir -p src/trusted_data_agent/auth
touch src/trusted_data_agent/auth/__init__.py
touch src/trusted_data_agent/auth/models.py
```

Ready to start? We'll begin with Phase 1: Database & Models! 🚀
