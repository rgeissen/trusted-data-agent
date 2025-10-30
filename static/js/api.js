/**
 * api.js
 * * This module handles all interactions with the backend server.
 * It encapsulates all `fetch` calls and the logic for handling API requests and responses.
 */

import * as DOM from './domElements.js';
import { state } from './state.js';
import { getSystemPromptForModel, isPrivilegedUser } from './utils.js';

/**
 * Gets standard headers for API requests, including Content-Type and User UUID.
 * @param {boolean} includeContentType - Whether to include 'Content-Type: application/json'. Defaults to true.
 * @returns {HeadersInit} The headers object.
 */
function _getHeaders(includeContentType = true) {
    const headers = {};
    if (includeContentType) {
        headers['Content-Type'] = 'application/json';
    }
    if (state.userUUID) {
        headers['X-TDA-User-UUID'] = state.userUUID;
    } else {
        console.warn("User UUID not found in state when creating headers.");
    }
    return headers;
}


export async function checkServerStatus() {
    const res = await fetch('/api/status', { headers: _getHeaders(false) });
    if (!res.ok) {
        return { isConfigured: false };
    }
    return await res.json();
}

/**
 * Fetches API keys from the backend /api_key/ endpoint.
 * @param {string} provider The name of the LLM provider.
 * @returns {Promise<object>} A promise that resolves to the credentials object.
 */
export async function getApiKey(provider) {
    const res = await fetch(`/api_key/${provider.toLowerCase()}`, { headers: _getHeaders(false) });
    if (!res.ok) {
        throw new Error(`Failed to fetch API key for ${provider}`);
    }
    return await res.json();
}


export async function startStream(endpoint, body) {
    const response = await fetch(endpoint, {
        method: 'POST',
        headers: _getHeaders(),
        body: JSON.stringify(body),
    });
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `Request failed with status ${response.status}`);
    }
    return response;
}

/**
 * Sends a request to the backend to cancel the active stream for a session.
 * @param {string} sessionId The ID of the session whose stream should be cancelled.
 * @returns {Promise<object>} A promise that resolves with the server's response.
 */
export async function cancelStream(sessionId) {
    if (!sessionId) {
        throw new Error("Session ID is required to cancel a stream.");
    }
    const response = await fetch(`/api/session/${sessionId}/cancel_stream`, {
        method: 'POST',
        headers: _getHeaders(),
    });
    if (!response.ok && response.status !== 404) {
        let errorData;
        try {
            errorData = await response.json();
        } catch(e) {
            errorData = { message: `Request failed with status ${response.status}` };
        }
        throw new Error(errorData.message || `Request failed with status ${response.status}`);
    }
    try {
        return await response.json();
    } catch(e) {
        return { status: response.status === 200 ? 'success' : 'info', message: response.statusText };
    }
}


export async function synthesizeText(text) {
    console.log("AUDIO DEBUG: synthesizeText called with text:", `"${text.substring(0,100)}..."`);
    if (!state.appConfig.voice_conversation_enabled) {
        console.log("AUDIO DEBUG: Voice feature is disabled in app config. Skipping synthesis.");
        return null;
    }
    const response = await fetch('/api/synthesize-speech', {
        method: 'POST',
        headers: _getHeaders(),
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
        const res = await fetch('/api/prompts-version', { headers: _getHeaders(false) });
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
        headers: _getHeaders(),
        body: JSON.stringify({ name: promptName, disabled: isDisabled })
    });
    if (!res.ok) {
        throw new Error('Server responded with an error.');
    }
}

export async function toggleToolApi(toolName, isDisabled) {
    const res = await fetch('/tool/toggle_status', {
        method: 'POST',
        headers: _getHeaders(),
        body: JSON.stringify({ name: toolName, disabled: isDisabled })
    });
    if (!res.ok) {
        throw new Error('Server responded with an error.');
    }
}

export async function loadResources(type) {
    const res = await fetch(`/${type}`, { headers: _getHeaders(false) });

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
        headers: _getHeaders(),
        body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) {
        throw new Error(data.error || "Failed to get a session ID.");
    }
    return data;
}

export async function loadSession(sessionId) {
    const res = await fetch(`/session/${sessionId}`, { headers: _getHeaders(false) });
    const data = await res.json();
    if (!res.ok) {
        throw new Error(data.error || "Failed to load session.");
    }
    return data;
}

export async function loadAllSessions() {
    const res = await fetch('/sessions', { headers: _getHeaders(false) });
    const sessions = await res.json();
    if (!res.ok) {
        throw new Error(sessions.error || "Could not retrieve past sessions.");
    }
    return sessions;
}

export async function renameSession(sessionId, newName) {
    if (!sessionId || !newName) {
        throw new Error("Session ID and new name are required for renaming.");
    }

    const response = await fetch(`/api/session/${sessionId}/rename`, {
        method: 'POST',
        headers: _getHeaders(),
        body: JSON.stringify({ newName: newName.trim() })
    });

    const result = await response.json();
    if (!response.ok) {
        throw new Error(result.message || `Failed to rename session (status ${response.status}).`);
    }
    return result;
}

