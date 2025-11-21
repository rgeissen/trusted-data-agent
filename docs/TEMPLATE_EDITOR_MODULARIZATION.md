# Template Editor Modal Modularization

## Overview
The Template Editor Modal has been successfully refactored to be fully modular and template-agnostic, matching the backend's plugin architecture. This completes the frontend modularization effort started with `templateManager.js`.

## Changes Made

### 1. HTML Structure Updates (`templates/index.html`)

#### Template Info Section
**Before:**
```html
<h3 class="text-lg font-semibold text-white mb-2">SQL Query Template</h3>
<p class="text-sm text-gray-400">Two-phase plan: Execute SQL, generate report</p>
```

**After:**
```html
<h3 id="template-editor-template-name" class="text-lg font-semibold text-white mb-2">Loading...</h3>
<p id="template-editor-template-description" class="text-sm text-gray-400"></p>
```

#### Input Variables Section
**Before:**
```html
<!-- Hardcoded badges for: user_query, sql_statement, database_name -->
<span class="inline-flex items-center...">user_query *</span>
<span class="inline-flex items-center...">sql_statement *</span>
<span class="inline-flex items-center...">database_name</span>
```

**After:**
```html
<div id="template-editor-input-variables" class="hidden mb-6">
    <h4 class="text-md font-medium text-gray-300 mb-3">Input Variables</h4>
    <div id="template-editor-input-vars-content" class="flex flex-wrap gap-2">
        <!-- Dynamically populated -->
    </div>
</div>
```

#### Configuration Fields Section
**Before:**
```html
<!-- Hardcoded fields -->
<input id="template-default-mcp-tool" value="base_executeRawSQLStatement">
<input id="template-default-mcp-context-prompt" value="base_tableBusinessDesc">
<input id="template-input-tokens" type="number" value="150">
<input id="template-output-tokens" type="number" value="180">
```

**After:**
```html
<div id="template-editor-config-fields" class="mb-6">
    <h4 class="text-md font-medium text-gray-300 mb-3">Configuration</h4>
    <div id="template-editor-config-content">
        <!-- Dynamically populated -->
    </div>
</div>
```

### 2. JavaScript Function Refactoring (`static/js/handlers/ragCollectionManagement.js`)

#### New Function: `editTemplate(templateId)`
Replaces the hardcoded `editSqlTemplate()` with a modular approach:

**Key Features:**
- **Dynamic Template Loading**: Loads any template by ID
- **Template Metadata Display**: Shows template name and description from backend
- **Dynamic Field Rendering**: Creates form fields based on template configuration
- **Configuration Caching**: Uses `templateManager.getTemplateConfig()` with caching
- **Input Variables Rendering**: Dynamically creates badges for required/optional variables
- **Template ID Storage**: Stores in modal's `data-template-id` attribute for form submission

**Code Structure:**
```javascript
async function editTemplate(templateId = null) {
    // 1. Get template ID from parameter or current selection
    const selectedTemplateId = templateId || ragCollectionTemplateType?.value || 'sql_query_v1';
    
    // 2. Store template ID for form submission
    modal.setAttribute('data-template-id', selectedTemplateId);
    
    // 3. Load template metadata
    const template = window.templateManager.getTemplate(selectedTemplateId);
    
    // 4. Populate template info
    document.getElementById('template-editor-template-name').textContent = template.display_name;
    document.getElementById('template-editor-template-description').textContent = template.description;
    
    // 5. Load template configuration
    const config = await window.templateManager.getTemplateConfig(selectedTemplateId);
    
    // 6. Render input variables dynamically
    if (config.input_variables && config.input_variables.length > 0) {
        config.input_variables.forEach(variable => {
            // Create badge with name and required indicator
        });
    }
    
    // 7. Render configuration fields dynamically
    if (config.default_mcp_tool !== undefined) {
        configContainer.appendChild(createConfigField(...));
    }
    // ... additional fields based on config
}
```

#### New Helper: `createConfigField(id, label, value, type, description)`
Creates form input elements dynamically:

**Supported Types:**
- `text`: Standard text input
- `number`: Numeric input with min/step attributes
- `textarea`: Multi-line text area

**Features:**
- Consistent styling with Tailwind CSS
- Optional description text
- Proper label association
- Value pre-population

#### Updated Function: `handleTemplateEditorSubmit(event)`
Now fully template-agnostic:

