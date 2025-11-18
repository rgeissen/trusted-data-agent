/**
 * main.js
 * * This is the entry point for the application.
 * It initializes the application by setting up event listeners and loading initial data.
 */

import { initializeEventListeners } from './eventHandlers.js';
import { finalizeConfiguration } from './handlers/configManagement.js';
import { initializeConfigurationUI } from './handlers/configurationHandler.js';
import * as API from './api.js';
import * as DOM from './domElements.js';
import { state } from './state.js';
import { setupPanelToggle } from './utils.js';
import * as UI from './ui.js';
import { handleViewSwitch } from './ui.js';
import { initializeVoiceRecognition } from './voice.js';
import { subscribeToNotifications } from './notifications.js';

/**
 * Ensures a user UUID exists in localStorage and application state.
 * Generates a new UUID if one is not found.
 */
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

// REMOVED: loadInitialConfig() function - obsolete with new configuration system
// The new configuration system (configState) automatically loads from localStorage
// and doesn't need manual form population

document.addEventListener('DOMContentLoaded', async () => {
    const savedShowWelcomeScreen = localStorage.getItem('showWelcomeScreenAtStartup');
    state.showWelcomeScreenAtStartup = savedShowWelcomeScreen === null ? true : savedShowWelcomeScreen === 'true';
    const welcomeScreenCheckbox = document.getElementById('toggle-welcome-screen-checkbox');
    const welcomeScreenPopupCheckbox = document.getElementById('welcome-screen-show-at-startup-checkbox');
    if (welcomeScreenCheckbox) {
        welcomeScreenCheckbox.checked = state.showWelcomeScreenAtStartup;
    }
    if (welcomeScreenPopupCheckbox) {
        welcomeScreenPopupCheckbox.checked = state.showWelcomeScreenAtStartup;
    }

    ensureUserUUID(); // Get/Set the User UUID right away
    console.log("DOMContentLoaded: User UUID ensured:", state.userUUID);
    subscribeToNotifications();

    const uuidInput = document.getElementById('tda-user-uuid');
    const copyButton = document.getElementById('copy-uuid-button');

    if (uuidInput) {
        uuidInput.value = state.userUUID;
    }

    if (copyButton) {
        copyButton.addEventListener('click', () => {
            uuidInput.select();
            document.execCommand('copy');
            const originalTitle = copyButton.title;
            copyButton.title = 'Copied!';
            setTimeout(() => {
                copyButton.title = originalTitle;
            }, 2000);
        });
    }

    // REMOVED: loadInitialConfig() - obsolete with new configuration system
    // The new configuration system uses configState which loads from localStorage automatically

    // Initialize all event listeners first to ensure they are ready.
    initializeEventListeners();
    initializeVoiceRecognition();

    // Initialize new configuration UI
    initializeConfigurationUI();

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

        if (DOM.ragStatusDot && !state.appConfig.rag_enabled) {
            DOM.ragStatusDot.parentElement.style.display = 'none';
        }

    } catch (e) {
        console.error("Could not fetch app config", e);
    }

    try {
        console.log("DEBUG: Checking server status on startup...");
        const status = await API.checkServerStatus();

        if (status.isConfigured) {
            console.log("DEBUG: Server is already configured. Proceeding with setup.", status);

            // NOTE: With new config UI, we don't need to pre-fill old form fields
            // The configurationHandler manages its own state via localStorage
            
            // Old code removed:
            // DOM.llmProviderSelect.value = status.provider;
            // DOM.mcpServerNameInput.value = status.mcp_server.name;
            // await loadCredentialsAndModels();

            const currentConfig = { provider: status.provider, model: status.model };
            // Pass the mcp_server details from status to ensure they are used if re-finalizing
            currentConfig.mcp_server = status.mcp_server;
            await finalizeConfiguration(currentConfig, true);

            console.log("DEBUG: Configuration finalized. Session loading is handled by finalizeConfiguration.");

            // handleViewSwitch is now called inside finalizeConfiguration


        } else {
            console.log("DEBUG: Server is not configured. Showing config modal.");
            // The new configuration UI handles its own state
            // No need to pre-fill old form fields
            const savedTtsCreds = localStorage.getItem('ttsCredentialsJson');
            if (savedTtsCreds && DOM.ttsCredentialsJsonTextarea) {
                DOM.ttsCredentialsJsonTextarea.value = savedTtsCreds;
            }
            
            // NOTE: Old loadCredentialsAndModels() is not needed with new config UI
            // The new configurationHandler manages everything via localStorage
            
            handleViewSwitch('credentials-view');
        }
    } catch (startupError) {
        console.error("DEBUG: Error during startup configuration/session loading. Showing config modal.", startupError);
        // Fallback to showing credentials view
        try {
             const savedTtsCreds = localStorage.getItem('ttsCredentialsJson');
             if (savedTtsCreds && DOM.ttsCredentialsJsonTextarea) { 
                 DOM.ttsCredentialsJsonTextarea.value = savedTtsCreds; 
             }
             // NOTE: Old loadCredentialsAndModels() removed - new config UI handles this
        } catch (prefillError) {
            console.error("DEBUG: Error during fallback pre-fill:", prefillError);
        }
        
        handleViewSwitch('credentials-view');
    }


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
    
    // This buggy line was unconditionally overriding the logic in the try/catch block.
    // handleViewSwitch('conversation-view'); // - REMOVED
});