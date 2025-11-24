# Phase 6: Manual End-to-End Testing Guide

## Overview
This guide walks through testing the profile-based classification system with the UI.
The browser is now open at http://127.0.0.1:5000

## Prerequisites
- Application running at http://127.0.0.1:5000
- Browser open to the application
- At least one MCP server available (e.g., filesystem, brave-search, memory)

---

## Test 1: Create Profile with Classification Mode "None"

### Steps:
1. **Open Configuration Panel**
   - Click "Configuration" in the sidebar

2. **Create New Profile**
   - Click "+ Create Profile" button
   - Fill in profile details:
     - **Name**: `Test None Mode`
     - **Tag**: `NONE`
     - **Description**: `Testing flat structure without categories`
     - **LLM Provider**: Select any (e.g., Google)
     - **Model**: Select any (e.g., gemini-1.5-flash)

3. **Select Classification Mode**
   - In the "Tool & Prompt Classification" section
   - Select **"None (Flat List)"** radio button
   - Verify you see: Gray badge "No Categories"

4. **Add MCP Server** (Optional - if you want to test with actual tools)
   - Click "+ Add MCP Server"
   - Configure any available server (e.g., filesystem)
   - Or skip if just testing UI

5. **Save Profile**
   - Click "Save Profile" button
   - Verify success notification appears

6. **Verify Display**
   - Find the new profile card in the list
   - Verify it shows **Classification: None** with gray badge
   - Note the profile appearance

### Expected Results:
✓ Profile created successfully  
✓ Classification mode saved as "none"  
✓ Profile card shows gray "None" badge  
✓ No error messages  

---

## Test 2: Create Profile with Classification Mode "Light"

### Steps:
1. **Create New Profile**
   - Click "+ Create Profile" button
   - Fill in profile details:
     - **Name**: `Test Light Mode`
     - **Tag**: `LIGHT`
     - **Description**: `Testing generic categorization`
     - **LLM Provider**: Select any
     - **Model**: Select any

2. **Select Classification Mode**
   - Select **"Light (Generic Categories)"** radio button
   - Verify you see: Blue badge "Generic Categories"
   - Read the description: "Basic categorization into Tools, Prompts, and Resources"

3. **Save Profile**
   - Click "Save Profile"
   - Verify success

4. **Verify Display**
   - Find the profile card
   - Verify it shows **Classification: Light** with blue badge

### Expected Results:
✓ Profile created with light mode  
✓ Blue badge displays correctly  
✓ Mode distinction clear from "None" profile  

---

## Test 3: Create Profile with Classification Mode "Full"

### Steps:
1. **Create New Profile**
   - Click "+ Create Profile"
   - Fill in profile details:
     - **Name**: `Test Full Mode`
     - **Tag**: `FULL`
     - **Description**: `Testing semantic LLM-powered categorization`
     - **LLM Provider**: Google (or any with API key configured)
     - **Model**: gemini-1.5-flash

2. **Select Classification Mode**
   - Select **"Full (Semantic Categories)"** radio button
   - Verify you see: Purple badge "AI-Powered Categorization"
   - Read description about LLM-powered organization

3. **Save Profile**
   - Click "Save Profile"
   - Verify success

4. **Verify Display**
   - Find the profile card
   - Verify it shows **Classification: Full** with purple badge

### Expected Results:
✓ Profile created with full mode  
✓ Purple badge displays correctly  
✓ All three modes now visible in profile list  

---

## Test 4: Edit Profile to Change Classification Mode

### Steps:
1. **Open Profile for Editing**
   - Find the "Test None Mode" profile
   - Click the **Edit** button (pencil icon)

2. **Change Classification Mode**
   - In the modal, find "Tool & Prompt Classification" section
   - Verify current selection is "None" (should be checked)
   - Change to **"Full (Semantic Categories)"**
   - Verify the purple badge appears

3. **Save Changes**
   - Click "Save Profile"
   - Verify success notification

4. **Verify Update**
   - Find the profile card again
   - Verify badge changed from gray "None" to purple "Full"
   - Note that the change persisted

### Expected Results:
✓ Profile editor loads with correct current mode  
✓ Mode can be changed via radio buttons  
✓ Change persists after save  
✓ Badge updates to reflect new mode  

---

## Test 5: Visual Badge Comparison

### Steps:
1. **View Profile List**
   - Look at all the test profiles you created
   - Compare the classification badges

2. **Verify Visual Distinction**
   - **None**: Gray badge, text "None"
   - **Light**: Blue badge, text "Light"
   - **Full**: Purple badge, text "Full"

3. **Check Consistency**
   - Verify all profiles show their classification mode
   - Verify colors are consistent
   - Check that badges are readable

