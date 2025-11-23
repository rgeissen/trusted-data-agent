# Pane Visibility Configuration

## Overview

The Trusted Data Agent now supports **tier-based pane visibility control**, allowing administrators to configure which user tiers can access different panes (views) in the application. This feature provides fine-grained access control beyond the existing feature-tier system.

## How It Works

### Three-Tier System
- **User Tier**: Basic access with limited panes
- **Developer Tier**: Advanced access with development tools
- **Admin Tier**: Full system access including administration

### Default Configuration

| Pane | User | Developer | Admin | Description |
|------|------|-----------|-------|-------------|
| Conversations | ✅ | ✅ | ✅ | Chat interface for conversations |
| Executions | ❌ | ✅ | ✅ | Execution dashboard and history |
| RAG Maintenance | ❌ | ✅ | ✅ | Manage RAG collections and templates |
| Marketplace | ✅ | ✅ | ✅ | Browse and install RAG templates |
| Credentials | ✅ | ✅ | ✅ | Configure LLM and MCP credentials |
| Administration | ❌ | ❌ | ✅ | User and system administration |

## Configuration

### Admin Interface

1. **Access Admin Panel**
   - Log in as an admin user
   - Click "Administration" in the sidebar
   - Navigate to the "Pane Configuration" tab

2. **Toggle Pane Visibility**
   - Each pane has three toggle switches (User, Developer, Admin)
   - Changes are saved immediately when toggled
   - Protected panes (like Administration) cannot be disabled for admins

3. **Reset to Defaults**
   - Click "Reset to Defaults" to restore the original configuration
   - Confirmation dialog prevents accidental resets

### API Endpoints

#### Get All Panes
```http
GET /api/v1/admin/panes
Authorization: Bearer <admin_token>
```

**Response:**
```json
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
```

#### Update Pane Visibility
```http
PATCH /api/v1/admin/panes/<pane_id>/visibility
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "visible_to_user": true,
  "visible_to_developer": true,
  "visible_to_admin": true
}
```

#### Reset to Defaults
```http
POST /api/v1/admin/panes/reset
Authorization: Bearer <admin_token>
```

## Database Schema

### PaneVisibility Table

```sql
CREATE TABLE pane_visibility (
    id VARCHAR(36) PRIMARY KEY,
    pane_id VARCHAR(50) UNIQUE NOT NULL,
    pane_name VARCHAR(100) NOT NULL,
    visible_to_user BOOLEAN NOT NULL DEFAULT TRUE,
    visible_to_developer BOOLEAN NOT NULL DEFAULT TRUE,
    visible_to_admin BOOLEAN NOT NULL DEFAULT TRUE,
    description VARCHAR(255),
    display_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

## User Experience

### For Users (User Tier)
- See only panes they have access to
- Cannot access Executions or RAG Maintenance by default
- Can use Conversations, Marketplace, and Credentials

### For Developers (Developer Tier)
- Access to all user panes plus developer tools
- Can access Executions and RAG Maintenance
- Cannot access Administration

### For Admins (Admin Tier)
- Full access to all panes
- Can configure pane visibility for other tiers
- Administration pane is always visible (protected)

## Security Considerations

### ✅ Advantages
- **Granular Access Control**: Control exactly what users can see
- **Reduced Cognitive Load**: Users only see relevant panes
- **Secure by Default**: New users start with minimal access
- **Flexible Configuration**: Admins can adjust based on needs

### 🔒 Protected Panes
- **Administration**: Always visible to admins only
- Cannot be disabled for admin tier
- Prevents accidental lockout

### 🔐 Backend Enforcement
- Pane visibility is enforced on the frontend (UI hiding)
- Backend API endpoints still require proper authentication
- Feature-tier system provides additional backend protection

## Implementation Details

### Frontend Components

1. **Pane Visibility Cache** (`templates/index.html`)
   ```javascript
   let paneVisibilityCache = null;
   
   async function updatePaneVisibility(userTier) {
       // Fetches configuration from API
       // Applies visibility to DOM elements
   }
   ```

2. **Admin Management** (`static/js/adminManager.js`)
   ```javascript
   AdminManager.loadPanes()        // Load configuration
   AdminManager.renderPanes()      // Render UI table
   AdminManager.updatePaneVisibility() // Update single pane
   AdminManager.resetPanes()       // Reset to defaults
   ```

3. **Admin UI Tab** (`templates/index.html`)
   - Third tab in Admin panel
   - Toggle switches for each tier
   - Real-time updates

### Backend Components

1. **Database Model** (`auth/models.py`)
   - `PaneVisibility` SQLAlchemy model
   - Tier visibility flags
   - Display order and metadata

2. **API Routes** (`api/admin_routes.py`)
   - `GET /api/v1/admin/panes`
   - `PATCH /api/v1/admin/panes/<pane_id>/visibility`
   - `POST /api/v1/admin/panes/reset`

3. **Initialization** (`api/admin_routes.py`)
   - `initialize_default_panes()` function
   - Auto-creates defaults on first access
   - Idempotent (safe to call multiple times)

## Migration

### Initial Setup

Run the migration script to create the table and seed defaults:

```bash
python maintenance/migrate_pane_visibility.py
```

The script:
1. Creates the `pane_visibility` table
2. Seeds default configuration
3. Can be run multiple times safely
4. Prompts before overwriting existing configuration

### Manual Database Setup

If needed, you can manually initialize:

```python
from trusted_data_agent.auth.database import init_database
from trusted_data_agent.api.admin_routes import initialize_default_panes

