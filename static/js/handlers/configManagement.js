/**
 * handlers/configManagement.js
 * * This module handles all logic related to the Configuration modal
 * and the System Prompt Editor.
 */

import * as DOM from '../domElements.js';
import { state } from '../state.js';
import * as API from '../api.js';
import * as UI from '../ui.js';
import * as Utils from '../utils.js';
import { handleLoadSession, handleStartNewSession } from './sessionManagement.js';
// We need to import from eventHandlers for functions not yet moved
import { handleLoadResources, openSystemPromptPopup } from '../eventHandlers.js';
import { handleViewSwitch } from '../ui.js';

/**
 * Gets the current core configuration from the form.
 * @returns {object} The configuration object.
 */
function getCurrentCoreConfig() {
    const formData = new FormData(DOM.configForm);
    return Object.fromEntries(formData.entries());
}

/**
 * Handles request to close the config modal, checking for changes.
 */
// export function handleCloseConfigModalRequest() {
//     const coreChanged = JSON.stringify(getCurrentCoreConfig()) !== JSON.stringify(state.pristineConfig);
//     if (coreChanged) {
//         UI.showConfirmation('Discard Changes?', 'You have unsaved changes in your configuration. Are you sure you want to close?', UI.closeConfigModal);
//     } else {
//         UI.closeConfigModal();
//     }
// }

/**
 * Handles click on the main config modal action button (Connect/Close).
 * @param {Event} e - The click event.
 */
// export function handleConfigActionButtonClick(e) {
//     if (e.currentTarget.type === 'button') {
//         handleCloseConfigModalRequest();
//     }
// }

/**
 * Finalizes the application configuration after a successful connection.
 * Loads resources, sessions, and sets UI state.
 * @param {object} config - The configuration object from the form.
 */
export async function finalizeConfiguration(config, switchToConversationView = true) {
    DOM.configStatus.textContent = 'Success! MCP & LLM services connected.';
    DOM.configStatus.className = 'text-sm text-green-400 text-center';
    DOM.mcpStatusDot.classList.remove('disconnected');
    DOM.mcpStatusDot.classList.add('connected');
    DOM.llmStatusDot.classList.remove('disconnected', 'busy');
    DOM.llmStatusDot.classList.add('idle'); // Start as idle
    DOM.contextStatusDot.classList.remove('disconnected');
    DOM.contextStatusDot.classList.add('idle');

    localStorage.setItem('lastSelectedProvider', config.provider);

    state.currentProvider = config.provider;
    state.currentModel = config.model;

    UI.updateStatusPromptName(config.provider, config.model);

    if (Utils.isPrivilegedUser()) {
        const activePrompt = Utils.getSystemPromptForModel(state.currentProvider, state.currentModel);
        if (!activePrompt) {
            await resetSystemPrompt(true);
        }
    }

    const promptEditorMenuItem = DOM.promptEditorButton.parentElement;
    if (Utils.isPrivilegedUser()) {
        promptEditorMenuItem.style.display = 'block';
        DOM.promptEditorButton.disabled = false;
    } else {
        promptEditorMenuItem.style.display = 'none';
        DOM.promptEditorButton.disabled = true;
    }

    await Promise.all([
        handleLoadResources('tools'),
        handleLoadResources('prompts'),
        handleLoadResources('resources')
    ]);

    const currentSessionId = state.currentSessionId;

    try {
        const sessions = await API.loadAllSessions();
        DOM.sessionList.innerHTML = '';
        if (sessions && Array.isArray(sessions) && sessions.length > 0) {
            sessions.forEach((session) => {
                const isActive = session.id === currentSessionId;
                const sessionItem = UI.addSessionToList(session, isActive);
                DOM.sessionList.appendChild(sessionItem);
            });
            // If the previously active session still exists, ensure it is loaded.
            // Otherwise, load the most recent session.
            const sessionToLoad = sessions.find(s => s.id === currentSessionId) ? currentSessionId : sessions[0].id;
            await handleLoadSession(sessionToLoad);
        } else {
            // No sessions exist, create a new one
            await handleStartNewSession();
        }
    } catch (sessionError) {
        console.error("Error loading previous sessions:", sessionError);
        DOM.sessionList.innerHTML = '<li class="text-red-400 p-2">Error loading sessions</li>';
        // Fallback to creating a new session if loading fails
        await handleStartNewSession();
    }

    DOM.chatModalButton.disabled = false;
    DOM.userInput.placeholder = "Ask about databases, tables, users...";
    UI.setExecutionState(false);

    state.pristineConfig = getCurrentCoreConfig();
    UI.updateConfigButtonState();
    if (state.showWelcomeScreenAtStartup) {
        openSystemPromptPopup();
    }

    // setTimeout(UI.closeConfigModal, 1000); // REMOVED
    // DOM.unconfiguredWrapper.classList.add('hidden'); // REMOVED
    // DOM.configuredWrapper.classList.remove('hidden'); // REMOVED
    if (switchToConversationView) {
        handleViewSwitch('conversation-view'); // Set the default view
    }
}

