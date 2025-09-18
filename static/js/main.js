/**
 * main.js
 * * This is the entry point for the application.
 * It initializes the application by setting up event listeners and loading initial data.
 */

// --- MODIFICATION START: Correct the API import to use a namespace ---
import { initializeEventListeners, finalizeConfiguration, loadCredentialsAndModels } from './eventHandlers.js';
import * as API from './api.js';
// --- MODIFICATION END ---
import * as DOM from './domElements.js';
import { state } from './state.js';
import { setupPanelToggle } from './utils.js';
import { updateHintAndIndicatorState, updateVoiceModeUI, updateKeyObservationsModeUI } from './ui.js';
import { initializeVoiceRecognition } from './voice.js';

document.addEventListener('DOMContentLoaded', async () => {
    // Initialize all event listeners first to ensure they are ready.
    initializeEventListeners();
    initializeVoiceRecognition();

    const promptEditorMenuItem = DOM.promptEditorButton.parentElement;
    promptEditorMenuItem.style.display = 'none';

    try {
        const res = await fetch('/app-config');
        state.appConfig = await res.json();
        console.log('License Info:', state.appConfig.license_info);

        // --- MODIFICATION START: Use the correct namespace for the imported function ---
        await API.checkAndUpdateDefaultPrompts();
        // --- MODIFICATION END ---

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

    try {
        console.log("DEBUG: Checking server status on startup...");
        const status = await API.checkServerStatus();

        if (status.isConfigured) {
            console.log("DEBUG: Server is already configured. Bypassing modal and finalizing setup.", status);

            DOM.llmProviderSelect.value = status.provider;
            DOM.mcpServerNameInput.value = status.mcp_server.name;

            await loadCredentialsAndModels();
            
            DOM.llmModelSelect.value = status.model;

            const currentConfig = { provider: status.provider, model: status.model };
            await finalizeConfiguration(currentConfig);

        } else {
            console.log("DEBUG: Server is not configured. Proceeding to show config modal.");
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

            await loadCredentialsAndModels();

            DOM.configMenuButton.click();
        }
    } catch (error) {
        console.error("DEBUG: Failed to check server status on startup. Showing config modal as a fallback.", error);
        DOM.configMenuButton.click();
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

    updateHintAndIndicatorState();
    updateVoiceModeUI();
    updateKeyObservationsModeUI();
});

