# Docker Credential Isolation Setup

## Overview

The Trusted Data Agent now supports **multi-user Docker deployments** with proper credential isolation. When running in a Docker container with `TDA_CONFIGURATION_PERSISTENCE=false`, credentials are never saved to disk or browser storage, ensuring each user must provide their own credentials per session.

## How It Works

### Backend (Server-Side)
- Environment variable: `TDA_CONFIGURATION_PERSISTENCE=false`
- Location: Set in `docker-compose.yml` or `docker run` command
- Effect: Server never writes configuration to `tda_config.json`
- API response includes `configurationPersistence: false` flag

### Frontend (Client-Side)
- Reads `configurationPersistence` flag from `/api/status`
- When `false`, all `localStorage.setItem()` calls for credentials are blocked
- Credentials remain in memory only for the duration of the session
- On page refresh or browser restart, user must reconfigure

## Configuration Files

### docker-compose.yml
```yaml
environment:
  - TDA_CONFIGURATION_PERSISTENCE=false
  - CORS_ALLOWED_ORIGINS=https://your-domain.com
```

### Alternative: docker run
```bash
docker run -d \
  -p 5050:5000 \
  -e TDA_CONFIGURATION_PERSISTENCE=false \
  -e CORS_ALLOWED_ORIGINS=https://your-domain.com \
  trusted-data-agent:latest
```

## User Experience

### With Persistence Disabled (`TDA_CONFIGURATION_PERSISTENCE=false`)
1. User opens application → sees welcome screen
2. User clicks "Configure Application"
3. User enters MCP server details and LLM credentials
4. Application connects and loads resources
5. User can work normally during the session
6. **On browser refresh/close**: Configuration is lost
7. Next user gets a clean slate with no saved credentials

### With Persistence Enabled (default)
1. User opens application → sees welcome screen
2. User configures once
3. Credentials saved to browser localStorage
4. **On browser refresh**: "Connect and Load" button appears
5. User clicks to auto-reconnect with saved credentials

## Security Considerations

### ✅ Advantages of Disabled Persistence
- **Zero credential leakage** between users
- **No stored secrets** in browser localStorage
- **Session-only access** - credentials cleared on restart
- Ideal for shared/public deployments

### ⚠️ Trade-offs
- Users must re-enter credentials after every browser restart
- Less convenient for single-user deployments
- Consider providing pre-configured environment variables for certain settings

## Implementation Details

### Modified Files
1. **Backend**:
   - `src/trusted_data_agent/api/routes.py` - Added `configurationPersistence` to status response
   - `src/trusted_data_agent/core/config.py` - Reads `TDA_CONFIGURATION_PERSISTENCE` env var

2. **Frontend**:
   - `static/js/state.js` - Added `configurationPersistence` state flag
   - `static/js/storageUtils.js` - **NEW** Safe localStorage wrapper
   - `static/js/main.js` - Sets persistence flag from server, clears credentials when disabled
   - `static/js/handlers/configManagement.js` - Uses `safeSetItem()` for credentials
   - `static/js/handlers/configurationHandler.js` - Uses `safeSetItem()` for credentials

### Storage Wrapper API
```javascript
import { safeSetItem, safeGetItem, clearAllCredentials } from './storageUtils.js';

// These respect the server's configurationPersistence setting
safeSetItem('key', 'value');  // No-op if persistence disabled
const value = safeGetItem('key');  // Returns null if persistence disabled

// Clear all stored credentials
clearAllCredentials();
```

## Testing

### Test Persistence Disabled
1. Set `TDA_CONFIGURATION_PERSISTENCE=false` in docker-compose.yml
2. Start container: `docker-compose up -d`
3. Open application in browser
4. Configure MCP and LLM
5. Verify configuration works
6. **Refresh browser** → Should require reconfiguration
7. Check browser console for: `[Storage] Persistence disabled - skipping localStorage.setItem`

### Test Persistence Enabled (default)
1. Remove or set `TDA_CONFIGURATION_PERSISTENCE=true`
2. Start container
3. Configure MCP and LLM
4. **Refresh browser** → Should show "Start Conversation" button
5. Click to auto-reconnect with saved credentials

## Deployment Recommendations

### Multi-User/Public Docker Deployment
```yaml
environment:
  - TDA_CONFIGURATION_PERSISTENCE=false
  - CORS_ALLOWED_ORIGINS=https://your-domain.com
```

### Single-User Docker Deployment
```yaml
environment:
  - TDA_CONFIGURATION_PERSISTENCE=true  # or omit (default)
  - CORS_ALLOWED_ORIGINS=https://your-domain.com
```

### Development (Local)
- Default behavior: persistence enabled
- Credentials saved to browser for convenience

## Troubleshooting

### Problem: Credentials Still Saved After Setting Persistence to False
**Solution**: Clear browser localStorage manually:
```javascript
// In browser console
localStorage.clear();
```
Or use the provided utility:
```javascript
import { clearAllCredentials } from './storageUtils.js';
clearAllCredentials();
```

### Problem: Getting "Start Conversation" Button When Persistence is Disabled
**Solution**: 
1. Verify `TDA_CONFIGURATION_PERSISTENCE=false` in docker-compose.yml
2. Restart container: `docker-compose restart`
3. Hard refresh browser: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)
4. Check `/api/status` response includes `"configurationPersistence": false`

## Future Enhancements

Potential improvements for even better multi-user support:

1. **Environment Variable Pre-Configuration**
   - Allow setting MCP server via `TDA_MCP_HOST`, `TDA_MCP_PORT` env vars
   - Reduces user configuration burden

2. **Session Tokens**
   - Implement proper session management with tokens
   - Track which user is using which session

3. **OAuth Integration**
   - Allow users to authenticate with OAuth providers
   - Each user brings their own LLM API keys via secure token exchange

4. **Read-Only Mode**
   - Admin pre-configures everything
   - Users can only query, not change configuration
