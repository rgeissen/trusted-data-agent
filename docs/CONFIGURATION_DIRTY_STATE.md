# Configuration Dirty State Tracking

## Overview

Prevents users from navigating away from the Configuration/Setup pane when they have unsaved changes, ensuring data integrity and preventing accidental loss of configuration work.

## Problem Statement

**Before:**
- Users could navigate away from Configuration view at any time
- Changes to MCP servers, LLM providers, profiles, or advanced settings could be lost
- No visual indication of unsaved changes
- System could end up in inconsistent state if changes weren't saved

**After:**
- ✅ All configuration changes are tracked
- ✅ Navigation is blocked when there are unsaved changes
- ✅ User must explicitly save or discard changes
- ✅ Visual indicators show dirty state
- ✅ System maintains consistency

## Implementation

### 1. Core Module: `configDirtyState.js`

**Purpose:** Tracks all changes to configuration parameters and controls navigation

**Tracked Changes:**
- MCP Server selection changes
- LLM Provider selection changes
- Profile modifications (all profiles)
- Default profile changes
- Advanced Settings (TTS credentials, charting intensity)

**Key Functions:**

```javascript
// Initialize tracking when entering configuration view
initializeConfigDirtyTracking()

// Check if navigation is allowed
canNavigateAway(targetView) → boolean

// Mark configuration as clean after successful save
markConfigClean()

// Reset tracking when leaving configuration view
resetConfigDirtyTracking()

// Check dirty state
isConfigDirty() → boolean
```

### 2. Integration with View Switching (`ui.js`)

**Enhanced `handleViewSwitch()` Logic:**

```javascript
handleViewSwitch(viewId)
  ├─ Is user leaving configuration view?
  │   ├─ Yes → Check canNavigateAway(viewId)
  │   │   ├─ Dirty? → Block navigation, show warning
  │   │   └─ Clean? → Allow navigation
  │   └─ No → Proceed normally
  ├─ Entering configuration? → Initialize dirty tracking
  └─ Perform view switch
```

### 3. Integration with Configuration Handler

**Event Dispatching:**
- Profile updates dispatch `profile-modified` event
- Default profile changes dispatch `default-profile-changed` event
- MCP/LLM selects have change listeners
- Advanced settings have input/change listeners

**Save & Connect Integration:**
- After successful configuration save
- Calls `markConfigClean()`
- Allows pending navigation to proceed

## User Experience Flow

### Scenario 1: User Makes Changes and Tries to Navigate

```
1. User enters Configuration view
   └─ initializeConfigDirtyTracking() called
   
2. User changes MCP server selection
   └─ markDirty('mcp-server') called
   └─ Orange dot appears on Configuration menu
   └─ "Save & Connect" button highlights (orange)
   └─ "Discard Changes" button appears
   
3. User clicks "Conversation" menu item
   └─ handleViewSwitch('conversation-view') called
   └─ canNavigateAway() checks dirty state
   └─ Returns FALSE - navigation blocked
   └─ Warning banner appears:
       "You have unsaved changes in Configuration.
        Please click 'Save & Connect' or discard them."
   
4. User has two options:
   
   Option A: Save Changes
   ├─ Click "Save & Connect"
   ├─ Configuration saved to backend
   ├─ markConfigClean() called
   ├─ Navigation proceeds automatically
   └─ User lands on Conversation view
   
   Option B: Discard Changes
   ├─ Click "Discard Changes"
   ├─ Confirmation dialog appears
   ├─ User confirms
   ├─ Configuration reloaded from backend
   ├─ markConfigClean() called
   ├─ Navigation proceeds automatically
   └─ User lands on Conversation view
```

### Scenario 2: User Saves Without Navigating

```
1. User makes changes → Dirty state activated
2. User clicks "Save & Connect"
3. Configuration saved successfully
4. markConfigClean() called
5. Dirty indicators removed
6. User stays on Configuration view (no pending navigation)
```

## Visual Indicators

