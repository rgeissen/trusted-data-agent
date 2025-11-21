# Frontend Modularization Testing Guide

## Pre-Test Checklist

### Environment Setup
- [ ] Backend server is running
- [ ] Database is initialized
- [ ] At least one MCP server is configured
- [ ] Browser developer tools are open (Console tab)

### File Verification
```bash
# Verify new files exist
ls -la static/js/templateManager.js
ls -la docs/RAG/FRONTEND_MODULARIZATION.md

# Verify no hardcoded paths remain
grep -c "sql_query_v1/config" static/js/handlers/ragCollectionManagement.js
# Expected: 0 (should show "Command exited with code 1")

# Check template manager line count
wc -l static/js/templateManager.js
# Expected: ~349 lines
```

## Test Scenarios

### Test 1: Page Load and Template Initialization
**Objective**: Verify templates load dynamically on page load

**Steps**:
1. Open browser to `http://localhost:8080`
2. Open browser DevTools Console
3. Click "Add RAG Collection" button
4. Check "Auto-generate with LLM" option

**Expected Results**:
- Console shows: `[Template System] Initialized successfully`
- Console shows: `Loaded X template(s)` (where X >= 1)
- Template dropdown shows "SQL Query Template" (not "Loading templates...")
- No JavaScript errors in console

**Success Criteria**: ✅ Templates load without errors

---

### Test 2: Template Dropdown Population
**Objective**: Verify dropdown is populated from backend API

**Steps**:
1. In Add RAG Collection modal
2. Select "Auto-generate with LLM" option
3. Look at Template Type dropdown

**Expected Results**:
- Dropdown shows at least "SQL Query Template"
- Dropdown shows "API Call Template (Coming Soon)" - disabled
- Dropdown shows "Custom Template (Coming Soon)" - disabled
- SQL Query Template is selected by default

**Success Criteria**: ✅ Dropdown populated from API, not hardcoded

---

### Test 3: Template Field Rendering
**Objective**: Verify fields render dynamically based on selected template

**Steps**:
1. In Add RAG Collection modal
2. Select "Auto-generate with LLM" option
3. Select "SQL Query Template" from dropdown
4. Observe rendered fields

**Expected Results**:
- Database Name field appears
- MCP Tool Name field appears (pre-filled from config)
- Examples textarea appears
- MCP Context Prompt textarea appears
- Console shows: `[Template Fields] Rendered fields for template: sql_query_v1`

**Success Criteria**: ✅ Fields render dynamically without errors

---

### Test 4: Template Configuration Loading
**Objective**: Verify template config loads from dynamic endpoint

**Steps**:
1. In Add RAG Collection modal
2. Select "Auto-generate with LLM" option
3. Open DevTools Network tab
4. Select "SQL Query Template" from dropdown
5. Check network requests

**Expected Results**:
- Request to `/api/v1/rag/templates/sql_query_v1/config`
- MCP Tool Name field populated with value from config
- No 404 or 500 errors

**Success Criteria**: ✅ Config loads via dynamic API call

---

### Test 5: Generate Context Workflow
**Objective**: Verify context generation uses selected template

**Steps**:
1. Fill in collection name: "Test Collection 1"
2. Select MCP server
3. Select "Auto-generate with LLM"
4. Enter Subject: "Customer Orders"
5. Database Name: "sales_db"
6. Click "Generate Context" button
7. Wait for execution to complete

**Expected Results**:
- Context Result Modal opens
- Shows execution trace
- Shows final answer with database context
- Token counts displayed
- "Generate Questions" button enabled

**Success Criteria**: ✅ Context generation workflow completes

---

### Test 6: Generate Questions Workflow
**Objective**: Verify question generation uses selected template

**Steps**:
1. After successful context generation (Test 5)
2. Click "Generate Questions" button
3. Wait for LLM to generate questions

**Expected Results**:
- Questions feedback section appears
- Shows generated questions with SQL
- Shows count: "Generated X question/SQL pairs"
- "Populate Collection" button enabled
- Console shows API call to `/api/v1/rag/generate-questions`

**Success Criteria**: ✅ Questions generated successfully

---

### Test 7: Collection Population
**Objective**: Verify collection creation with generated data

**Steps**:
1. After successful question generation (Test 6)
2. Click "Populate Collection" button
3. Review the staged questions
4. Click "Create RAG Collection" button
5. Wait for collection creation

**Expected Results**:
- Success notification: "Collection created"
- Success notification: "Populated X cases successfully"
- Modal closes
- New collection appears in RAG Collections list

**Success Criteria**: ✅ Collection created and populated

---

### Test 8: Template Configuration Changes
**Objective**: Verify template config can be updated

**Steps**:
1. In RAG Collections section
2. Click "Edit" on SQL Query Template card
3. Modify "Default MCP Tool Name"
4. Modify token estimates
5. Click "Save Template Configuration"

**Expected Results**:
- Success notification appears
- Modal closes
- Console shows PUT request to `/api/v1/rag/templates/sql_query_v1/config`
- Configuration persists on page reload

**Success Criteria**: ✅ Template config updated via dynamic API

---

### Test 9: Fallback Behavior
**Objective**: Verify system handles missing template selection

**Steps**:
1. Add RAG Collection modal
2. Use browser console to clear dropdown:
   ```javascript
   document.getElementById('rag-collection-template-type').value = '';
   ```
3. Try to switch templates