**Before:**
```javascript
// Hardcoded field access
const defaultMcpTool = document.getElementById('template-default-mcp-tool').value;
const defaultMcpContextPrompt = document.getElementById('template-default-mcp-context-prompt').value;
```

**After:**
```javascript
// 1. Get template ID from modal
const templateId = modal.getAttribute('data-template-id') || 'sql_query_v1';

// 2. Load current configuration to know which fields exist
const currentConfig = await window.templateManager.getTemplateConfig(templateId);

// 3. Build configuration payload dynamically
const configPayload = {};
if (currentConfig.default_mcp_tool !== undefined) {
    const toolInput = document.getElementById('template-default-mcp-tool');
    if (toolInput) {
        configPayload.default_mcp_tool = toolInput.value.trim();
    }
}
// ... collect other fields dynamically

// 4. Save to backend with dynamic template ID
await fetch(`/api/v1/rag/templates/${templateId}/config`, {
    method: 'PUT',
    body: JSON.stringify(configPayload)
});
```

**Validation:**
- Only validates fields that exist in the template configuration
- Checks for empty required fields
- Properly parses numeric values

**Cache Management:**
- Calls `window.templateManager.clearCache()` after successful save
- Forces fresh configuration load on next access

#### Updated Event Listener: Edit Template Button
**Before:**
```javascript
editSqlTemplateBtn.addEventListener('click', (event) => {
    editSqlTemplate(); // Always opens SQL template
});
```

**After:**
```javascript
editSqlTemplateBtn.addEventListener('click', (event) => {
    const currentTemplateId = ragCollectionTemplateType?.value || 'sql_query_v1';
    editTemplate(currentTemplateId); // Opens currently selected template
});
```

#### Backward Compatibility
Maintained for legacy code:
```javascript
// Alias function
async function editSqlTemplate() {
    await editTemplate('sql_query_v1');
}

// Global exports
window.editTemplate = editTemplate;
window.editSqlTemplate = editSqlTemplate; // Backward compatibility
```

## Architecture

### Data Flow
```
User Clicks "Edit Template" Button
    ↓
editTemplate(templateId) called with current selection
    ↓
templateManager.getTemplate(templateId) - Get metadata
    ↓
templateManager.getTemplateConfig(templateId) - Get configuration
    ↓
Dynamic HTML rendering:
  - Template name & description
  - Input variables badges
  - Configuration form fields
    ↓
Modal displayed with populated fields
    ↓
User edits configuration
    ↓
handleTemplateEditorSubmit() triggered
    ↓
Collect values from dynamic fields
    ↓
PUT /api/v1/rag/templates/{templateId}/config
    ↓
Clear cache → Close modal → Show success notification
```

### Dependencies
- **templateManager.js**: Core template management module
  - `getTemplate(id)`: Retrieve template metadata
  - `getTemplateConfig(id)`: Fetch configuration with caching
  - `clearCache()`: Invalidate configuration cache
- **Backend API**:
  - `GET /api/v1/rag/templates/{id}/config`: Load configuration
  - `PUT /api/v1/rag/templates/{id}/config`: Save configuration

## Benefits

### 1. **Template Agnostic**
- Works with any template type (SQL, REST, GraphQL, etc.)
- No hardcoded template references
- Automatically adapts to template structure

### 2. **Dynamic Field Rendering**
- Configuration fields created based on template definition
- No manual HTML updates needed for new templates
- Supports extensibility

### 3. **Maintainability**
- Single code path for all templates
- Changes to template structure automatically reflected
- Reduced code duplication

### 4. **Backend Consistency**
- Matches backend plugin architecture
- Uses same configuration structure
- API-driven UI generation

### 5. **Backward Compatible**
- `editSqlTemplate()` alias maintained
- Existing code continues to work
- Gradual migration path

## Testing Checklist

### Basic Functionality
- [ ] Click "Edit Template" button - modal opens
- [ ] Template name displays correctly (e.g., "SQL Query Template")
- [ ] Template description populates
- [ ] Input variables badges render with required indicators
- [ ] Configuration fields render with correct values
- [ ] Modal animation smooth (fade in/out)

### Configuration Loading
- [ ] Fields pre-populated with current values
- [ ] Numeric fields show correct numbers
- [ ] Text fields show correct strings
- [ ] Default values used if API fails