### 1. Orange Dot on Configuration Menu Item
- **When:** Configuration is dirty
- **Where:** Next to "Configuration" text in sidebar
- **Effect:** Pulsing orange dot
- **Purpose:** Alert user they have unsaved changes

### 2. "Save & Connect" Button Highlight
- **When:** Configuration is dirty
- **Change:** Background changes to orange (`bg-orange-600`)
- **Purpose:** Draw attention to the save action

### 3. "Discard Changes" Button
- **When:** Configuration is dirty AND user attempts navigation
- **Where:** Next to "Save & Connect" button
- **Purpose:** Provide explicit discard option

### 4. Warning Banner
- **When:** User attempts to navigate with unsaved changes
- **Message:** Clear explanation and instructions
- **Type:** Warning (orange banner)

## Technical Details

### State Tracking

```javascript
dirtyState = {
    isDirty: boolean,              // Overall dirty flag
    originalState: object,         // Baseline captured state
    trackedFields: Map,            // Changed fields with timestamps
    isInitialized: boolean,        // Tracking active?
    pendingNavigation: string      // Target view if blocked
}
```

### Change Detection

**Captured State:**
```javascript
{
    activeMcpServer: "server-id",
    activeLlmProvider: "provider-id",
    defaultProfile: "profile-id",
    profiles: [...],              // All profile configs
    advancedSettings: {
        ttsCredentials: "...",
        chartingIntensity: "none"
    }
}
```

**Change Listeners:**
- `#mcp-server-select` → change event
- `#llm-config-select` → change event
- `#tts-credentials-json` → input event
- `#charting-intensity` → change event
- Custom events: `profile-modified`, `default-profile-changed`

### Navigation Control Flow

```
handleViewSwitch(targetView)
  ↓
[Is leaving configuration?]
  ↓ YES
[Check dirty state]
  ↓
[Dirty?]
  ↓ YES
[Block navigation]
  ├─ Store pendingNavigation = targetView
  ├─ Show warning banner
  └─ Show "Discard Changes" button
  
User clicks "Save & Connect"
  ↓
reconnectAndLoad() executes
  ↓
[Save successful]
  ↓
markConfigClean()
  ├─ Clear dirty flag
  ├─ Update UI indicators
  ├─ Check pendingNavigation
  └─ Execute pending navigation → handleViewSwitch(targetView)
```

## Edge Cases Handled

### 1. Rapid Clicks
**Scenario:** User clicks navigation multiple times rapidly
**Handling:** 
- First click stores `pendingNavigation`
- Subsequent clicks while dirty are blocked
- Only one navigation proceeds after save

### 2. Direct URL Change (if applicable)
**Scenario:** User tries to bypass UI navigation
**Handling:** View switch always goes through `handleViewSwitch()`

### 3. Save Failure
**Scenario:** Backend save fails
**Handling:**
- `markConfigClean()` not called
- User remains on configuration view
- Dirty state persists
- Can retry or discard

### 4. Browser Refresh
**Scenario:** User refreshes page with unsaved changes
**Handling:**
- Changes lost (browser limitation)
- Future enhancement: `beforeunload` event handler

### 5. Session Timeout
**Scenario:** User leaves configuration dirty for extended period
**Handling:**
- JWT token may expire
- Save will fail with auth error
- User must re-authenticate

## Testing Strategy

### Manual Test Cases

**Test 1: Basic Dirty Detection**
1. Enter Configuration view
2. Change MCP server
3. ✅ Verify orange dot appears
4. ✅ Verify button highlights

**Test 2: Navigation Blocking**
1. Enter Configuration view
2. Change default profile
3. Click "Conversation" menu
4. ✅ Verify navigation blocked
5. ✅ Verify warning banner shown
6. ✅ Verify "Discard Changes" button appears

**Test 3: Save and Navigate**
1. Enter Configuration view
2. Make changes
3. Click "Conversation" menu (blocked)
4. Click "Save & Connect"
5. ✅ Verify save succeeds
6. ✅ Verify automatic navigation to Conversation
7. ✅ Verify indicators cleared

