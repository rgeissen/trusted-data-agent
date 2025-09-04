/**
 * main.js
 * * This is the entry point for the application.
 * It initializes the application by setting up event listeners and loading initial data.
 */

import { initializeEventListeners } from './eventHandlers.js';
import { fetchModels } from './api.js';
import * as DOM from './domElements.js';
import { state } from './state.js';
import { checkAndUpdateDefaultPrompts } from './api.js';
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

        await checkAndUpdateDefaultPrompts();

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

    // --- MODIFICATION START: Load saved TTS credentials from local storage ---
    const savedTtsCreds = localStorage.getItem('ttsCredentialsJson');
    if (savedTtsCreds) {
        DOM.ttsCredentialsJsonTextarea.value = savedTtsCreds;
    }
    // --- MODIFICATION END ---

    const lastProvider = localStorage.getItem('lastSelectedProvider');
    if (lastProvider) {
        DOM.llmProviderSelect.value = lastProvider;
    }
    DOM.llmProviderSelect.dispatchEvent(new Event('change'));

    DOM.toggleHistoryCheckbox.checked = !DOM.sessionHistoryPanel.classList.contains('collapsed');
    setupPanelToggle(DOM.toggleHistoryButton, DOM.sessionHistoryPanel, DOM.toggleHistoryCheckbox, DOM.historyCollapseIcon, DOM.historyExpandIcon);

    DOM.toggleHeaderCheckbox.checked = !DOM.toolHeader.classList.contains('collapsed');
    setupPanelToggle(DOM.toggleHeaderButton, DOM.toolHeader, DOM.toggleHeaderCheckbox, DOM.headerCollapseIcon, DOM.headerExpandIcon);

    DOM.toggleStatusCheckbox.checked = !DOM.statusWindow.classList.contains('collapsed');
    setupPanelToggle(DOM.toggleStatusButton, DOM.statusWindow, DOM.toggleStatusCheckbox, DOM.statusCollapseIcon, DOM.statusExpandIcon);

    // Now that listeners are attached, we can programmatically click the button to show the modal on load.
    DOM.configMenuButton.click();

    if (DOM.llmApiKeyInput.value || DOM.awsAccessKeyIdInput.value || DOM.ollamaHostInput.value) {
        await fetchModels();
    }
    
    const savedKeyObservationsMode = localStorage.getItem('keyObservationsMode');
    if (['autoplay-off', 'autoplay-on', 'off'].includes(savedKeyObservationsMode)) {
        state.keyObservationsMode = savedKeyObservationsMode;
    }

    updateHintAndIndicatorState();
    updateVoiceModeUI();
    updateKeyObservationsModeUI();
});
