/**
 * state.js
 * * This module manages the application's global state.
 * Centralizing state variables ensures a single source of truth and simplifies state management.
 */

export const state = {
    simpleChatHistory: [],
    currentProvider: 'Google',
    currentModel: '',
    currentStatusId: 0,
    currentSessionId: null,
    resourceData: { tools: {}, prompts: {}, resources: {}, charts: {} },
    currentlySelectedResource: null,
    eventSource: null,
    systemPromptPopupTimer: null,
    countdownValue: 5,
    mouseMoveHandler: null,
    pristineConfig: {},
    isMouseOverStatus: false,
    isInFastPath: false,
    mcpIndicatorTimeout: null,
    llmIndicatorTimeout: null,
    contextIndicatorTimeout: null,
    isTempLastTurnMode: false,
    isLastTurnModeLocked: false,
    isTempVoiceMode: false,
    isVoiceModeLocked: false,
    defaultPromptsCache: {},
    currentPhaseContainerEl: null,
    appConfig: {},
    // --- MODIFICATION START: Add state for TTS conversation flow ---
    ttsState: 'IDLE', // Can be 'IDLE', 'AWAITING_OBSERVATION_CONFIRMATION'
    ttsObservationBuffer: '', // Stores key observations while waiting for user confirmation
    // --- MODIFICATION END ---
    // --- MODIFICATION START: Add state for key observations mode ---
    keyObservationsMode: 'autoplay-off', // 'autoplay-off', 'autoplay-on', 'off'
    // --- MODIFICATION END ---
    // --- MODIFICATION START: Add state for tooltip visibility ---
    showTooltips: true,
    // --- MODIFICATION END ---
    // --- MODIFICATION START: Add state for pending sub-task planning events ---
    pendingSubtaskPlanningEvents: [],
    // --- MODIFICATION END ---
};

// Functions to modify state can be added here if needed, e.g.:
export function setCurrentSessionId(id) {
    state.currentSessionId = id;
}

export function setResourceData(type, data) {
    state.resourceData[type] = data;
}

export function resetCurrentStatusId() {
    state.currentStatusId = 0;
}

export function incrementCurrentStatusId() {
    state.currentStatusId++;
}

