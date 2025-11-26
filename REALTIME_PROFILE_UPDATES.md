# Real-Time Profile Updates Implementation

## Overview
Profile changes now appear in real-time in the Configuration UI without requiring page refresh. This implementation leverages the existing WebSocket SSE (Server-Sent Events) infrastructure used for REST Call monitoring.

## Architecture

### 1. Frontend Event Handler (`static/js/eventHandlers.js`)
When the application receives a `config_update` SSE event:
- Reloads all profiles from state via `configState.loadProfiles()`
- Dynamically imports and calls:
  - `renderProfiles()` - Updates profile cards with copy buttons
  - `renderLLMProviders()` - Refreshes LLM provider list
  - `renderMCPServers()` - Refreshes MCP server list

### 2. Backend Config Update Events
Five profile modification endpoints now broadcast `config_update` events:

| Endpoint | Method | Action | Payload |
|----------|--------|--------|---------|
| `/v1/profiles` | POST | `profile_created` | `{profile_id, profile_tag}` |
| `/v1/profiles/<id>` | PUT | `profile_updated` | `{profile_id}` |
| `/v1/profiles/<id>` | DELETE | `profile_deleted` | `{profile_id}` |
| `/v1/profiles/<id>/set_default` | POST | `profile_set_default` | `{profile_id}` |
| `/v1/profiles/set_active_for_consumption` | POST | `profiles_set_active_for_consumption` or `profiles_cleared_active_for_consumption` | `{profile_ids}` |

### 3. Profile Copy Button
Each profile card includes a copy button that:
- Copies profile ID to clipboard
- Shows "Copied!" tooltip on hover (right side, 100ms fade-in)
- Uses existing profile ID visual badge styling

## Implementation Details

### Frontend Changes

**File:** `static/js/handlers/configurationHandler.js`
- Exported `renderProfiles()` function for dynamic import from event handler
- Added copy button HTML with data-action attribute
- Attached event listener for clipboard operations

**File:** `static/js/eventHandlers.js`
- Added `config_update` event case in SSE message handler
- Async/await pattern with error handling
- Dynamic imports prevent circular dependencies

### Backend Changes

**File:** `src/trusted_data_agent/api/rest_routes.py`
- All profile endpoints (create, update, delete, set_default, set_active) now:
  1. Perform their primary operation
  2. Broadcast `config_update_notification` to all connected clients
  3. Include relevant payload data (profile IDs, actions)

#### Broadcasting Pattern
```python
# Get notification queues for the current user
notification_queues = APP_STATE.get("notification_queues", {}).get(user_uuid, set())

# Broadcast to all connected clients
if notification_queues:
    config_update_notification = {
        "type": "config_update",
        "payload": {
            "action": "profile_created",  # or other actions
            "profile_id": id,
            "profile_tag": tag
        }
    }
    for queue in notification_queues:
        asyncio.create_task(queue.put(config_update_notification))
```

## User Experience

**Without Real-Time Updates (Before):**
1. User creates a new profile in Configuration UI
2. Profile appears in list
3. User navigates to another page
4. User returns to Configuration → Page must be refreshed to see active REST Call badges

**With Real-Time Updates (After):**
1. User creates a new profile in Configuration UI
2. Profile appears in list
3. User can see profile badges update in real-time as Airflow DAG executes
4. No page refresh needed

## Event Flow Diagram

```
User Action (REST API)
    ↓
Profile Endpoint (create/update/delete/etc.)
    ↓
Operation succeeds
    ↓
Broadcast config_update to notification_queues
    ↓
Frontend SSE Handler receives config_update
    ↓
Reload profiles via configState
    ↓
Re-render Configuration sections
    ↓
UI displays updated profiles with badges
```

## Testing

1. **Start Application**
   ```bash
   python -m trusted_data_agent.main --host 0.0.0.0 --port 5000
   ```

2. **Verify Real-Time Updates**
   - Open Configuration tab in browser
   - Create a new profile via REST API or UI
   - Observe new profile appears immediately (no refresh needed)
   - Create/run an Airflow DAG
   - Watch profile badge update in real-time

3. **Verify Copy Button**
   - Hover over profile badge
   - Click copy button
   - "Copied!" tooltip appears and fades
   - Profile ID in clipboard

## Related Features

- **REST Call Badges:** Similar real-time updates using `rest_task_update` events (line 1155-1163)
- **Profile Discovery:** Profiles can be discovered via Configuration UI or REST API (`GET /v1/profiles`)
- **Active Profile Management:** Use `set_active_for_consumption` endpoint to activate profiles for monitoring

## Troubleshooting

**Profile doesn't update in real-time:**
- Check browser WebSocket connection (Network tab → WS)
- Verify SSE event handler is active: `console.log('config_update received')`
- Check server logs for broadcast errors

**Copy button not working:**
- Verify profile ID appears in clipboard: `console.log(await navigator.clipboard.readText())`
- Check browser console for JavaScript errors
- Verify copyProfileId listener is attached in configurationHandler

**No config_update events:**
- Verify notification_queues exist: Check APP_STATE in server logs
- Confirm user_uuid is being extracted correctly
- Check for asyncio.create_task errors in server logs