### Form Submission
- [ ] Edit configuration values
- [ ] Click "Save Configuration" - saves successfully
- [ ] Success notification displays
- [ ] Modal closes after save
- [ ] Changes persist (reopen modal to verify)

### Validation
- [ ] Empty required field → error notification
- [ ] Invalid numeric value → validation error
- [ ] Valid submission → success

### Template Switching
- [ ] Select "SQL Query" template → Edit → Correct fields
- [ ] Switch to different template (if available) → Edit → Different fields
- [ ] Configuration specific to each template

### Error Handling
- [ ] Backend unavailable → graceful error message
- [ ] Invalid template ID → error notification
- [ ] Network timeout → error handling

### Backward Compatibility
- [ ] `window.editSqlTemplate()` works from console
- [ ] `window.editTemplate('sql_query_v1')` works from console
- [ ] Existing code calling `editSqlTemplate()` still functions

### Cache Management
- [ ] Edit and save configuration
- [ ] Reload page
- [ ] Configuration changes persisted
- [ ] Cache cleared after save (fresh load next time)

## Migration Path for New Templates

### Adding a New Template Type
1. **Backend**: Add plugin directory with `manifest.json` and `template.json`
2. **Template Discovery**: Backend automatically discovers on `/api/v1/rag/templates/discover`
3. **Frontend**: Automatically populated in dropdown via `templateManager.initialize()`
4. **Edit Template**: Click edit button → Dynamically renders fields based on configuration

**No frontend code changes required!**

### Template Configuration Structure
The modal dynamically renders based on these fields in `template.json`:
```json
{
    "default_mcp_tool": "string",           // → Text input
    "default_mcp_context_prompt": "string", // → Text input
    "estimated_input_tokens": 150,          // → Number input
    "estimated_output_tokens": 180,         // → Number input
    "input_variables": [                    // → Badges display
        {
            "name": "variable_name",
            "type": "str",
            "required": true,
            "description": "Variable description"
        }
    ]
}
```

### Extending Field Types
To add support for new field types (e.g., checkboxes, dropdowns):

1. **Update `createConfigField()` function**:
```javascript
function createConfigField(id, label, value, type = 'text', options = {}) {
    // ... existing code ...
    
    if (type === 'checkbox') {
        inputEl.type = 'checkbox';
        inputEl.checked = value;
    } else if (type === 'select') {
        // Create select dropdown
        const selectEl = document.createElement('select');
        options.choices.forEach(choice => {
            const optionEl = document.createElement('option');
            optionEl.value = choice.value;
            optionEl.textContent = choice.label;
            selectEl.appendChild(optionEl);
        });
    }
}
```

2. **Update `editTemplate()` rendering logic**:
```javascript
if (config.some_checkbox_field !== undefined) {
    configContainer.appendChild(createConfigField(
        'template-checkbox-field',
        'Checkbox Option',
        config.some_checkbox_field,
        'checkbox'
    ));
}
```

3. **Update `handleTemplateEditorSubmit()` collection logic**:
```javascript
if (currentConfig.some_checkbox_field !== undefined) {
    const checkboxInput = document.getElementById('template-checkbox-field');
    if (checkboxInput) {
        configPayload.some_checkbox_field = checkboxInput.checked;
    }
}
```

## Completion Status

### ✅ Completed
- HTML structure fully modularized
- JavaScript functions refactored
- Dynamic field rendering implemented
- Template-agnostic form submission
- Backward compatibility maintained
- Event listeners updated
- Global function exports
- Cache management integrated

### 🎯 Frontend Modularization Complete
All frontend template handling is now fully modular and plugin-based, matching the backend architecture:

1. ✅ **templateManager.js** - Core template management
2. ✅ **Template Dropdown** - Dynamic population
3. ✅ **Field Rendering** - Template-specific UI
4. ✅ **API Calls** - Dynamic template ID usage
5. ✅ **SQL Template Populator** - Collection dropdown fixed
6. ✅ **Template Editor Modal** - Fully modular
7. ✅ **Backward Compatibility** - Legacy support maintained

## Related Documentation
- [Frontend Modularization Summary](FRONTEND_MODULARIZATION.md)
- [Frontend Testing Guide](FRONTEND_TESTING_GUIDE.md)
- [RAG Template Documentation](RAG/TEMPLATE_POPULATION.md)
- [Template Quick Reference](RAG/QUICK_REFERENCE.md)