### Expected Results:
✓ Three distinct badge colors  
✓ Easy to scan and identify modes  
✓ Consistent styling across all profiles  

---

## Test 6: Manual Reclassification (If MCP Server Configured)

**Note**: This test requires a profile with actual MCP servers configured.

### Steps:
1. **Activate Profile**
   - Find a profile with MCP servers (or add servers to one of test profiles)
   - Click "Activate" button
   - Wait for activation to complete

2. **Locate Reclassify Button**
   - The active profile should now show a "Reclassify" button
   - Button should be in the profile's action area

3. **Trigger Reclassification**
   - Click the **"Reclassify"** button
   - Verify confirmation dialog appears
   - Confirm the action

4. **Monitor Progress**
   - Button should change to "Reclassifying..." (disabled state)
   - Wait for operation to complete
   - Button should return to "Reclassify" (enabled)

5. **Verify Success**
   - Success notification should appear
   - Check console for any errors

### Expected Results:
✓ Reclassify button visible on active profile  
✓ Confirmation dialog prevents accidental clicks  
✓ Loading state provides feedback  
✓ Operation completes successfully  
✓ No errors in console  

---

## Test 7: Profile Activation with Different Modes (Advanced)

**Note**: This requires actual MCP servers and API keys configured.

### Steps:
1. **Activate "None" Mode Profile**
   - Activate your "Test None Mode" profile
   - Navigate to the main chat interface
   - Check if tools are listed (should be flat list)

2. **Activate "Light" Mode Profile**
   - Switch to "Test Light Mode" profile
   - Check tool organization (should have basic categories)

3. **Activate "Full" Mode Profile**
   - Switch to "Test Full Mode" profile
   - Check tool organization (should have semantic categories)
   - Categories should be descriptive and contextual

### Expected Results:
✓ Different modes produce different structures  
✓ None = flat list  
✓ Light = generic categories  
✓ Full = semantic categories  

---

## Test 8: Form Validation and User Experience

### Steps:
1. **Test Radio Button Selection**
   - Open profile editor
   - Click through all three classification mode options
   - Verify only one can be selected at a time
   - Verify descriptions and badges update

2. **Test Visual Feedback**
   - Hover over each radio button option
   - Verify hover states work
   - Check that selected option is clearly highlighted

3. **Test Default Selection**
   - Create a new profile (don't select any mode manually)
   - Save the profile
   - Edit it again
   - Verify a default mode is selected (should be "Full")

### Expected Results:
✓ Mutually exclusive selection works  
✓ Visual feedback is clear  
✓ Default mode is sensible (Full)  
✓ No UI glitches or confusion  

---

## Validation Checklist

After completing all tests, verify:

- [ ] All three classification modes can be selected
- [ ] Mode selection persists after save
- [ ] Profile cards show correct badge colors
- [ ] Badge colors match modal radio button badges
- [ ] Profile editor loads current mode correctly
- [ ] Mode can be changed and persists
- [ ] Reclassify button appears on active profiles
- [ ] Reclassify operation provides user feedback
- [ ] No JavaScript errors in console
- [ ] UI is intuitive and self-explanatory
- [ ] Documentation accurately describes behavior

---

## Success Criteria

**Phase 6 is complete when:**

1. ✓ All UI components render correctly
2. ✓ Classification modes are saved and retrieved properly
3. ✓ Visual badges accurately reflect profile modes
4. ✓ Mode editing works without issues
5. ✓ Manual reclassification is functional
6. ✓ No errors in browser console
7. ✓ User experience is smooth and intuitive

---

## Troubleshooting

### Issue: Badge not showing
- **Check**: Profile has classification_mode field set
- **Fix**: Edit profile and select a mode, save

### Issue: Reclassify button not appearing
- **Check**: Profile is activated
- **Fix**: Click "Activate" button first

### Issue: Mode doesn't persist
- **Check**: Browser console for API errors
- **Fix**: Verify backend API endpoint is working

### Issue: Can't select different modes
- **Check**: Radio buttons are rendering
- **Fix**: Clear browser cache and reload

---

## Next Steps After Testing

Once Phase 6 manual testing is complete:

1. **Document any issues found**
2. **Move to Phase 8**: Deprecation planning for global setting
3. **Prepare for Phase 9-10**: Final cleanup and production deployment

---

## Notes

- This is manual testing due to MCP requiring actual server connections
- Automated tests (test_phase5_ui.py) validated API layer
- This guide validates the complete user experience
- Take screenshots if helpful for documentation

---

**Test Started**: [Fill in when you begin]  
**Test Completed**: [Fill in when done]  
**Issues Found**: [List any problems]  
**Overall Result**: [PASS/FAIL]