/**
 * Handles the submission of the main configuration form.
 * @param {Event} e - The submit event.
 */
export async function handleConfigFormSubmit(e) {
    e.preventDefault();
    await API.checkAndUpdateDefaultPrompts();

    const selectedModel = DOM.llmModelSelect.value;
    if (!selectedModel) {
        DOM.configStatus.textContent = 'Please select your LLM Model.';
        DOM.configStatus.className = 'text-sm text-red-400 text-center';
        return;
    }

    DOM.configLoadingSpinner.classList.remove('hidden');
    DOM.configActionButton.disabled = true;
    DOM.configStatus.textContent = 'Connecting to MCP & LLM...';
    DOM.configStatus.className = 'text-sm text-yellow-400 text-center';

    const formData = new FormData(e.target);
    const config = Object.fromEntries(formData.entries());

    const mcpConfig = { server_name: config.server_name, host: config.host, port: config.port, path: config.path };
    localStorage.setItem('mcpConfig', JSON.stringify(mcpConfig));

    if (config.provider === 'Amazon') {
        const awsCreds = { aws_access_key_id: config.aws_access_key_id, aws_secret_access_key: config.aws_secret_access_key, aws_region: config.aws_region };
        localStorage.setItem('amazonApiKey', JSON.stringify(awsCreds));
    } else if (config.provider === 'Ollama') {
        localStorage.setItem('ollamaHost', config.ollama_host);
    } else if (config.provider === 'Azure') {
        const azureCreds = {
            azure_api_key: config.azure_api_key,
            azure_endpoint: config.azure_endpoint,
            azure_deployment_name: config.azure_deployment_name,
            azure_api_version: config.azure_api_version
        };
        localStorage.setItem('azureApiKey', JSON.stringify(azureCreds));
    } else if (config.provider === 'Friendli') {
        const friendliCreds = {
            friendli_token: config.friendli_token,
            friendli_endpoint_url: config.friendli_endpoint_url
        };
        localStorage.setItem('friendliApiKey', JSON.stringify(friendliCreds));
    } else {
        localStorage.setItem(`${config.provider.toLowerCase()}ApiKey`, config.apiKey);
    }

    if (config.tts_credentials_json) {
        localStorage.setItem('ttsCredentialsJson', config.tts_credentials_json);
    }

    try {
        const res = await fetch('/configure', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        const result = await res.json();

        if (res.ok) {
            await finalizeConfiguration(config, false);
        } else {
            throw new Error(result.message || 'An unknown configuration error occurred.');
        }
    } catch (error) {
        DOM.configStatus.textContent = `Error: ${error.message}`;
        DOM.configStatus.className = 'text-sm text-red-400 text-center';
        DOM.promptEditorButton.disabled = true;
        DOM.chatModalButton.disabled = true;
        DOM.mcpStatusDot.classList.add('disconnected');
        DOM.mcpStatusDot.classList.remove('connected');
        DOM.llmStatusDot.classList.add('disconnected');
        DOM.llmStatusDot.classList.remove('connected', 'idle');
        DOM.contextStatusDot.classList.add('disconnected');
        DOM.contextStatusDot.classList.remove('idle', 'context-active');
    } finally {
        DOM.configLoadingSpinner.classList.add('hidden');
        DOM.configActionButton.disabled = false;
        UI.updateConfigButtonState();
    }
}

/**
 * Loads saved credentials and fetches models for the selected provider.
 */
export async function loadCredentialsAndModels() {
    const newProvider = DOM.llmProviderSelect.value;

    DOM.apiKeyContainer.classList.add('hidden');
    DOM.awsCredentialsContainer.classList.add('hidden');
    DOM.awsListingMethodContainer.classList.add('hidden');
    DOM.ollamaHostContainer.classList.add('hidden');
    DOM.azureCredentialsContainer.classList.add('hidden');
    DOM.friendliCredentialsContainer.classList.add('hidden');

    if (newProvider === 'Amazon') {
        DOM.awsCredentialsContainer.classList.remove('hidden');
        DOM.awsListingMethodContainer.classList.remove('hidden');
        const envCreds = await API.getApiKey('amazon');
        const savedCreds = JSON.parse(localStorage.getItem('amazonApiKey')) || {};
        DOM.awsAccessKeyIdInput.value = envCreds.aws_access_key_id || savedCreds.aws_access_key_id || '';
        DOM.awsSecretAccessKeyInput.value = envCreds.aws_secret_access_key || savedCreds.aws_secret_access_key || '';
        DOM.awsRegionInput.value = envCreds.aws_region || savedCreds.aws_region || '';
    } else if (newProvider === 'Ollama') {
        DOM.ollamaHostContainer.classList.remove('hidden');
        const data = await API.getApiKey('ollama');
        DOM.ollamaHostInput.value = data.host || localStorage.getItem('ollamaHost') || 'http://localhost:11434';
    } else if (newProvider === 'Azure') {
        DOM.azureCredentialsContainer.classList.remove('hidden');
        const envCreds = await API.getApiKey('azure');
        const savedCreds = JSON.parse(localStorage.getItem('azureApiKey')) || {};
        DOM.azureApiKeyInput.value = envCreds.azure_api_key || savedCreds.azure_api_key || '';
        DOM.azureEndpointInput.value = envCreds.azure_endpoint || savedCreds.azure_endpoint || '';
        DOM.azureDeploymentNameInput.value = envCreds.azure_deployment_name || savedCreds.azure_deployment_name || '';
        DOM.azureApiVersionInput.value = envCreds.azure_api_version || savedCreds.azure_api_version || '2024-02-01';
    } else if (newProvider === 'Friendli') {
        DOM.friendliCredentialsContainer.classList.remove('hidden');
        const envCreds = await API.getApiKey('friendli');
        const savedCreds = JSON.parse(localStorage.getItem('friendliApiKey')) || {};
        DOM.friendliTokenInput.value = envCreds.friendli_token || savedCreds.friendli_token || '';
        DOM.friendliEndpointUrlInput.value = envCreds.friendli_endpoint_url || savedCreds.friendli_endpoint_url || '';
    } else {
        DOM.apiKeyContainer.classList.remove('hidden');
        const data = await API.getApiKey(newProvider);
        DOM.llmApiKeyInput.value = data.apiKey || localStorage.getItem(`${newProvider.toLowerCase()}ApiKey`) || '';
    }

    await handleRefreshModelsClick();
}

/**
 * Handles the change event for the LLM provider dropdown.
 */
export async function handleProviderChange() {
    DOM.llmModelSelect.innerHTML = '<option value="">-- Select Provider & Enter Credentials --</option>';
    DOM.configStatus.textContent = '';

    await loadCredentialsAndModels();
}

/**
 * Handles the change event for the LLM model dropdown.
 */
export async function handleModelChange() {
    state.currentModel = DOM.llmModelSelect.value;
    state.currentProvider = DOM.llmProviderSelect.value;
    if (!state.currentModel || !state.currentProvider) return;

    if (Utils.isPrivilegedUser()) {
        const activePrompt = Utils.getSystemPromptForModel(state.currentProvider, state.currentModel);
        if (!activePrompt) {
            DOM.configStatus.textContent = `Fetching default prompt for ${Utils.getNormalizedModelId(state.currentModel)}...`;
            DOM.configStatus.className = 'text-sm text-gray-400 text-center';
            await resetSystemPrompt(true);
            DOM.configStatus.textContent = `Default prompt for ${Utils.getNormalizedModelId(state.currentModel)} loaded.`;
            setTimeout(() => { DOM.configStatus.textContent = ''; }, 2000);
        }
    }
}

/**
 * Handles the click event for the "Refresh Models" button.
 */
export async function handleRefreshModelsClick() {
    DOM.refreshIcon.classList.add('hidden');
    DOM.refreshSpinner.classList.remove('hidden');
    DOM.refreshModelsButton.disabled = true;
    DOM.configStatus.textContent = 'Fetching models...';
    DOM.configStatus.className = 'text-sm text-gray-400 text-center';
    try {
        const result = await API.fetchModels();
        DOM.llmModelSelect.innerHTML = '';
        result.models.forEach(model => {
            const option = document.createElement('option');
            option.value = model.name;
            option.textContent = model.name + (model.certified ? '' : ' (support evaluated)');
            option.disabled = !model.certified;
            DOM.llmModelSelect.appendChild(option);
        });
        DOM.configStatus.textContent = `Successfully fetched ${result.models.length} models.`;
        DOM.configStatus.className = 'text-sm text-green-400 text-center';
        if (DOM.llmModelSelect.value) {
            await handleModelChange();
        }
    } catch (error) {
        DOM.configStatus.textContent = `Error: ${error.message}`;
        DOM.configStatus.className = 'text-sm text-red-400 text-center';
        DOM.llmModelSelect.innerHTML = '<option value="">-- Could not fetch models --</option>';
    } finally {
        DOM.refreshIcon.classList.remove('hidden');
        DOM.refreshSpinner.classList.add('hidden');
        DOM.refreshModelsButton.disabled = false;
    }
}

/**
 * Opens the System Prompt Editor modal.
 */
export function openPromptEditor() {
    DOM.promptEditorTitle.innerHTML = `System Prompt Editor for: <code class="text-teradata-orange font-normal">${state.currentProvider} / ${Utils.getNormalizedModelId(state.currentModel)}</code>`;
    const promptText = Utils.getSystemPromptForModel(state.currentProvider, state.currentModel);
    DOM.promptEditorTextarea.value = promptText;
    DOM.promptEditorTextarea.dataset.initialValue = promptText;

    DOM.promptEditorOverlay.classList.remove('hidden', 'opacity-0');
    DOM.promptEditorContent.classList.remove('scale-95', 'opacity-0');
    UI.updatePromptEditorState();
}

/**
 * Force-closes the System Prompt Editor modal without checking for changes.
 */
export function forceClosePromptEditor() {
    DOM.promptEditorOverlay.classList.add('opacity-0');
    DOM.promptEditorContent.classList.add('scale-95', 'opacity-0');
    setTimeout(() => {
        DOM.promptEditorOverlay.classList.add('hidden');
        DOM.promptEditorStatus.textContent = '';
    }, 300);
}

/**
 * Handles request to close the System Prompt Editor, checking for unsaved changes.
 */
export function closePromptEditor() {
    const hasChanged = DOM.promptEditorTextarea.value.trim() !== DOM.promptEditorTextarea.dataset.initialValue.trim();
    if (hasChanged) {
        UI.showConfirmation(
            'Discard Changes?',
            'You have unsaved changes that will be lost. Are you sure you want to close the editor?',
            forceClosePromptEditor
        );
    } else {
        forceClosePromptEditor();
    }
}

/**
 * Saves changes made in the System Prompt Editor.
 */
export async function saveSystemPromptChanges() {
    const newPromptText = DOM.promptEditorTextarea.value;
    const defaultPromptText = await Utils.getDefaultSystemPrompt(state.currentProvider, state.currentModel);

    if (defaultPromptText === null) {
        return;
    }

    const isCustom = newPromptText.trim() !== defaultPromptText.trim();

    Utils.saveSystemPromptForModel(state.currentProvider, state.currentModel, newPromptText, isCustom);
    UI.updateStatusPromptName();

    DOM.promptEditorTextarea.dataset.initialValue = newPromptText;

    DOM.promptEditorStatus.textContent = 'Saved!';
    DOM.promptEditorStatus.className = 'text-sm text-green-400';
    setTimeout(() => {
        UI.updatePromptEditorState();
    }, 2000);
}

/**
 * Resets the System Prompt to its default value.
 * @param {boolean} [force=false] - If true, saves the reset without confirmation.
 */
export async function resetSystemPrompt(force = false) {
    const defaultPrompt = await Utils.getDefaultSystemPrompt(state.currentProvider, state.currentModel);
    if (defaultPrompt) {
        if (!force) {
            DOM.promptEditorTextarea.value = defaultPrompt;
            UI.updatePromptEditorState();
        } else {
            Utils.saveSystemPromptForModel(state.currentProvider, state.currentModel, defaultPrompt, false);
            DOM.promptEditorTextarea.value = defaultPrompt;
            UI.updateStatusPromptName();
        }
    }
}

/**
 * Handles changes to the charting intensity dropdown.
 */
export async function handleIntensityChange() {
    if (Utils.isPromptCustomForModel(state.currentProvider, state.currentModel)) {
        UI.showConfirmation(
            'Reset System Prompt?',
            'Changing the charting intensity requires resetting the system prompt to a new default to include updated instructions. Your custom changes will be lost. Do you want to continue?',
            () => {
                resetSystemPrompt(true);
                DOM.configStatus.textContent = 'Charting intensity updated and system prompt was reset to default.';
                DOM.configStatus.className = 'text-sm text-yellow-400 text-center';
            }
        );
    } else {
        await resetSystemPrompt(true);
        DOM.configStatus.textContent = 'Charting intensity updated.';
        DOM.configStatus.className = 'text-sm text-green-400 text-center';
    }
}