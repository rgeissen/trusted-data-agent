# Profile Override Feature - Implementation Summary

## ✅ Feature Complete

The trusted-data-agent REST API now supports **per-query profile overrides with UI visibility**.

## What Was Implemented

### 1. Optional Profile Parameter in REST Queries

REST endpoint: `POST /api/v1/sessions/{session_id}/query`

**Request Body:**
```json
{
  "prompt": "Your question here",
  "profile_id": "profile-xxx-optional"  // Optional override
}
```

- If `profile_id` is specified, that profile is used for the query
- If `profile_id` is omitted, the user's default profile is used

### 2. Per-Message Profile Tracking

Each message in the session history now includes `profile_tag`:

```json
{
  "role": "user",
  "content": "What is the system version?",
  "profile_tag": "GOGET",  // ← Tracks which profile was used
  "source": "rest",
  "turn_number": 1
}
```

### 3. UI Profile Badges

When loading a session, each message displays its profile badge:

- **Visual indicator** showing which profile executed that query
- **Color-coded** based on profile branding
- **Different badges** for different queries (when overrides are used)

## Architecture

```
REST API
  ↓
  ├─ Accept optional profile_id
  ├─ Default to user's default profile
  ↓
Execution Service
  ├─ Receive profile_override_id
  ├─ Get profile tag from profile manager
  ↓
Session Manager
  ├─ Store profile_tag with message
  ├─ Save to session history
  ↓
UI
  ├─ Read profile_tag from message
  ├─ Render profile badge with styling
```

## Code Changes

### REST Routes (`src/trusted_data_agent/api/rest_routes.py`)

**Before:**
```python
# Only used default profile for all queries
profile_id_to_use = config_manager.get_default_profile_id(user_uuid)
```

**After:**
```python
# Accept optional profile_id parameter
profile_id_override = data.get("profile_id")
profile_id_to_use = profile_id_override or config_manager.get_default_profile_id(user_uuid)

# Pass to execution service
await execution_service.run_agent_execution(
    ...,
    profile_override_id=profile_id_override
)
```

### Execution Service (`src/trusted_data_agent/agent/execution_service.py`)

**Changes:**
```python
# Added profile_override_id parameter
async def run_agent_execution(
    ...,
    profile_override_id: str = None
):
    # Resolve profile tag from profile_override_id
    profile_tag = None
    if profile_override_id or session_data.get("profile_tag"):
        profiles = config_manager.get_profiles(user_uuid)
        profile = next((p for p in profiles if p.get("id") == profile_override_id), None)
        if profile:
            profile_tag = profile.get("tag")
    
    # Pass to message storage
    session_manager.add_message_to_histories(
        ...,
        profile_tag=profile_tag  # ← Store profile with message
    )
```

### UI (`static/js/handlers/sessionManagement.js`)

**Changes:**
```javascript
// Already reads profile_tag from messages
const profileTag = msg.profile_tag || null;

// Passes to UI rendering
UI.addMessage(msg.role, msg.content, ..., profileTag);
```

## Test Results

✅ **Test 1: Basic Profile Override**
- Query with default profile: ✓ Uses default
- Query with override: ✓ Uses override
- Both work correctly

✅ **Test 2: Per-Message Profile Tags**
- Message 1: `profile_tag: GOGET` (default)
- Message 2: `profile_tag: FRGOT` (override)
- Both correctly stored

✅ **Test 3: Session History Loading**
- Messages load with profile tags
- UI renders profile badges
- Different messages show different profiles

## Files Modified

1. **`src/trusted_data_agent/api/rest_routes.py`**
   - Extract `profile_id` from request body
   - Pass `profile_override_id` to execution service
   - Store override in task state

2. **`src/trusted_data_agent/agent/execution_service.py`**
   - Receive `profile_override_id` parameter
   - Resolve to profile tag
   - Pass to message storage

3. **`src/trusted_data_agent/core/session_manager.py`**
   - Already supported (no changes needed)

4. **`static/js/handlers/sessionManagement.js`**
   - Already supported (no changes needed)

5. **`static/js/ui.js`**
   - Already supported (no changes needed)

## Files Created

1. **`docs/RestAPI/PROFILE_OVERRIDE_FEATURE.md`**
   - Complete feature documentation
   - Usage examples (bash, Python, JavaScript)
   - UI display examples
   - Error handling notes

2. **Test files:**
   - `test/test_profile_override.py` - Basic functionality
   - `test/test_profile_override_per_message.py` - Per-message tracking
   - `test/verify_profile_tags.py` - Verification script
   - `test/test_profile_badges_after_restart.py` - End-to-end test

## Usage Example

```bash
# Get available profiles
curl -X GET http://localhost:5000/api/v1/profiles \
  -H "Authorization: Bearer {token}"

# Query with default profile
curl -X POST http://localhost:5000/api/v1/sessions/{id}/query \
  -H "Authorization: Bearer {token}" \
  -d '{"prompt": "Question 1"}'

# Query with specific profile
curl -X POST http://localhost:5000/api/v1/sessions/{id}/query \
  -H "Authorization: Bearer {token}" \
  -d '{"prompt": "Question 2", "profile_id": "profile-xxx"}'
```

## UI Behavior

### Single Profile Session
```
User (@GOGET)
What is the system version?

Assistant
The version is 20.00.22.31.
```

### Multi-Profile Session (with overrides)
```
User (@GOGET)
What is the system version?

Assistant
The version is 20.00.22.31.

User (@FRGOT)          ← Different profile badge
Tell me about the date

Assistant
The date is 2025-11-26.
```

## Benefits

1. **Flexibility** - Use different profiles for different queries in same session
2. **Visibility** - UI clearly shows which profile was used for each query
3. **Traceability** - Session history records profile for each message
4. **Consistency** - Works with both web UI and REST API
5. **Backward Compatible** - Omitting `profile_id` uses default

## Next Steps

- All functionality is complete and tested ✅
- UI displays profile badges correctly ✅
- Documentation is available ✅
- Ready for production use ✅