**Test 4: Discard Changes**
1. Enter Configuration view
2. Change LLM provider
3. Click "Intelligence" menu (blocked)
4. Click "Discard Changes"
5. Confirm dialog
6. ✅ Verify configuration reverted
7. ✅ Verify navigation proceeds

**Test 5: Multiple Changes**
1. Change MCP server
2. Change default profile
3. Modify advanced settings
4. ✅ All tracked in dirtyState.trackedFields
5. Save
6. ✅ All changes persisted

**Test 6: Stay on Configuration**
1. Make changes
2. Click "Save & Connect"
3. ✅ Saved successfully
4. ✅ Dirty indicators removed
5. ✅ User stays on Configuration view

### Automated Testing

```javascript
// Test dirty state detection
import { initializeConfigDirtyTracking, isConfigDirty, markConfigClean } from './configDirtyState.js';

// Test 1: Initial state
initializeConfigDirtyTracking();
assert(isConfigDirty() === false);

// Test 2: Mark dirty
document.dispatchEvent(new CustomEvent('profile-modified', { 
    detail: { profileId: 'test', updates: {} } 
}));
assert(isConfigDirty() === true);

// Test 3: Mark clean
markConfigClean();
assert(isConfigDirty() === false);

// Test 4: Navigation blocking
const canNav = canNavigateAway('conversation-view');
assert(canNav === true); // Should be clean now
```

## Debugging

### Console Logging

**Initialization:**
```
[ConfigDirty] Initializing dirty state tracking
[ConfigDirty] Captured initial state: {...}
[ConfigDirty] Change listeners attached
[ConfigDirty] ✅ Dirty state tracking initialized
```

**Change Detection:**
```
[ConfigDirty] ⚠️ Configuration is now DIRTY - changes detected in: mcp-server
[ConfigDirty] Additional changes detected in: default-profile
```

**Navigation:**
```
[handleViewSwitch] Switching to view: conversation-view
[ConfigDirty] ❌ Navigation blocked - unsaved changes detected
```

**Save:**
```
[reconnectAndLoad] Conversation fully initialized
[reconnectAndLoad] Configuration marked as clean after successful save
[ConfigDirty] ✅ Configuration marked as CLEAN
[ConfigDirty] Executing pending navigation to: conversation-view
```

### Debug Function

```javascript
import { getConfigDirtyState } from './configDirtyState.js';

// In browser console
const state = window.getConfigDirtyState?.();
console.log(state);

// Output:
// {
//   isDirty: true,
//   changedFields: ['mcp-server', 'default-profile'],
//   pendingNavigation: 'conversation-view',
//   isInitialized: true
// }
```

## Future Enhancements

### 1. Granular Change Comparison
- Deep diff profiles to detect actual changes
- Ignore cosmetic changes (whitespace, etc.)

### 2. Auto-save
- Periodic auto-save of configuration
- Draft state preservation

### 3. Undo/Redo
- Track change history
- Allow undo of specific changes

### 4. Browser Refresh Protection
```javascript
window.addEventListener('beforeunload', (e) => {
    if (isConfigDirty()) {
        e.preventDefault();
        e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
    }
});
```

### 5. Change Summary
- Show list of changed fields before save
- Confirmation dialog with change details

## Related Systems

### 1. Conversation Initialization
- Configuration changes trigger `resetInitialization()`
- Ensures conversation reinitializes with new settings

### 2. Repository Loading
- Configuration save triggers repository reload
- Knowledge and planner collections refresh

### 3. Profile Management
- Profile updates dispatch custom events
- Dirty state tracker listens for these events

## Conclusion

The Configuration Dirty State Tracking system ensures:
- ✅ **Data Integrity** - No accidental loss of configuration work
- ✅ **User Awareness** - Clear visual indicators of unsaved changes
- ✅ **Forced Decision** - Must save or discard before leaving
- ✅ **System Consistency** - Configuration always in known state
- ✅ **Better UX** - Users understand their current state and required actions

This pattern follows industry best practices for dirty state management and provides a robust foundation for configuration management.
