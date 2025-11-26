#!/bin/bash

# PROFILE BADGES IN REST API - FIX SUMMARY

## Issue
Profile badges (color/branding indicators) were not appearing in the UI for REST API-generated sessions.
This is because the profile information wasn't being:
1. Attached to the session during creation
2. Used during query execution (profile context wasn't being activated)

## Root Cause
1. Session creation didn't store `profile_id` - only `profile_tag`
2. Query execution via REST API didn't activate the profile context
3. Profile context includes color/branding information needed for UI display

## Solution Implemented

### 1. Session Manager Enhancement
**File:** `src/trusted_data_agent/core/session_manager.py`
- Added `profile_id` parameter to `create_session()` function
- Now stores profile_id in session JSON alongside provider, model, profile_tag

### 2. REST API Session Creation Fix
**File:** `src/trusted_data_agent/api/rest_routes.py` (lines 1025)
- Updated POST `/v1/sessions` endpoint
- Now passes `profile_id=default_profile_id` to create_session()
- Ensures sessions know which profile was used

### 3. REST API Query Execution Fix
**File:** `src/trusted_data_agent/api/rest_routes.py` (lines 1077-1087)
- Updated POST `/v1/sessions/{id}/query` endpoint
- Added profile context switching before query execution
- Activates profile's LLM and color scheme before running the query

## How It Works Now

### Session Creation Flow
```
1. User submits POST /v1/sessions with auth token
2. Get default profile_id from config_manager
3. Create session with profile_id parameter
4. Session file now contains: {profile_id, profile_tag, provider, ...}
```

### Query Execution Flow
```
1. User submits POST /v1/sessions/{id}/query
2. Get user's default profile_id
3. Activate profile context (switch_profile_context)
4. Execute query with activated profile
5. Profile's LLM instance and color info active
6. Events sent to UI include profile context
```

## What This Enables

✅ **Profile Badges in UI**
- Sessions now display with correct provider color/branding
- Profile information available through session JSON

✅ **Query Attribution**
- Each query execution associated with correct profile
- UI can show which profile was used for each message

✅ **Consistent Provider Branding**
- REST API queries display same as UI queries
- Color badges match profile configuration

## Testing

Created test scripts to verify:
- `test/test_profile_badges.py` - Tests profile info in REST queries
- `test/test_profile_storage.py` - Verifies profile_id stored in sessions
- `test/test_direct_session_creation.py` - Tests direct session creation with profile_id

## Files Modified

1. `src/trusted_data_agent/core/session_manager.py`
   - Added profile_id parameter to create_session()

2. `src/trusted_data_agent/api/rest_routes.py`
   - POST /v1/sessions - passes profile_id when creating
   - POST /v1/sessions/{id}/query - activates profile context

## Verification Checklist

After server restart:

- [ ] Create session via REST API
- [ ] Check session JSON contains profile_id
- [ ] Submit query via REST API
- [ ] Verify profile color appears in UI
- [ ] Verify provider badge appears in session list
- [ ] Verify color matches profile configuration

## Server Restart Required

These changes require the Flask development server to be restarted to take effect:

```bash
# Stop current server (Ctrl+C)
# Clear Python cache
find src -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null

# Restart server
python -m trusted_data_agent.main
```