export async function deleteSession(sessionId) {
    if (!sessionId) {
        throw new Error("Session ID is required for deletion.");
    }

    const response = await fetch(`/api/session/${sessionId}`, {
        method: 'DELETE',
        headers: _getHeaders(false),
    });

    if (response.status === 204) {
        return { status: "success", message: "Session deleted successfully." };
    }

    const result = await response.json();
    if (!response.ok) {
        throw new Error(result.message || `Failed to delete session (status ${response.status}).`);
    }
    return result;
}


export async function fetchModels() {
    const provider = DOM.llmProviderSelect.value;
    let body = { provider };

    // Credentials gathering logic remains the same...
    if (provider === 'Amazon') {
        body.aws_access_key_id = DOM.awsAccessKeyIdInput.value;
        body.aws_secret_access_key = DOM.awsSecretAccessKeyInput.value;
        body.aws_region = DOM.awsRegionInput.value;
        body.listing_method = document.querySelector('input[name="listing_method"]:checked').value;
    } else if (provider === 'Ollama') {
        body.host = DOM.ollamaHostInput.value;
    } else if (provider === 'Azure') {
        body.azure_api_key = DOM.azureApiKeyInput.value;
        body.azure_endpoint = DOM.azureEndpointInput.value;
        body.azure_deployment_name = DOM.azureDeploymentNameInput.value;
        body.azure_api_version = DOM.azureApiVersionInput.value;
    } else if (provider === 'Friendli') {
        body.friendli_token = DOM.friendliTokenInput.value;
        body.friendli_endpoint_url = DOM.friendliEndpointUrlInput.value;
    } else {
        body.apiKey = DOM.llmApiKeyInput.value;
    }

    if (
        (provider === 'Amazon' && (!body.aws_access_key_id || !body.aws_secret_access_key || !body.aws_region)) ||
        (provider === 'Ollama' && !body.host) ||
        (provider === 'Azure' && (!body.azure_api_key || !body.azure_endpoint || !body.azure_deployment_name || !body.azure_api_version)) ||
        (provider === 'Friendli' && !body.friendli_token) ||
        (!['Amazon', 'Ollama', 'Azure', 'Friendli'].includes(provider) && !body.apiKey)
    ) {
        throw new Error('API credentials or host are required to fetch models.');
    }

    const response = await fetch('/models', {
        method: 'POST',
        headers: _getHeaders(),
        body: JSON.stringify(body)
    });
    const result = await response.json();

    if (!response.ok) {
        throw new Error(result.message || 'Failed to fetch models.');
    }
    return result;
}

export async function fetchTurnPlan(sessionId, turnId) {
    if (!sessionId || !turnId) {
        throw new Error("Session ID and Turn ID are required to fetch the plan.");
    }
    const res = await fetch(`/api/session/${sessionId}/turn/${turnId}/plan`, {
        headers: _getHeaders(false)
    });
    const data = await res.json();
    if (!res.ok) {
        throw new Error(data.error || `Failed to load plan for turn ${turnId} (status ${res.status}).`);
    }
    return data;
}

export async function fetchTurnQuery(sessionId, turnId) {
    if (!sessionId || !turnId) {
        throw new Error("Session ID and Turn ID are required to fetch the query.");
    }
    const res = await fetch(`/api/session/${sessionId}/turn/${turnId}/query`, {
        headers: _getHeaders(false)
    });
    const data = await res.json();
    if (!res.ok) {
        throw new Error(data.error || `Failed to load query for turn ${turnId} (status ${res.status}).`);
    }
    return data;
}

// --- MODIFICATION START: Add fetchTurnDetails function ---
/**
 * Fetches the full details (plan, trace, etc.) for a specific turn from the backend.
 * @param {string} sessionId - The ID of the session.
 * @param {string|number} turnId - The turn number (1-based).
 * @returns {Promise<object>} A promise that resolves to the full turn data object or throws an error.
 */
export async function fetchTurnDetails(sessionId, turnId) {
    if (!sessionId || !turnId) {
        throw new Error("Session ID and Turn ID are required to fetch turn details.");
    }
    const res = await fetch(`/api/session/${sessionId}/turn/${turnId}/details`, {
        headers: _getHeaders(false) // No content-type for GET
    });
    const data = await res.json(); // Always expect JSON, even for errors
    if (!res.ok) {
        throw new Error(data.error || `Failed to load details for turn ${turnId} (status ${res.status}).`);
    }
    // Expected format is the full turn_data object: { turn: ..., user_query: ..., original_plan: ..., execution_trace: ..., final_summary: ..., timestamp: ... }
    return data;
}
// --- MODIFICATION END ---

// --- MODIFICATION START: Add purgeSessionMemory function ---
/**
 * Sends a request to the backend to purge the agent's memory (`chat_object`)
 * for the current session.
 * @param {string} sessionId The ID of the session to purge.
 * @returns {Promise<object>} A promise that resolves with the server's response.
 */
export async function purgeSessionMemory(sessionId) {
    if (!sessionId) {
        throw new Error("Session ID is required to purge memory.");
    }
    const response = await fetch(`/api/session/${sessionId}/purge_memory`, {
        method: 'POST',
        headers: _getHeaders(),
    });

    const result = await response.json();
    if (!response.ok) {
        throw new Error(result.message || `Failed to purge memory (status ${response.status}).`);
    }
    return result;
}
// --- MODIFICATION END ---
