/**
 * main.js
 * * This is the entry point for the application.
 * It initializes the application by setting up event listeners and loading initial data.
 */

// --- MODIFICATION START: Import UI functions ---
import { initializeEventListeners, finalizeConfiguration, loadCredentialsAndModels } from './eventHandlers.js';
import * as API from './api.js';
import * as DOM from './domElements.js';
import { state } from './state.js';
import { setupPanelToggle } from './utils.js';
// --- MODIFICATION START: Import UI functions correctly ---
import * as UI from './ui.js';
// --- MODIFICATION END ---
import { initializeVoiceRecognition } from './voice.js';

// --- MODIFICATION START: Add user UUID handling ---
function ensureUserUUID() {
    console.log("ensureUserUUID: Checking for existing UUID...");
    let userUUID = null;
    try {
        userUUID = localStorage.getItem('tdaUserUUID');
        if (userUUID) {
            console.log("ensureUserUUID: Found existing User UUID:", userUUID);
        } else {
            userUUID = crypto.randomUUID();
            console.log("ensureUserUUID: Generated New User UUID:", userUUID);
            localStorage.setItem('tdaUserUUID', userUUID);
            // Verify it was set
            const storedUUID = localStorage.getItem('tdaUserUUID');
            if (storedUUID === userUUID) {
                console.log("ensureUserUUID: Successfully stored new UUID.");
            } else {
                console.error("ensureUserUUID: Failed to store UUID in localStorage!");
                // Optionally alert the user or fallback to temporary UUID
                alert("Warning: Could not save user identifier. Session history may not persist correctly.");
            }
        }
    } catch (e) {
        console.error("ensureUserUUID: Error accessing localStorage:", e);
        // Fallback: Generate a temporary UUID if localStorage fails
        userUUID = userUUID || crypto.randomUUID(); // Use existing if generated before error
        console.warn("ensureUserUUID: Using temporary User UUID for this session:", userUUID);
        alert("Warning: Cannot access local storage. Session history will not persist across browser sessions.");
    }
    // Set the state regardless
    state.userUUID = userUUID;

    if (!state.userUUID) {
         console.error("FATAL: User UUID is null after ensureUserUUID!");
         alert("Fatal error: Could not establish user identifier.");
    }
}
// --- MODIFICATION END ---


