/**
 * api.js
 * * This module handles all interactions with the backend server.
 * It encapsulates all `fetch` calls and the logic for handling API requests and responses.
 */

import * as DOM from './domElements.js';
import { state } from './state.js';
import { getSystemPromptForModel, isPrivilegedUser } from './utils.js';


export async function checkServerStatus() {
    const res = await fetch('/api/status');
    if (!res.ok) {
        // If the endpoint fails, it's safer to assume not configured.
        return { isConfigured: false };
    }
    return await res.json();
}

// --- MODIFICATION START: Add the missing getApiKey helper function to centralize this logic ---
/**
 * Fetches API keys from the backend /api_key/ endpoint.
 * @param {string} provider The name of the LLM provider.
 * @returns {Promise<object>} A promise that resolves to the credentials object.
 */
export async function getApiKey(provider) {
    const res = await fetch(`/api_key/${provider.toLowerCase()}`);
    if (!res.ok) {
        throw new Error(`Failed to fetch API key for ${provider}`);
    }
    return await res.json();
}
// --- MODIFICATION END ---


export async function startStream(endpoint, body) {
    const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `Request failed with status ${response.status}`);
    }
    return response;
}

export async function synthesizeText(text) {
    console.log("AUDIO DEBUG: synthesizeText called with text:", `"${text.substring(0,100)}..."`);
    if (!state.appConfig.voice_conversation_enabled) {
        console.log("AUDIO DEBUG: Voice feature is disabled in app config. Skipping synthesis.");
        return null;
    }
    const response = await fetch('/api/synthesize-speech', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
    });

    if (response.ok) {
        console.log("AUDIO DEBUG: Synthesis API call successful.");
        return await response.blob();
    } else {
        const errorData = await response.json();
        console.error('AUDIO DEBUG: Speech synthesis API call failed:', errorData.error);
        return null;
    }
}


export async function checkAndUpdateDefaultPrompts() {
    if (!isPrivilegedUser()) {
        console.log("Standard user tier. Skipping client-side prompt cache check.");
        localStorage.removeItem('userSystemPrompts'); 
        return;
    }

    try {
        const res = await fetch('/api/prompts-version');
        if (!res.ok) {
            console.error('Could not fetch prompt version from server.');
            return;
        }
        const data = await res.json();
        const serverVersion = data.version;

        if (!serverVersion) {
            console.error('Server did not return a valid prompt version.');
            return;
        }

        const localVersion = localStorage.getItem('promptVersionHash');

        if (serverVersion !== localVersion) {
            console.log('New master system prompts detected on server. Flushing non-custom local prompts.');
            
            const allPrompts = getSystemPrompts();
            const updatedPrompts = {};

            for (const key in allPrompts) {
                if (allPrompts[key].isCustom === true) {
                    updatedPrompts[key] = allPrompts[key];
                }
            }

            localStorage.setItem('userSystemPrompts', JSON.stringify(updatedPrompts));
        } else {
             console.log('Local prompt cache is up to date.');
        }

        localStorage.setItem('promptVersionHash', serverVersion);

    } catch (e) {
        console.error('Error checking for prompt updates:', e);
    }
}

export async function togglePromptApi(promptName, isDisabled) {
    const res = await fetch('/prompt/toggle_status', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: promptName, disabled: isDisabled })
    });
    if (!res.ok) {
        throw new Error('Server responded with an error.');
    }
}

export async function toggleToolApi(toolName, isDisabled) {
    const res = await fetch('/tool/toggle_status', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: toolName, disabled: isDisabled })
    });
    if (!res.ok) {
        throw new Error('Server responded with an error.');
    }
}

export async function loadResources(type) {
    const res = await fetch(`/${type}`);
    
    if (res.status === 404) {
        return {};
    }

    const data = await res.json();
    if (!res.ok) {
        throw new Error(data.error || `Failed to load ${type}`);
    }
    return data;
}

export async function startNewSession() {
    const payload = {
        charting_intensity: DOM.chartingIntensitySelect.value
    };

    if (isPrivilegedUser()) {
        const activePrompt = getSystemPromptForModel(state.currentProvider, state.currentModel);
        if (!activePrompt) {
            throw new Error('Cannot start a new session. The system prompt is not loaded for the current model. Please re-configure.');
        }
        payload.system_prompt = activePrompt;
    }

    const res = await fetch('/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) {
        throw new Error(data.error || "Failed to get a session ID.");
    }
    return data;
}

export async function loadSession(sessionId) {
    const res = await fetch(`/session/${sessionId}`);
    const data = await res.json();
    if (!res.ok) {
        throw new Error(data.error || "Failed to load session.");
    }
    return data;
}

export async function loadAllSessions() {
    const res = await fetch('/sessions');
    const sessions = await res.json();
    if (!res.ok) {
        throw new Error(sessions.error || "Could not retrieve past sessions.");
    }
    return sessions;
}

export async function fetchModels() {
    const provider = DOM.llmProviderSelect.value;
    let body = { provider };

    if (provider === 'Amazon') {
        body.aws_access_key_id = DOM.awsAccessKeyIdInput.value;
        body.aws_secret_access_key = DOM.awsSecretAccessKeyInput.value;
        body.aws_region = DOM.awsRegionInput.value;
        body.listing_method = document.querySelector('input[name="listing_method"]:checked').value;
    } else if (provider === 'Ollama') {
        body.host = DOM.ollamaHostInput.value;
    // --- MODIFICATION START: Add logic to gather Azure credentials ---
    } else if (provider === 'Azure') {
        body.azure_api_key = DOM.azureApiKeyInput.value;
        body.azure_endpoint = DOM.azureEndpointInput.value;
        body.azure_deployment_name = DOM.azureDeploymentNameInput.value;
        body.azure_api_version = DOM.azureApiVersionInput.value;
    // --- MODIFICATION END ---
    } else {
        body.apiKey = DOM.llmApiKeyInput.value;
    }

    if (
        (provider === 'Amazon' && (!body.aws_access_key_id || !body.aws_secret_access_key || !body.aws_region)) ||
        (provider === 'Ollama' && !body.host) ||
        // --- MODIFICATION START: Add validation check for Azure fields ---
        (provider === 'Azure' && (!body.azure_api_key || !body.azure_endpoint || !body.azure_deployment_name || !body.azure_api_version)) ||
        // --- MODIFICATION END ---
        (!['Amazon', 'Ollama', 'Azure'].includes(provider) && !body.apiKey)
    ) {
        throw new Error('API credentials or host are required to fetch models.');
    }
    
    const response = await fetch('/models', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    });
    const result = await response.json();

    if (!response.ok) {
        throw new Error(result.message || 'Failed to fetch models.');
    }
    return result;
}