**Expected Results**:
- No JavaScript errors
- System falls back to 'sql_query_v1'
- Fields still render correctly

**Success Criteria**: ✅ Graceful fallback to default template

---

### Test 10: Multiple Template Switching
**Objective**: Verify switching between templates works

**Steps**:
1. Add RAG Collection modal
2. Select "Auto-generate with LLM"
3. Select "SQL Query Template"
4. Note the fields displayed
5. If other templates are available, switch to them

**Expected Results**:
- Fields update based on template type
- No orphaned fields from previous selection
- Console logs template rendering for each switch

**Success Criteria**: ✅ Template switching works smoothly

---

## Regression Testing

### Test 11: Manual Template Population
**Objective**: Verify manual template method still works

**Steps**:
1. Create collection with "Use Template" option
2. Fill template examples manually
3. Create collection

**Expected Results**:
- Collection created successfully
- Template examples populated correctly
- No errors related to template_id

**Success Criteria**: ✅ Manual template population works

---

### Test 12: Empty Collection Creation
**Objective**: Verify "Do not populate" option works

**Steps**:
1. Create collection with "Do not populate" option
2. Create collection

**Expected Results**:
- Collection created with 0 cases
- No population attempted
- No template-related errors

**Success Criteria**: ✅ Empty collection creation works

---

## Performance Testing

### Test 13: Template Load Time
**Objective**: Measure template loading performance

**Steps**:
1. Open page with empty cache (hard refresh)
2. Note timing in console
3. Open Add RAG Collection modal
4. Note initialization timing

**Expected Results**:
- Template initialization < 500ms
- Template config loading < 200ms
- No perceivable lag in UI

**Success Criteria**: ✅ Template loading is fast

---

## Error Handling

### Test 14: Backend API Failure
**Objective**: Verify graceful error handling

**Steps**:
1. Stop backend server
2. Open Add RAG Collection modal
3. Try to select template

**Expected Results**:
- Error notification appears
- Console shows fetch error
- UI doesn't crash
- Fallback values used where possible

**Success Criteria**: ✅ Graceful error handling

---

### Test 15: Invalid Template Configuration
**Objective**: Verify validation of template data

**Steps**:
1. Use browser console to modify template config:
   ```javascript
   window.templateManager.templateCache.clear();
   ```
2. Try to load template config

**Expected Results**:
- System reloads from backend
- Validation errors logged if config invalid
- Fallback to defaults if necessary

**Success Criteria**: ✅ Invalid config handled properly

---

## Browser Compatibility

### Test 16: Cross-Browser Testing
**Objective**: Verify works in multiple browsers

**Browsers to Test**:
- [ ] Chrome/Chromium
- [ ] Firefox
- [ ] Safari (macOS)
- [ ] Edge

**Expected Results**:
- All tests pass in each browser
- No browser-specific errors
- Consistent UI rendering

**Success Criteria**: ✅ Works across browsers

---

## Console Log Verification

### Expected Console Messages
During normal operation, you should see:

```
[Template System] Initialized successfully
Loaded 1 template(s)
[Template Config] Reloaded configuration: {...}
[Template Fields] Rendered fields for template: sql_query_v1
```

### Warning Messages (Acceptable)
```
[Template Config] Failed to reload, status: 404  // If template not found
```

### Error Messages (Investigate)
```
Failed to initialize template manager: ...
Error loading config for template: ...
Failed to render template fields: ...
```

---

## Automated Testing Commands

```bash
# Backend health check
curl http://localhost:8080/api/status

# List templates
curl http://localhost:8080/api/v1/rag/templates/list

# Get template config
curl http://localhost:8080/api/v1/rag/templates/sql_query_v1/config

# Discover plugins
curl http://localhost:8080/api/v1/rag/templates/discover

# Validate plugin
curl -X POST http://localhost:8080/api/v1/rag/templates/validate \
  -H "Content-Type: application/json" \
  -d '{"plugin_path": "/path/to/plugin"}'

# Reload templates (hot reload)
curl -X POST http://localhost:8080/api/v1/rag/templates/reload
```

---

## Rollback Procedure

If issues are discovered, rollback steps:

1. **Remove templateManager.js**:
   ```bash
   rm static/js/templateManager.js
   ```

2. **Restore index.html**:
   - Remove templateManager.js script tag
   - Restore hardcoded template dropdown options

3. **Restore ragCollectionManagement.js**:
   - Revert to version before modularization
   - Use git to restore:
     ```bash
     git checkout HEAD -- static/js/handlers/ragCollectionManagement.js
     ```

4. **Restart server**:
   ```bash
   # Restart application
   ```

---

## Success Summary

### Overall Success Criteria
- ✅ All 16 tests pass
- ✅ No JavaScript errors in console
- ✅ No regression in existing functionality
- ✅ Performance metrics acceptable
- ✅ Cross-browser compatibility confirmed

### Sign-Off Checklist
- [ ] All tests executed and passed
- [ ] Documentation reviewed
- [ ] Console logs verified
- [ ] Network requests inspected
- [ ] Performance acceptable
- [ ] Error handling confirmed
- [ ] Rollback procedure documented
- [ ] Ready for production deployment

---

## Notes
- Test on a non-production instance first
- Keep browser DevTools open during all tests
- Document any unexpected behavior
- Take screenshots of errors for debugging
- Test with fresh browser cache
- Verify with actual MCP servers configured