document.addEventListener('DOMContentLoaded', async () => {
    // --- MODIFICATION START: Ensure UUID is set first ---
    ensureUserUUID(); // Get/Set the User UUID right away
    console.log("DOMContentLoaded: User UUID ensured:", state.userUUID);
    // --- MODIFICATION END ---

    // Initialize all event listeners first to ensure they are ready.
    initializeEventListeners();
    initializeVoiceRecognition();

    const promptEditorMenuItem = DOM.promptEditorButton.parentElement;
    promptEditorMenuItem.style.display = 'none';

    try {
        const res = await fetch('/app-config');
        state.appConfig = await res.json();
        console.log('License Info:', state.appConfig.license_info);

        await API.checkAndUpdateDefaultPrompts();

        const chartingIntensityContainer = document.getElementById('charting-intensity-container');
        if (!state.appConfig.charting_enabled) {
            chartingIntensityContainer.style.display = 'none';
        } else {
            DOM.chartingIntensitySelect.value = state.appConfig.default_charting_intensity || 'medium';
        }

        if (state.appConfig.voice_conversation_enabled) {
            DOM.voiceInputButton.classList.remove('hidden');
            DOM.keyObservationsToggleButton.classList.remove('hidden');
        }

    } catch (e) {
        console.error("Could not fetch app config", e);
    }

    // --- MODIFICATION START: Adjust Startup Logic ---
    try {
        console.log("DEBUG: Checking server status on startup...");
        const status = await API.checkServerStatus();

        if (status.isConfigured) {
            console.log("DEBUG: Server is already configured. Proceeding with setup.", status);

            DOM.llmProviderSelect.value = status.provider;
            DOM.mcpServerNameInput.value = status.mcp_server.name;

            await loadCredentialsAndModels(); // Load credentials/models based on provider

            // Ensure the model from status actually exists in the dropdown before selecting
            const modelExists = Array.from(DOM.llmModelSelect.options).some(opt => opt.value === status.model);
            if (modelExists) {
                DOM.llmModelSelect.value = status.model;
            } else {
                console.warn(`DEBUG: Model '${status.model}' from server status not found in dropdown. Model list might be outdated or model unavailable.`);
                // Optionally select the first available model or leave as default
            }


            const currentConfig = { provider: status.provider, model: status.model };
            await finalizeConfiguration(currentConfig); // This sets up MCP client etc.

            // --- Load Sessions AFTER finalizeConfiguration ---
            console.log("DEBUG: Configuration finalized. Session loading is handled by finalizeConfiguration.");
            // --- MODIFICATION START: Removed redundant session loading ---
            // This logic is now inside finalizeConfiguration()
            // --- MODIFICATION END ---
             // --- END Load Sessions ---

        } else {
            console.log("DEBUG: Server is not configured. Pre-filling and showing config modal.");
            // Pre-fill config modal (remains the same)
            const savedMcpConfig = JSON.parse(localStorage.getItem('mcpConfig'));
            if (savedMcpConfig) {
                DOM.mcpServerNameInput.value = savedMcpConfig.server_name || 'teradata_mcp_server';
                document.getElementById('mcp-host').value = savedMcpConfig.host || '127.0.0.1';
                document.getElementById('mcp-port').value = savedMcpConfig.port || '8001';
                document.getElementById('mcp-path').value = savedMcpConfig.path || '/mcp/';
            } else {
                DOM.mcpServerNameInput.value = 'teradata_mcp_server';
                document.getElementById('mcp-host').value = '127.0.0.1';
                document.getElementById('mcp-port').value = '8001';
                document.getElementById('mcp-path').value = '/mcp/';
            }
            const savedTtsCreds = localStorage.getItem('ttsCredentialsJson');
            if (savedTtsCreds) {
                DOM.ttsCredentialsJsonTextarea.value = savedTtsCreds;
            }
            const lastProvider = localStorage.getItem('lastSelectedProvider');
            if (lastProvider) {
                DOM.llmProviderSelect.value = lastProvider;
            }
            await loadCredentialsAndModels(); // Load potential credentials/models
            DOM.configMenuButton.click(); // Open the config modal
        }
    } catch (startupError) {
        console.error("DEBUG: Error during startup configuration/session loading. Showing config modal.", startupError);
        // Attempt to pre-fill and show config modal as fallback
        try {
            const savedMcpConfig = JSON.parse(localStorage.getItem('mcpConfig'));
             if (savedMcpConfig) { /* ... pre-fill MCP ... */ } else { /* ... default MCP ... */ }
             const savedTtsCreds = localStorage.getItem('ttsCredentialsJson');
             if (savedTtsCreds) { /* ... pre-fill TTS ... */ }
             const lastProvider = localStorage.getItem('lastSelectedProvider');
             if (lastProvider) { DOM.llmProviderSelect.value = lastProvider; }
             await loadCredentialsAndModels();
        } catch (prefillError) {
            console.error("DEBUG: Error during fallback pre-fill:", prefillError);
        }
        DOM.configMenuButton.click(); // Show config modal
    }
    // --- MODIFICATION END ---


    DOM.toggleHistoryCheckbox.checked = !DOM.sessionHistoryPanel.classList.contains('collapsed');
    setupPanelToggle(DOM.toggleHistoryButton, DOM.sessionHistoryPanel, DOM.toggleHistoryCheckbox, DOM.historyCollapseIcon, DOM.historyExpandIcon);

    DOM.toggleHeaderCheckbox.checked = !DOM.toolHeader.classList.contains('collapsed');
    setupPanelToggle(DOM.toggleHeaderButton, DOM.toolHeader, DOM.toggleHeaderCheckbox, DOM.headerCollapseIcon, DOM.headerExpandIcon);

    DOM.toggleStatusCheckbox.checked = !DOM.statusWindow.classList.contains('collapsed');
    setupPanelToggle(DOM.toggleStatusButton, DOM.statusWindow, DOM.toggleStatusCheckbox, DOM.statusCollapseIcon, DOM.statusExpandIcon);

    const savedKeyObservationsMode = localStorage.getItem('keyObservationsMode');
    if (['autoplay-off', 'autoplay-on', 'off'].includes(savedKeyObservationsMode)) {
        state.keyObservationsMode = savedKeyObservationsMode;
    }

    UI.updateHintAndIndicatorState();
    UI.updateVoiceModeUI();
    UI.updateKeyObservationsModeUI();
});