# Create tables
init_database()

# Seed panes
from trusted_data_agent.auth.database import get_db_session
with get_db_session() as session:
    initialize_default_panes(session)
```

## Testing

### Test Pane Visibility for User Tier

1. Log in as a user with `profile_tier='user'`
2. Verify you can see:
   - Conversations
   - Marketplace
   - Credentials
3. Verify you cannot see:
   - Executions
   - RAG Maintenance
   - Administration

### Test Pane Visibility for Developer Tier

1. Log in as a user with `profile_tier='developer'`
2. Verify you can see:
   - All user panes plus
   - Executions
   - RAG Maintenance
3. Verify you cannot see:
   - Administration

### Test Pane Visibility for Admin Tier

1. Log in as a user with `profile_tier='admin'`
2. Verify you can see all panes including Administration

### Test Configuration Changes

1. Log in as admin
2. Navigate to Admin → Pane Configuration
3. Toggle a pane visibility for "User" tier
4. Log out and log in as a user
5. Verify the pane visibility changed
6. Changes are applied immediately (no restart needed)

## Troubleshooting

### Problem: Panes Not Hiding After Configuration Change

**Solution:**
1. Hard refresh browser: `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac)
2. Check browser console for errors
3. Verify `/api/v1/admin/panes` returns updated configuration
4. Clear browser cache if needed

### Problem: Admin Cannot Access Administration Pane

**Solution:**
1. Verify user has `profile_tier='admin'` or `is_admin=True`
2. Check `/api/v1/auth/me` returns correct tier
3. Administration pane is protected and should always be visible to admins
4. If still not visible, run migration script to reset: `python maintenance/migrate_pane_visibility.py`

### Problem: Migration Script Fails

**Solution:**
1. Ensure `TDA_AUTH_ENABLED=true` in environment
2. Check database file permissions
3. Verify SQLite database exists: `tda_auth.db`
4. Check error logs for specific SQLAlchemy errors

## Future Enhancements

Potential improvements for enhanced access control:

1. **Role-Based Access Control (RBAC)**
   - Custom roles beyond the three tiers
   - Permission groups for complex hierarchies

2. **Time-Based Access**
   - Temporary pane access for specific users
   - Scheduled visibility changes

3. **Per-User Overrides**
   - Grant individual users access to specific panes
   - Temporary elevation for specific tasks

4. **Audit Logging**
   - Track pane visibility changes
   - Log when users attempt to access restricted panes

5. **API-Level Enforcement**
   - Backend middleware to enforce pane visibility
   - Return 403 Forbidden for restricted pane API calls

## Best Practices

### Recommended Configuration Scenarios

**Scenario 1: Public Demo Environment**
```
User:      Conversations, Marketplace
Developer: [No developers]
Admin:     All panes
```
- Minimal access for demo users
- Only admins can configure system

**Scenario 2: Development Team**
```
User:      Conversations, Credentials
Developer: All except Administration
Admin:     All panes
```
- Users can chat and configure credentials
- Developers have full development tools
- Admins manage users and system

**Scenario 3: Enterprise Deployment**
```
User:      Conversations only
Developer: Conversations, Executions, RAG Maintenance
Admin:     All panes
```
- Strict access control for regular users
- Developers can debug and maintain
- Admins have full control

### Security Guidelines

1. **Principle of Least Privilege**
   - Start with minimal access
   - Grant additional panes only when needed
   - Regularly review and revoke unnecessary access

2. **Admin Protection**
   - Keep Administration pane restricted to admins only
   - Never disable admin access to Administration pane

3. **Testing Access Changes**
   - Test configuration changes with non-admin accounts
   - Verify users cannot bypass restrictions
   - Document access control decisions

4. **Regular Audits**
   - Review pane visibility configuration quarterly
   - Check for unnecessary elevated access
   - Update based on organizational changes
