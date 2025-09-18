/**
 * api.js
 * * This module handles all interactions with the backend server.
 * It encapsulates all `fetch` calls and the logic for handling API requests and responses.
 */

import * as DOM from './domElements.js';
import { state } from './state.js';
// --- MODIFICATION START: Remove all UI imports to break the circular dependency ---
// import { addMessage, toggleLoading, updateStatusWindow, updateTokenDisplay, setThinkingIndicator, highlightResource, addSessionToList, updatePromptsTabCounter, updateToolsTabCounter, createResourceItem } from './ui.js';
// --- MODIFICATION END ---
import { getSystemPromptForModel, isPrivilegedUser } from './utils.js';


// --- MODIFICATION START: Add the new status check function ---
export async function checkServerStatus() {
    const response = await fetch('/api/status');
    if (!response.ok) {
        throw new Error('Could not connect to the server to check status.');
    }
    return await response.json();
}
// --- MODIFICATION END ---


// --- MODIFICATION START: Refactor API calls to throw errors instead of calling UI functions ---
export async function startStream(endpoint, body) {
    // This function now throws an error on failure, which will be caught by the event handler.
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
    // --- MODIFICATION START: Add detailed debugging for API call ---
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
        // Return null to allow graceful failure of the audio playback.
        return null;
    }
    // --- MODIFICATION END ---
}
// --- MODIFICATION END ---


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
    
    // --- MODIFICATION START: Handle empty resource categories gracefully ---
    // If the server responds with a 404, it means the resource category
    // might be empty or not exist. We treat this as a valid, empty state
    // instead of throwing an error.
    if (res.status === 404) {
        return {};
    }
    // --- MODIFICATION END ---

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
    } else {
        body.apiKey = DOM.llmApiKeyInput.value;
    }

    if (
        (provider === 'Amazon' && (!body.aws_access_key_id || !body.aws_secret_access_key || !body.aws_region)) ||
        (provider === 'Ollama' && !body.host) ||
        (!['Amazon', 'Ollama'].includes(provider) && !body.apiKey)
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
