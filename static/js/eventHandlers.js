/**
 * eventHandlers.js
 * * This module sets up all the event listeners for the application.
 * It connects user interactions (clicks, form submissions, etc.) to the corresponding application logic.
 */

import * as DOM from './domElements.js';
import { state } from './state.js';
import * as API from './api.js';
import * as UI from './ui.js';
import * as Utils from './utils.js';
import { copyToClipboard, copyTableToClipboard, classifyConfirmation } from './utils.js';
import { renameSession, deleteSession } from './api.js'; // Import the rename/delete API functions
import { startRecognition, stopRecognition, startConfirmationRecognition } from './voice.js';

// --- Stream Processing ---

async function processStream(responseBody) {
    const reader = responseBody.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const messages = buffer.split('\n\n');
        buffer = messages.pop();

        for (const message of messages) {
            if (!message) continue;

            let eventName = 'message';
            let dataLine = '';

            const lines = message.split('\n');
            for(const line of lines) {
                if (line.startsWith('data:')) {
                    dataLine = line.substring(5).trim();
                } else if (line.startsWith('event:')) {
                    eventName = line.substring(6).trim();
                }
            }

            if (dataLine) {
                try {
                    const eventData = JSON.parse(dataLine);

                    // --- MODIFICATION START: Handle task_id for interactive sessions ---
                    if (eventData.task_id && state.currentTaskId !== eventData.task_id) {
                        state.currentTaskId = eventData.task_id;
                        UI.updateTaskIdDisplay(eventData.task_id);
                    }
                    // --- MODIFICATION END ---

                    // --- Event Handling Logic ---
                    if (eventName === 'status_indicator_update') {
                        const { target, state: statusState } = eventData;
                        let dot;
                        if (target === 'db') dot = DOM.mcpStatusDot;
                        else if (target === 'llm') dot = DOM.llmStatusDot;
                        // Handle LLM thinking indicator separately
                        if (target === 'llm') UI.setThinkingIndicator(statusState === 'busy');

                        if (dot) {
                            if (statusState === 'busy') {
                                dot.classList.replace('idle', 'busy') || dot.classList.replace('connected', 'busy');
                                dot.classList.add('pulsing');
                            } else {
                                dot.classList.remove('pulsing');
                                dot.classList.replace('busy', target === 'db' ? 'connected' : 'idle');
                            }
                        }
                    } else if (eventName === 'context_state_update') {
                         // Currently no specific UI update needed, but could add visual feedback here
                        console.log("Context state update:", eventData);
                    } else if (eventName === 'token_update') {
                        UI.updateTokenDisplay(eventData);
                        if (eventData.call_id && state.currentProvider !== 'Amazon') {
                            const metricsEl = document.querySelector(`.per-call-metrics[data-call-id="${eventData.call_id}"]`);
                            if (metricsEl) {
                                metricsEl.innerHTML = `(LLM Call: ${eventData.statement_input.toLocaleString()} in / ${eventData.statement_output.toLocaleString()} out)`;
                                metricsEl.classList.remove('hidden');
                            }
                        }
                    } else if (eventName === 'session_name_update') {
                        const { session_id, newName } = eventData;
                        UI.updateSessionListItemName(session_id, newName);
                    } else if (eventName === 'session_model_update') {
                        const { session_id, models_used, last_updated } = eventData;
                        UI.updateSessionModels(session_id, models_used);
                        UI.updateSessionTimestamp(session_id, last_updated);
                    } else if (eventName === 'request_user_input') {
                        UI.updateStatusWindow({ step: "Action Required", details: "Waiting for user to correct parameters.", type: 'workaround' });
                        UI.setExecutionState(false);
                        openCorrectionModal(eventData.details);
                    } else if (eventName === 'session_update') {
                        // Logic to potentially update session list if needed
                    } else if (eventName === 'llm_thought') {
                        UI.updateStatusWindow({ step: "Parser has generated the final answer", ...eventData });
                    } else if (eventName === 'prompt_selected') {
                        UI.updateStatusWindow(eventData);
                        if (eventData.prompt_name) UI.highlightResource(eventData.prompt_name, 'prompts');
                    } else if (eventName === 'tool_result' || eventName === 'tool_error' || eventName === 'tool_intent') {
                        UI.updateStatusWindow(eventData);
                        if (eventData.tool_name) {
                            const toolType = eventData.tool_name.startsWith('generate_') ? 'charts' : 'tools';
                            UI.highlightResource(eventData.tool_name, toolType);
                        }
                    } else if (eventName === 'cancelled') {
                        const lastStep = document.getElementById(`status-step-${state.currentStatusId}`);
                        if (lastStep) {
                            lastStep.classList.remove('active');
                            lastStep.classList.add('cancelled');
                        }
                        UI.updateStatusWindow({ step: "Execution Stopped", details: eventData.message || "Process cancelled by user.", type: 'cancelled'}, true);
                        UI.setExecutionState(false);
                    } else if (eventName === 'final_answer') {
                        // --- MODIFICATION START: Pass turn_id to addMessage ---
                        // All new messages are valid by default, so we don't need to pass `true`
                        UI.addMessage('assistant', eventData.final_answer, eventData.turn_id); // Pass turn_id here
                        // --- MODIFICATION END ---
                        UI.updateStatusWindow({ step: "Finished", details: "Response sent to chat." }, true);
                        UI.setExecutionState(false);

                        if (eventData.source === 'voice' && eventData.tts_payload) {
                           const { direct_answer, key_observations } = eventData.tts_payload;

                            if (direct_answer) {
                                const directAnswerAudio = await API.synthesizeText(direct_answer);
                                if (directAnswerAudio) {
                                    const audioUrl = URL.createObjectURL(directAnswerAudio);
                                    const audio = new Audio(audioUrl);
                                    await new Promise(resolve => {
                                        audio.onended = resolve;
                                        audio.onerror = resolve;
                                        audio.play().catch(resolve);
                                    });
                                }
                            }

                            if (key_observations) {
                                switch (state.keyObservationsMode) {
                                    case 'autoplay-off':
                                        state.ttsState = 'AWAITING_OBSERVATION_CONFIRMATION';
                                        state.ttsObservationBuffer = key_observations;
                                        UI.updateVoiceModeUI();

                                        const confirmationQuestion = "Do you want to hear the key observations?";
                                        const questionAudio = await API.synthesizeText(confirmationQuestion);

                                        if (questionAudio) {
                                            const questionUrl = URL.createObjectURL(questionAudio);
                                            const questionPlayer = new Audio(questionUrl);
                                            await new Promise(resolve => {
                                                questionPlayer.onended = resolve;
                                                questionPlayer.onerror = resolve;
                                                questionPlayer.play().catch(resolve);
                                            });
                                            startConfirmationRecognition(handleObservationConfirmation);
                                        } else {
                                            state.ttsState = 'IDLE';
                                            UI.updateVoiceModeUI();
                                        }
                                        break;

                                    case 'autoplay-on':
                                        const observationAudio = await API.synthesizeText(key_observations);
                                        if (observationAudio) {
                                            const audioUrl = URL.createObjectURL(observationAudio);
                                            const audio = new Audio(audioUrl);
                                            await new Promise(resolve => {
                                                audio.onended = resolve;
                                                audio.onerror = resolve;
                                                audio.play().catch(resolve);
                                            });
                                        }

                                    case 'off':
                                        if (state.isVoiceModeLocked) {
                                            setTimeout(() => startRecognition(), 100);
                                        }
                                        break;
                                }
                            } else if (state.isVoiceModeLocked) {
                                setTimeout(() => startRecognition(), 100);
                            }
                        }


                    } else if (eventName === 'error') {
                        UI.addMessage('assistant', `Sorry, an error occurred: ${eventData.error || 'Unknown error'}`);
                        UI.updateStatusWindow({ step: "Error", details: eventData.details || eventData.error, type: 'error' }, true);
                        UI.setExecutionState(false);
                    } else if (eventName === 'rest_task_update') {
                        const { task_id, session_id, event } = eventData.payload; // eslint-disable-line no-unused-vars
                        UI.updateStatusWindow(event, false, 'rest', task_id);
                    } else if (eventName === 'task_start') { // Handle the new task_start event
                        UI.updateTaskIdDisplay(eventData.task_id);
                    } else {
                        UI.updateStatusWindow(eventData);
                    }
                } catch (e) {
                    console.error("Error parsing SSE data line:", dataLine, e);
                }
            }
        }
    }
    if (buffer.trim()) {
        console.warn("Stream ended with unprocessed buffer:", buffer);
    }
}


async function handleObservationConfirmation(transcribedText) {
    const classification = Utils.classifyConfirmation(transcribedText);

    if (classification === 'yes' && state.ttsObservationBuffer) {
        const observationAudio = await API.synthesizeText(state.ttsObservationBuffer);
        if (observationAudio) {
            const audioUrl = URL.createObjectURL(observationAudio);
            const audio = new Audio(audioUrl);
            await new Promise(resolve => {
                audio.onended = resolve;
                audio.play();
            });
        }
    }
    if (state.isVoiceModeLocked) {
        setTimeout(() => startRecognition(), 100);
    }
}


async function handleStreamRequest(endpoint, body) {
    if (body.message) {
        // --- MODIFICATION START: Do not add user message again during replay ---
        // Only add user message if it's NOT a replay initiated by the replay button
        if (!body.is_replay) {
            UI.addMessage('user', body.message, null, true, 'text');
        } else {
             console.log("Replay initiated, skipping adding user message again.");
        }
        // --- MODIFICATION END ---
    } else {
        UI.addMessage('user', `Executing prompt: ${body.prompt_name}`, null, true, 'text');
    }
    DOM.userInput.value = '';
    UI.setExecutionState(true);
    // --- MODIFICATION START: Use centralized reset function ---
    UI.resetStatusWindowForNewTask();
    // --- MODIFICATION END ---

    // This call remains to set the prompt name specifically for the new execution
    UI.updateStatusPromptName();

    const useLastTurnMode = state.isLastTurnModeLocked || state.isTempLastTurnMode;
    // --- MODIFICATION START: Also disable history if it's a replay ---
    body.disabled_history = useLastTurnMode || body.is_replay; // Disable if last turn mode OR replay
    // --- MODIFICATION END ---


    DOM.contextStatusDot.classList.remove('history-disabled-preview');

    try {
        const response = await API.startStream(endpoint, body);
        if (response && response.ok && response.body) {
            await processStream(response.body);
        }
    } catch (error) {
        UI.addMessage('assistant', `Sorry, a stream processing error occurred: ${error.message}`);
        UI.updateStatusWindow({ step: "Error", details: error.stack, type: 'error' }, true);
    } finally {
        UI.setExecutionState(false);
        UI.updateHintAndIndicatorState();
    }
}


// --- Event Handlers ---

export async function handleChatSubmit(e, source = 'text') {
    e.preventDefault();
    const message = DOM.userInput.value.trim();
    if (!message || !state.currentSessionId) return;
    handleStreamRequest('/ask_stream', {
        message,
        session_id: state.currentSessionId,
        source: source
        // is_replay is implicitly false here
    });
}

async function handleStopExecutionClick() {
    console.log("Stop button clicked.");
    if (!state.currentSessionId) {
        console.warn("Cannot stop execution: No active session ID.");
        return;
    }
    if(DOM.stopExecutionButton) DOM.stopExecutionButton.disabled = true;
    try {
        const result = await API.cancelStream(state.currentSessionId);
        console.log("Cancellation request result:", result);
    } catch (error) {
        console.error("Error sending cancellation request:", error);
        UI.addMessage('assistant', `Error trying to stop execution: ${error.message}`);
        if(DOM.stopExecutionButton) DOM.stopExecutionButton.disabled = false;
    }
}

// --- MODIFICATION START: Define handleReloadPlanClick ---
/**
 * Handles clicks on the "Reload Plan" button or user avatar. Fetches and displays the full turn details.
 * @param {HTMLElement} element - The element that was clicked (button or avatar div).
 */
async function handleReloadPlanClick(element) {
    const turnId = element.dataset.turnId; // Get turnId from data attribute
    const sessionId = state.currentSessionId;
    if (!turnId || !sessionId) {
        console.error("Missing turnId or sessionId for reloading plan details.");
        return;
    }

    // Indicate loading in the status window
    DOM.statusWindowContent.innerHTML = `<p class="p-4 text-gray-400">Loading details for Turn ${turnId}...</p>`;
    // Scroll to top of status window
    DOM.statusWindowContent.scrollTop = 0;
    // Ensure status panel is open
    const statusCheckbox = document.getElementById('toggle-status-checkbox');
    if (statusCheckbox && !statusCheckbox.checked) {
        statusCheckbox.checked = true;
        // Manually trigger the toggle logic if checkbox change doesn't automatically do it
        const event = new Event('change');
        statusCheckbox.dispatchEvent(event);
    }


    try {
        // Fetch the full turn details (plan + trace)
        const turnData = await API.fetchTurnDetails(sessionId, turnId);
        console.log("Fetched Turn Details:", turnData);

        // Check if data is valid
        if (!turnData || (!turnData.original_plan && !turnData.execution_trace)) {
            throw new Error("Received empty or invalid turn details from the server.");
        }

        // Render the historical trace using the new UI function
        UI.renderHistoricalTrace(turnData.original_plan || [], turnData.execution_trace || [], turnId, turnData.user_query);

        // --- MODIFICATION START: Update task ID display for reloaded turn ---
        // Prioritize task_id if available in turnData, otherwise use turnId as fallback
        const taskIdToDisplay = turnData.task_id || turnId;
        UI.updateTaskIdDisplay(taskIdToDisplay);
        // --- MODIFICATION END ---

        // --- MODIFICATION START: Update model display for reloaded turn ---
        // After rendering, update the model display to reflect the turn's actual model
        if (turnData.provider && turnData.model) {
            // --- MODIFICATION: Pass historical data directly to UI function ---
            UI.updateStatusPromptName(turnData.provider, turnData.model, true);
        }
        // --- MODIFICATION END ---

        // --- MODIFICATION START: Synchronize header buttons ---
        // After successfully rendering the trace, update the header buttons
        if (DOM.headerReplayPlannedButton) {
            DOM.headerReplayPlannedButton.classList.remove('hidden');
            DOM.headerReplayPlannedButton.disabled = false;
            DOM.headerReplayPlannedButton.dataset.turnId = turnId;
        }
        if (DOM.headerReplayOptimizedButton) {
            DOM.headerReplayOptimizedButton.classList.remove('hidden');
            DOM.headerReplayOptimizedButton.disabled = false;
            DOM.headerReplayOptimizedButton.dataset.turnId = turnId;
        }
        // --- MODIFICATION END ---

    } catch (error) {
        console.error(`Error loading details for turn ${turnId}:`, error);
        DOM.statusWindowContent.innerHTML = `<div class="p-4 status-step error"><h4 class="font-bold text-sm text-white mb-2">Error Loading Details</h4><p class="text-xs">${error.message}</p></div>`;
    }
}
// --- MODIFICATION END ---

// --- MODIFICATION START: This function is now for REPLAYING THE QUERY ---
/**
 * Handles clicks on the "Replay Original Query" button. Fetches the original query
 * text for that turn and re-submits it, triggering a NEW PLAN.
 * @param {HTMLButtonElement} buttonEl - The button element that was clicked.
 */
export async function handleReplayQueryClick(buttonEl) {
    const turnId = buttonEl.dataset.turnId;
    const sessionId = state.currentSessionId;
    if (!turnId || !sessionId) {
        console.error("Missing turnId or sessionId for replaying query.");
        return;
    }

    try {
        // 1. Fetch ONLY the original query text
        const queryData = await API.fetchTurnQuery(sessionId, turnId);
        const originalQuery = queryData.query;

        if (!originalQuery) {
            throw new Error("Could not retrieve the original query for this turn.");
        }

        const displayMessage = `🔄 Replaying **query** from Turn ${turnId}: ${originalQuery}`;
        console.log(`Replaying QUERY from Turn ${turnId}: "${originalQuery}"`);
        // Add a message indicating a *query* replay
        UI.addMessage('user', displayMessage, null, true, 'text');

        // 2. Re-submit using handleStreamRequest, *without* a plan
        handleStreamRequest('/ask_stream', {
            message: originalQuery,      // Used for original_user_input on backend
            display_message: displayMessage, // The message to be saved in history
            session_id: sessionId,
            source: 'text',
            is_replay: true,             // Ensures logging and disables history for planning
            plan_to_execute: null        // Explicitly null. This forces a new plan.
        });

    } catch (error) {
        console.error(`Error replaying query for turn ${turnId}:`, error);
        UI.addMessage('assistant', `Sorry, could not replay the query from Turn ${turnId}. Error: ${error.message}`);
    }
}
// --- MODIFICATION END ---

// --- MODIFICATION START: Add new handler for REPLAYING THE PLAN ---
/**
 * Handles clicks on the "Replay Planned Query" button. Fetches the original query *and*
 * the original plan for that turn, then re-submits *the plan* for execution.
 * @param {HTMLButtonElement} buttonEl - The button element that was clicked.
 */
async function handleReplayPlanClick(buttonEl) {
    const turnId = buttonEl.dataset.turnId;
    const sessionId = state.currentSessionId;
    if (!turnId || !sessionId) {
        console.error("Missing turnId or sessionId for replaying plan.");
        return;
    }

    try {
        // 1. Fetch BOTH the original query (for context) and the original plan
        const [queryData, planData] = await Promise.all([
            API.fetchTurnQuery(sessionId, turnId),
            API.fetchTurnPlan(sessionId, turnId)
        ]);

        const originalQuery = queryData.query;
        const originalPlan = planData.plan;

        if (!originalQuery) {
            throw new Error("Could not retrieve the original query for this turn.");
        }
        if (!originalPlan) {
            throw new Error("Could not retrieve the original plan for this turn.");
        }

        const displayMessage = `🔄 Replaying **plan** from Turn ${turnId}: ${originalQuery}`;
        console.log(`Replaying PLAN from Turn ${turnId} (Query: "${originalQuery}")`);
        // Add a message indicating a *plan* replay
        UI.addMessage('user', displayMessage, null, true, 'text');

        // 2. Re-submit using handleStreamRequest, passing the plan_to_execute
        handleStreamRequest('/ask_stream', {
            message: originalQuery,      // Used for original_user_input on backend
            display_message: displayMessage, // The message to be saved in history
            session_id: sessionId,
            source: 'text',
            is_replay: true,             // Ensures logging and disables history for planning (which is skipped anyway)
            plan_to_execute: originalPlan  // This tells the backend to skip planning and execute this plan
        });

    } catch (error) {
        console.error(`Error replaying plan for turn ${turnId}:`, error);
        UI.addMessage('assistant', `Sorry, could not replay the plan from Turn ${turnId}. Error: ${error.message}`);
    }
}
// --- MODIFICATION END ---

// --- MODIFICATION START: Add handler for context purge click ---
/**
 * Handles clicks on the "Context" status dot to purge agent memory.
 */
async function handleContextPurgeClick() {
    if (!state.currentSessionId) {
        console.warn("Context purge click ignored: No active session ID.");
        return;
    }

    // Use the existing UI.showConfirmation
    UI.showConfirmation(
        'Purge Agent Memory?',
        "Are you sure you want to archive the context of all past turns? This will force the agent to re-evaluate the next query from scratch. Your chat log and replay ability will be preserved.",
        async () => {
            try {
                // Call the new API endpoint
                await API.purgeSessionMemory(state.currentSessionId);
                // Blink the dot on success
                UI.blinkContextDot();
                console.log(`Agent memory purged for session ${state.currentSessionId}`);
                
                // --- START NEW LOGIC ---
                // Visually invalidate all existing turns in the DOM
                const allBadges = DOM.chatLog.querySelectorAll('.turn-badge');
                allBadges.forEach(badge => {
                    badge.classList.add('context-invalid');
                });
        
                // Update avatar titles to reflect archived state
                const allClickableAvatars = DOM.chatLog.querySelectorAll('.clickable-avatar');
                allClickableAvatars.forEach(avatar => {
                    // Remove old title text if present and add the new one
                    avatar.title = avatar.title.replace(' (Archived Context)', '') + ' (Archived Context)';
                });
                
                console.log(`Applied .context-invalid style to ${allBadges.length} existing turn badges.`);
                // --- END NEW LOGIC ---

            } catch (error) {
                console.error(`Failed to purge agent memory:`, error);
                // Optionally show an error to the user
                alert(`Error: Could not purge agent memory. ${error.message}`);
            }
        }
    );
}
// --- MODIFICATION END ---


export async function handleLoadResources(type) {
    const tabButton = document.querySelector(`.resource-tab[data-type="${type}"]`);
    const categoriesContainer = document.getElementById(`${type}-categories`);
    const panelsContainer = document.getElementById(`${type}-panels-container`);
    const typeCapitalized = type.charAt(0).toUpperCase() + type.slice(1);

    try {
        const data = await API.loadResources(type);

        if (!data || Object.keys(data).length === 0) {
            if(tabButton) {
                tabButton.style.display = 'none';
            }
            return;
        }

        tabButton.style.display = 'inline-block';
        state.resourceData[type] = data;

        if (type === 'prompts') {
            UI.updatePromptsTabCounter();
        } else if (type === 'tools') {
            UI.updateToolsTabCounter();
        } else {
            const totalCount = Object.values(data).reduce((acc, items) => acc + items.length, 0);
            tabButton.textContent = `${typeCapitalized} (${totalCount})`;
        }

        categoriesContainer.innerHTML = '';
        panelsContainer.innerHTML = '';

        Object.keys(data).forEach(category => {
            const categoryTab = document.createElement('button');
            categoryTab.className = 'category-tab px-4 py-2 rounded-md font-semibold text-sm transition-colors hover:bg-[#D9501A]';
            categoryTab.textContent = category;
            categoryTab.dataset.category = category;
            categoryTab.dataset.type = type;
            categoriesContainer.appendChild(categoryTab);

            const panel = document.createElement('div');
            panel.id = `panel-${type}-${category}`;
            panel.className = 'category-panel px-4 space-y-2';
            panel.dataset.category = category;

            data[category].forEach(resource => {
                const itemEl = UI.createResourceItem(resource, type);
                panel.appendChild(itemEl);
            });
            panelsContainer.appendChild(panel);
        });

        document.querySelectorAll(`#${type}-categories .category-tab`).forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll(`#${type}-categories .category-tab`).forEach(t => t.classList.remove('active'));
                tab.classList.add('active');

                document.querySelectorAll(`#${type}-panels-container .category-panel`).forEach(p => {
                    p.classList.toggle('open', p.dataset.category === tab.dataset.category);
                });
            });
        });

        if (categoriesContainer.querySelector('.category-tab')) {
            categoriesContainer.querySelector('.category-tab').click();
        }

    } catch (error) {
        console.error(`Failed to load ${type}: ${error.message}`);
        if(tabButton) {
            tabButton.textContent = `${typeCapitalized} (Error)`;
            tabButton.style.display = 'inline-block';
        }
        categoriesContainer.innerHTML = '';
        panelsContainer.innerHTML = `<div class="p-4 text-center text-red-400">Failed to load ${type}.</div>`;
    }
}


export async function handleStartNewSession() {
    DOM.chatLog.innerHTML = '';
    DOM.statusWindowContent.innerHTML = '<p class="text-gray-400">Waiting for a new request...</p>';
    UI.updateTokenDisplay({ statement_input: 0, statement_output: 0, total_input: 0, total_output: 0 });
    UI.addMessage('assistant', "Starting a new conversation... Please wait.");
    UI.setThinkingIndicator(false);

    // --- MODIFICATION START: Hide header buttons and clear turnId on new session ---
    if (DOM.headerReplayPlannedButton) {
        DOM.headerReplayPlannedButton.classList.add('hidden');
        DOM.headerReplayPlannedButton.dataset.turnId = '';
    }
    if (DOM.headerReplayOptimizedButton) {
        DOM.headerReplayOptimizedButton.classList.add('hidden');
        DOM.headerReplayOptimizedButton.dataset.turnId = '';
    }
    // --- MODIFICATION END ---

    try {
        const data = await API.startNewSession();
        const sessionItem = UI.addSessionToList(data, true);
        DOM.sessionList.prepend(sessionItem);
        await handleLoadSession(data.id, true);
    } catch (error) {
        UI.addMessage('assistant', `Failed to start a new session: ${error.message}`);
    } finally {
        DOM.userInput.focus();
    }
}


export async function handleLoadSession(sessionId, isNewSession = false) {
    if (state.currentSessionId === sessionId && !isNewSession) return;

    // --- MODIFICATION START: Remove highlight on load ---
    UI.removeHighlight(sessionId);
    // --- MODIFICATION END ---

    try {
        const data = await API.loadSession(sessionId);
        state.currentSessionId = sessionId;
        state.currentProvider = data.provider || state.currentProvider;
        state.currentModel = data.model || state.currentModel;
        DOM.chatLog.innerHTML = '';
        if (data.history && data.history.length > 0) {
            // --- MODIFICATION START: Pass turn_id and isValid during history load ---
            // Simulate turn IDs based on message pairs for existing sessions
            let currentTurnId = 1;
            for (let i = 0; i < data.history.length; i++) {
                const msg = data.history[i];
                // Default to true if isValid flag is missing (for older sessions)
                const isValid = msg.isValid === undefined ? true : msg.isValid;

                if (msg.role === 'assistant') {
                    // Pass the calculated turn ID and validity for assistant messages
                    UI.addMessage(msg.role, msg.content, currentTurnId, isValid, msg.source);
                    currentTurnId++; // Increment turn ID after an assistant message
                } else {
                    // User messages don't need a turn ID, but pass validity
                    UI.addMessage(msg.role, msg.content, null, isValid, msg.source);
                }
            }
            // --- MODIFICATION END ---
        } else {
             UI.addMessage('assistant', "I'm ready to help. How can I assist you with your Teradata system today?");
        }
        UI.updateTokenDisplay({ total_input: data.input_tokens, total_output: data.output_tokens });

        document.querySelectorAll('.session-item').forEach(item => {
            item.classList.toggle('active', item.dataset.sessionId === sessionId);
        });

        // --- MODIFICATION START ---
        // Explicitly update the models for the loaded session in the UI
        UI.updateSessionModels(sessionId, data.models_used);
        // This will reset the status display to the globally configured model
        UI.updateStatusPromptName(data.provider, data.model);
        // --- MODIFICATION END ---
    } catch (error) {
        UI.addMessage('assistant', `Error loading session: ${error.message}`);
    } finally {
        DOM.userInput.focus();
    }
}

function handleResourceTabClick(e) {
    if (e.target.classList.contains('resource-tab')) {
        const type = e.target.dataset.type;
        document.querySelectorAll('.resource-tab').forEach(tab => tab.classList.remove('active'));
        e.target.classList.add('active');

        document.querySelectorAll('.resource-panel').forEach(panel => {
            panel.style.display = panel.id === `${type}-panel` ? 'flex' : 'none';
        });
    }
}

function openPromptModal(prompt) {
    DOM.promptModalOverlay.classList.remove('hidden', 'opacity-0');
    DOM.promptModalContent.classList.remove('scale-95', 'opacity-0');
    DOM.promptModalTitle.textContent = prompt.name;
    DOM.promptModalForm.dataset.promptName = prompt.name;
    DOM.promptModalInputs.innerHTML = '';
    DOM.promptModalForm.querySelector('button[type="submit"]').textContent = 'Run Prompt';

    if (prompt.arguments && prompt.arguments.length > 0) {
        prompt.arguments.forEach(arg => {
            const inputGroup = document.createElement('div');
            const label = document.createElement('label');
            label.htmlFor = `prompt-arg-${arg.name}`;
            label.className = 'block text-sm font-medium text-gray-300 mb-1';
            label.textContent = arg.name + (arg.required ? ' *' : '');

            const input = document.createElement('input');
            input.type = 'text';
            input.id = `prompt-arg-${arg.name}`;
            input.name = arg.name;
            input.className = 'w-full p-2 bg-gray-700 border border-gray-600 rounded-md focus:ring-2 focus:ring-[#F15F22] focus:border-[#F15F22] outline-none';
            input.placeholder = arg.description || `Enter value for ${arg.name}`;
            if (arg.required) input.required = true;

            inputGroup.appendChild(label);
            inputGroup.appendChild(input);
            DOM.promptModalInputs.appendChild(inputGroup);
        });
    } else {
        DOM.promptModalInputs.innerHTML = '<p class="text-gray-400">This prompt requires no arguments.</p>';
    }

    DOM.promptModalForm.onsubmit = (e) => {
        e.preventDefault();
        const promptName = e.target.dataset.promptName;
        const formData = new FormData(e.target);
        const arugments = Object.fromEntries(formData.entries());

        UI.closePromptModal();
        handleStreamRequest('/invoke_prompt_stream', {
            session_id: state.currentSessionId,
            prompt_name: promptName,
            arguments: arugments
        });
    };
}

function openCorrectionModal(data) {
    DOM.promptModalOverlay.classList.remove('hidden', 'opacity-0');
    DOM.promptModalContent.classList.remove('scale-95', 'opacity-0');

    const spec = data.specification;
    DOM.promptModalTitle.textContent = `Correction for: ${spec.name}`;
    DOM.promptModalForm.dataset.toolName = spec.name;
    DOM.promptModalInputs.innerHTML = '';
    DOM.promptModalForm.querySelector('button[type="submit"]').textContent = 'Run Correction';

    const messageEl = document.createElement('p');
    messageEl.className = 'text-yellow-300 text-sm mb-4 p-3 bg-yellow-500/10 rounded-lg';
    messageEl.textContent = data.message;
    DOM.promptModalInputs.appendChild(messageEl);

    spec.arguments.forEach(arg => {
        const inputGroup = document.createElement('div');
        const label = document.createElement('label');
        label.htmlFor = `correction-arg-${arg.name}`;
        label.className = 'block text-sm font-medium text-gray-300 mb-1';
        label.textContent = arg.name + (arg.required ? ' *' : '');

        const input = document.createElement('input');
        input.type = 'text';
        input.id = `correction-arg-${arg.name}`;
        input.name = arg.name;
        input.className = 'w-full p-2 bg-gray-700 border border-gray-600 rounded-md focus:ring-2 focus:ring-[#F15F22] focus:border-[#F15F22] outline-none';
        input.placeholder = arg.description || `Enter value for ${arg.name}`;
        if (arg.required) input.required = true;

        inputGroup.appendChild(label);
        inputGroup.appendChild(input);
        DOM.promptModalInputs.appendChild(inputGroup);
    });

    DOM.promptModalForm.onsubmit = (e) => {
        e.preventDefault();
        const toolName = e.target.dataset.toolName;
        const formData = new FormData(e.target);
        const userArgs = Object.fromEntries(formData.entries());

        const correctedPrompt = `Please run the tool '${toolName}' with the following corrected parameters: ${JSON.stringify(userArgs)}`;

        UI.closePromptModal();

        handleStreamRequest('/ask_stream', { message: correctedPrompt, session_id: state.currentSessionId });
    };
}

async function openViewPromptModal(promptName) {
    DOM.viewPromptModalOverlay.classList.remove('hidden', 'opacity-0');
    DOM.viewPromptModalContent.classList.remove('scale-95', 'opacity-0');
    DOM.viewPromptModalTitle.textContent = `Viewing Prompt: ${promptName}`;
    DOM.viewPromptModalText.textContent = 'Loading...';

    try {
        const res = await fetch(`/prompt/${promptName}`);
        const data = await res.json();
        if (res.ok) {
            DOM.viewPromptModalText.textContent = data.content;
        } else {
            if (data.error === 'dynamic_prompt_error') {
                DOM.viewPromptModalText.textContent = `Info: ${data.message}`;
            } else {
                throw new Error(data.error || 'Failed to fetch prompt content.');
            }
        }
    } catch (error) {
        DOM.viewPromptModalText.textContent = `Error: ${error.message}`;
    }
}

function getCurrentCoreConfig() {
    const formData = new FormData(DOM.configForm);
    return Object.fromEntries(formData.entries());
}

function handleCloseConfigModalRequest() {
    const coreChanged = JSON.stringify(getCurrentCoreConfig()) !== JSON.stringify(state.pristineConfig);
    if (coreChanged) {
        UI.showConfirmation('Discard Changes?', 'You have unsaved changes in your configuration. Are you sure you want to close?', UI.closeConfigModal);
    } else {
        UI.closeConfigModal();
    }
}

function handleConfigActionButtonClick(e) {
    if (e.currentTarget.type === 'button') {
        handleCloseConfigModalRequest();
    }
}

export async function finalizeConfiguration(config) {
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

    setTimeout(UI.closeConfigModal, 1000);
}


async function handleConfigFormSubmit(e) {
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
            await finalizeConfiguration(config);
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


async function handleProviderChange() {
    DOM.llmModelSelect.innerHTML = '<option value="">-- Select Provider & Enter Credentials --</option>';
    DOM.configStatus.textContent = '';

    await loadCredentialsAndModels();
}

async function handleModelChange() {
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

async function handleRefreshModelsClick() {
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

function openPromptEditor() {
    DOM.promptEditorTitle.innerHTML = `System Prompt Editor for: <code class="text-teradata-orange font-normal">${state.currentProvider} / ${Utils.getNormalizedModelId(state.currentModel)}</code>`;
    const promptText = Utils.getSystemPromptForModel(state.currentProvider, state.currentModel);
    DOM.promptEditorTextarea.value = promptText;
    DOM.promptEditorTextarea.dataset.initialValue = promptText;

    DOM.promptEditorOverlay.classList.remove('hidden', 'opacity-0');
    DOM.promptEditorContent.classList.remove('scale-95', 'opacity-0');
    UI.updatePromptEditorState();
}

function forceClosePromptEditor() {
    DOM.promptEditorOverlay.classList.add('opacity-0');
    DOM.promptEditorContent.classList.add('scale-95', 'opacity-0');
    setTimeout(() => {
        DOM.promptEditorOverlay.classList.add('hidden');
        DOM.promptEditorStatus.textContent = '';
    }, 300);
}

function closePromptEditor() {
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

async function saveSystemPromptChanges() {
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

async function resetSystemPrompt(force = false) {
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

function openChatModal() {
    DOM.chatModalOverlay.classList.remove('hidden', 'opacity-0');
    DOM.chatModalContent.classList.remove('scale-95', 'opacity-0');
    DOM.chatModalInput.focus();
}

async function handleChatModalSubmit(e) {
    e.preventDefault();
    const message = DOM.chatModalInput.value.trim();
    if (!message) return;

    UI.addMessageToModal('user', message);
    state.simpleChatHistory.push({ role: 'user', content: message });
    DOM.chatModalInput.value = '';
    DOM.chatModalInput.disabled = true;

    try {
        const res = await fetch('/simple_chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                history: state.simpleChatHistory
            })
        });

        const data = await res.json();

        if (res.ok) {
            UI.addMessageToModal('assistant', data.response);
            state.simpleChatHistory.push({ role: 'assistant', content: data.response });
        } else {
            throw new Error(data.error || 'An unknown error occurred.');
        }

    } catch (error) {
        UI.addMessageToModal('assistant', `Error: ${error.message}`);
    } finally {
        DOM.chatModalInput.disabled = false;
        DOM.chatModalInput.focus();
    }
}

function handleKeyDown(e) {
    if (e.key === 'Control' && !e.repeat) {
        if (e.shiftKey) {
            state.isVoiceModeLocked = !state.isVoiceModeLocked;
            if (state.isVoiceModeLocked) {
                startRecognition();
            } else {
                stopRecognition();
            }
        } else {
            state.isTempVoiceMode = true;
            startRecognition();
        }
        UI.updateVoiceModeUI();
        e.preventDefault();
        return;
    }

    if (e.key === 'Alt' && !e.repeat) {
        if (e.shiftKey) {
            state.isLastTurnModeLocked = !state.isLastTurnModeLocked;
        } else {
            state.isTempLastTurnMode = true;
        }
        UI.updateHintAndIndicatorState();
        e.preventDefault();
    }
}

function handleKeyUp(e) {
    if (e.key === 'Control') {
        if (state.isTempVoiceMode) {
            state.isTempVoiceMode = false;
            stopRecognition();
            UI.updateVoiceModeUI();
        }
        e.preventDefault();
    }

    if (e.key === 'Alt') {
        if (state.isTempLastTurnMode) {
            state.isTempLastTurnMode = false;
            UI.updateHintAndIndicatorState();
        }
        e.preventDefault();
    }
}

function handleKeyObservationsToggleClick() {
    switch (state.keyObservationsMode) {
        case 'autoplay-off':
            state.keyObservationsMode = 'autoplay-on';
            break;
        case 'autoplay-on':
            state.keyObservationsMode = 'off';
            break;
        case 'off':
        default:
            state.keyObservationsMode = 'autoplay-off';
            break;
    }
    localStorage.setItem('keyObservationsMode', state.keyObservationsMode);
    UI.updateKeyObservationsModeUI();

    let announcementText = '';
    switch (state.keyObservationsMode) {
        case 'autoplay-off':
            announcementText = 'Key Observations Autoplay Off';
            break;
        case 'autoplay-on':
            announcementText = 'Key Observations Autoplay On';
            break;
        case 'off':
            announcementText = 'Key Observations Off';
            break;
    }

    if (announcementText) {
        (async () => {
            try {
                const audioBlob = await API.synthesizeText(announcementText);
                if (audioBlob) {
                    const audioUrl = URL.createObjectURL(audioBlob);
                    const audio = new Audio(audioUrl);
                    audio.play();
                }
            } catch (error) {
                console.error("Failed to play state change announcement:", error);
            }
        })();
    }
}

async function handleIntensityChange() {
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

function getSystemPromptSummaryHTML() {
    let devFlagHtml = '';
//    if (state.appConfig.allow_synthesis_from_history) {
//        devFlagHtml = `
//             <div class="p-3 bg-yellow-900/50 rounded-lg mt-4">
//                <p class="font-semibold text-yellow-300">Developer Mode Enabled</p>
//                <p class="text-xs text-yellow-400 mt-1">The 'Answer from History' feature is active. The agent may answer questions by synthesizing from previous turns without re-running tools.</p>
//           </div>
//        `;
//    }

    return `
        <div class="space-y-4 text-gray-300 text-sm p-2">
            <h4 class="font-bold text-lg text-white">Agent Operating Principles</h4>
            <p>The agent's primary goal is to answer your requests by using its available capabilities:</p>
            <ul class="list-disc list-outside space-y-2 pl-5">
                <li><strong>Prompts:</strong> For pre-defined analyses, descriptions, or summaries.</li>
                <li><strong>Tools:</strong> For direct actions like "list tables" or "count users".</li>
            </ul>
            <div class="p-3 bg-gray-900/50 rounded-lg">
                <p class="font-semibold text-white">Decision-Making Process:</p>
                <p class="text-xs text-gray-400 mt-1">The agent follows a strict hierarchy. It will <strong class="text-white">always prioritize using a pre-defined prompt</strong> if it matches your request for an analysis. Otherwise, it will use the most appropriate tool to perform a direct action.</p>
            </div>
            ${devFlagHtml}
            <div class="border-t border-white/10 pt-4 mt-4">
                <h4 class="text-md font-bold text-yellow-300 mb-2">New features available</h4>
                <p class="text-xs text-gray-400 mb-3">Latest enhancements and updates to the Trusted Data Agent.</p>
                <div class="whats-new-container">
                    <ul class="list-disc list-inside text-xs text-gray-300 space-y-1">
                       <li><strong>06-Nov-2025:</strong> UI Real-Time Monitoring of Rest Requests</li>
                       <li><strong>31-Oct-2025:</strong> Fully configurable Context Management (Turn & Session)</li>
                       <li><strong>28-Oct-2025:</strong> Turn Replay & Turn Reload Plan</li>
                       <li><strong>24-Oct-2025:</strong> Stop Button Added - Ability to immediately Stop Workflows</li>
                       <li><strong>23-Oct-2025:</strong> Robust Multi-Tool Phase Handling</li>
                       <li><strong>11-Oct-2025:</strong> Friendly.AI Integration</li>
                       <li><strong>10-Oct-2025:</strong> Context Aware Rendering of the Collateral Report</li>
                       <li><strong>19-SEP-2025:</strong> Microsoft Azure Integration</li>
                       <li><strong>18-SEP-2025:</strong> REST Interface for Engine Configuration, Execution & Monitoring </li>
                       <li><strong>12-SEP-2025:</strong> Significant Formatting Upgrade (Canonical Baseline Model for LLM Provider Rendering)</li>
                       <li><strong>05-SEP-2025:</strong> Conversation Mode (Google Cloud Credentials required)</li>
                    </ul>
                </div>
            </div>
            <div class="border-t border-white/10 pt-4 mt-4">
                 <h4 class="text-md font-bold text-yellow-300 mb-2">Model Price/Performance Leadership Board</h4>
                 <p class="text-xs text-gray-400 mb-3">External link to the latest LLM benchmarks.</p>
                 <a href="https://gorilla.cs.berkeley.edu/leaderboard.html" target="_blank" class="text-teradata-orange hover:underline text-sm">https://gorilla.cs.berkeley.edu/leaderboard.html</a>
            </div>
            <div id="disabled-capabilities-container-splash">
                <!-- Disabled capabilities will be injected here -->
            </div>
        </div>
    `;
}

function buildDisabledCapabilitiesListHTML() {
    const disabledTools = [];
    if (state.resourceData.tools) {
        Object.values(state.resourceData.tools).flat().forEach(tool => {
            if (tool.disabled) disabledTools.push(tool.name);
        });
    }

    const disabledPrompts = [];
    if (state.resourceData.prompts) {
        Object.values(state.resourceData.prompts).flat().forEach(prompt => {
            if (prompt.disabled) disabledPrompts.push(prompt.name);
        });
    }

    if (disabledTools.length === 0 && disabledPrompts.length === 0) {
        return '';
    }

    let html = `
        <div class="border-t border-white/10 pt-4 mt-4">
            <h4 class="text-md font-bold text-yellow-300 mb-2">Reactive Capabilities</h4>
            <p class="text-xs text-gray-400 mb-3">The following capabilities are not actively participating in user queries. You can enable and/or actively execute them in the 'Capabilities' panel.</p>
            <div class="flex gap-x-8">
    `;

    if (disabledTools.length > 0) {
        html += '<div><h5 class="font-semibold text-sm text-white mb-1">Tools</h5><ul class="list-disc list-inside text-xs text-gray-300 space-y-1">';
        disabledTools.forEach(name => {
            html += `<li><code class="text-teradata-orange text-xs">${name}</code></li>`;
        });
        html += '</ul></div>';
    }

    if (disabledPrompts.length > 0) {
        html += '<div><h5 class="font-semibold text-sm text-white mb-1">Prompts</h5><ul class="list-disc list-inside text-xs text-gray-300 space-y-1">';
        disabledPrompts.forEach(name => {
            html += `<li><code class="text-teradata-orange text-xs">${name}</code></li>`;
        });
        html += '</ul></div>';
    }

    html += '</div></div>';
    return html;
}

function startPopupCountdown() {
    if (state.systemPromptPopupTimer) {
        clearInterval(state.systemPromptPopupTimer);
    }

    const countdownTimerEl = document.getElementById('countdown-timer');
    const countdownContainerEl = document.getElementById('countdown-container');

    if (countdownTimerEl && countdownContainerEl) {
        countdownTimerEl.textContent = state.countdownValue;
        countdownContainerEl.style.visibility = 'visible';

        state.systemPromptPopupTimer = setInterval(() => {
            state.countdownValue--;
            countdownTimerEl.textContent = state.countdownValue;
            if (state.countdownValue <= 0) {
                closeSystemPromptPopup();
            }
        }, 1000);
    }
}

function stopPopupCountdown() {
    if (state.systemPromptPopupTimer) {
        clearInterval(state.systemPromptPopupTimer);
        state.systemPromptPopupTimer = null;
    }
    const countdownContainerEl = document.getElementById('countdown-container');
    if(countdownContainerEl) {
        countdownContainerEl.style.visibility = 'hidden';
    }
}

function openSystemPromptPopup() {
    DOM.systemPromptPopupBody.innerHTML = getSystemPromptSummaryHTML();
    const disabledListContainer = document.getElementById('disabled-capabilities-container-splash');
    if (disabledListContainer) {
        disabledListContainer.innerHTML = buildDisabledCapabilitiesListHTML();
    }

    if (Utils.isPrivilegedUser()) {
        DOM.systemPromptPopupViewFull.style.display = 'inline-block';
    } else {
        DOM.systemPromptPopupViewFull.style.display = 'none';
    }

    DOM.systemPromptPopupOverlay.classList.remove('hidden', 'opacity-0');
    DOM.systemPromptPopupContent.classList.remove('scale-95', 'opacity-0');

    state.countdownValue = 5;
    startPopupCountdown();

    state.mouseMoveHandler = () => {
        stopPopupCountdown();
        document.removeEventListener('mousemove', state.mouseMoveHandler);
    };
    document.addEventListener('mousemove', state.mouseMoveHandler);
}

function closeSystemPromptPopup() {
    stopPopupCountdown();
    if (state.mouseMoveHandler) {
         document.removeEventListener('mousemove', state.mouseMoveHandler);
         state.mouseMoveHandler = null;
    }
    DOM.systemPromptPopupOverlay.classList.add('opacity-0');
    DOM.systemPromptPopupContent.classList.add('scale-95', 'opacity-0');
    setTimeout(() => {
        DOM.systemPromptPopupOverlay.classList.add('hidden');
    }, 300);
}

async function handleTogglePrompt(promptName, isDisabled, buttonEl) {
    try {
        await API.togglePromptApi(promptName, isDisabled);

        for (const category in state.resourceData.prompts) {
            const prompt = state.resourceData.prompts[category].find(p => p.name === promptName);
            if (prompt) {
                prompt.disabled = isDisabled;
                break;
            }
        }

        const promptItem = document.getElementById(`resource-prompts-${promptName}`);
        const runButton = promptItem.querySelector('.run-prompt-button');

        promptItem.classList.toggle('opacity-60', isDisabled);
        promptItem.title = isDisabled ? 'This prompt is disabled and will not be used by the agent.' : '';
        runButton.disabled = isDisabled;
        runButton.title = isDisabled ? 'This prompt is disabled.' : 'Run this prompt.';

        buttonEl.innerHTML = isDisabled ?
            `<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M3.707 2.293a1 1 0 00-1.414 1.414l14 14a1 1 0 001.414-1.414l-1.473-1.473A10.014 10.014 0 0019.542 10C18.268 5.943 14.478 3 10 3a9.958 9.958 0 00-4.512 1.074L3.707 2.293zM10 12a2 2 0 110-4 2 2 0 010 4z" clip-rule="evenodd" /><path d="M2 10s3.939 4 8 4 8-4 8-4-3.939-4-8-4-8 4-8 4zm13.707 4.293a1 1 0 00-1.414-1.414L12.586 14.6A8.007 8.007 0 0110 16c-4.478 0-8.268-2.943-9.542-7 .946-2.317 2.83-4.224 5.166-5.447L2.293 1.293A1 1 0 00.879 2.707l14 14a1 1 0 001.414 0z" /></svg>` :
            `<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path d="M10 12a2 2 0 100-4 2 2 0 000 4z" /><path fill-rule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.022 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clip-rule="evenodd" /></svg>`;

        UI.updatePromptsTabCounter();

    } catch (error) {
        console.error(`Failed to toggle prompt ${promptName}:`, error);
    }
}

async function handleToggleTool(toolName, isDisabled, buttonEl) {
    try {
        await API.toggleToolApi(toolName, isDisabled);

        for (const category in state.resourceData.tools) {
            const tool = state.resourceData.tools[category].find(t => t.name === toolName);
            if (tool) {
                tool.disabled = isDisabled;
                break;
            }
        }

        const toolItem = document.getElementById(`resource-tools-${toolName}`);
        toolItem.classList.toggle('opacity-60', isDisabled);
        toolItem.title = isDisabled ? 'This tool is disabled and will not be used by the agent.' : '';

        buttonEl.innerHTML = isDisabled ?
            `<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M3.707 2.293a1 1 0 00-1.414 1.414l14 14a1 1 0 001.414-1.414l-1.473-1.473A10.014 10.014 0 0019.542 10C18.268 5.943 14.478 3 10 3a9.958 9.958 0 00-4.512 1.074L3.707 2.293zM10 12a2 2 0 110-4 2 2 0 010 4z" clip-rule="evenodd" /><path d="M2 10s3.939 4 8 4 8-4 8-4-3.939-4-8-4-8 4-8 4zm13.707 4.293a1 1 0 00-1.414-1.414L12.586 14.6A8.007 8.007 0 0110 16c-4.478 0-8.268-2.943-9.542-7 .946-2.317 2.83-4.224 5.166-5.447L2.293 1.293A1 1 0 00.879 2.707l14 14a1 1 0 001.414 0z" /></svg>` :
            `<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path d="M10 12a2 2 0 100-4 2 2 0 000 4z" /><path fill-rule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.022 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clip-rule="evenodd" /></svg>`;

        UI.updateToolsTabCounter();

    } catch (error) {
        console.error(`Failed to toggle tool ${toolName}:`, error);
    }
}

/**
 * Handles the save action when editing a session name (Enter or Blur).
 * @param {Event} e - The event object (blur or keydown).
 */
export async function handleSessionRenameSave(e) {
    const inputElement = e.target;
    const sessionItem = inputElement.closest('.session-item');
    if (!sessionItem) return;

    const sessionId = sessionItem.dataset.sessionId;
    const newName = inputElement.value.trim();
    const originalName = inputElement.dataset.originalName;

    if (!newName || newName === originalName) {
        UI.exitSessionEditMode(inputElement, originalName);
        return;
    }

    inputElement.disabled = true;
    inputElement.style.opacity = '0.7';

    try {
        await renameSession(sessionId, newName);
        UI.exitSessionEditMode(inputElement, newName);
        console.log(`Session ${sessionId} renamed to '${newName}'`);
        UI.moveSessionToTop(sessionId);
    } catch (error) {
        console.error(`Failed to rename session ${sessionId}:`, error);
        inputElement.style.borderColor = 'red';
        inputElement.disabled = false;
        // Revert to original name and exit edit mode on API error
        UI.exitSessionEditMode(inputElement, originalName);
    }
}

/**
 * Handles the cancel action when editing a session name (Escape).
 * @param {Event} e - The event object (keydown).
 */
export function handleSessionRenameCancel(e) {
    const inputElement = e.target;
    const originalName = inputElement.dataset.originalName;
    UI.exitSessionEditMode(inputElement, originalName);
}

/**
 * Handles the click event for the delete session button.
 * @param {HTMLButtonElement} deleteButton - The delete button element that was clicked.
 */
async function handleDeleteSessionClick(deleteButton) {
    const sessionItem = deleteButton.closest('.session-item');
    if (!sessionItem) return;

    const sessionId = sessionItem.dataset.sessionId;
    const sessionName = sessionItem.querySelector('.session-name-span')?.textContent || 'this session';

    UI.showConfirmation(
        'Delete Session?',
        `Are you sure you want to permanently delete '${sessionName}'? This action cannot be undone.`,
        async () => {
            try {
                await deleteSession(sessionId);
                UI.removeSessionFromList(sessionId);

                if (state.currentSessionId === sessionId) {
                    console.log('Active session deleted. Checking for remaining sessions.');
                    try {
                        const remainingSessions = await API.loadAllSessions();
                        if (remainingSessions && remainingSessions.length > 0) {
                            // The API returns sessions sorted by most recent first.
                            const nextSessionId = remainingSessions[0].id;
                            console.log(`Switching to most recent session: ${nextSessionId}`);
                            await handleLoadSession(nextSessionId);
                        } else {
                            console.log('No remaining sessions. Starting a new session.');
                            await handleStartNewSession();
                        }
                    } catch (error) {
                        console.error('Error handling session switch after deletion:', error);
                        UI.addMessage('assistant', `Could not switch to another session. Please select one manually or start a new one. ${error.message}`);
                        // As a fallback, create a new session if the session loading fails
                        await handleStartNewSession();
                    }
                }
            } catch (error) {
                console.error(`Failed to delete session ${sessionId}:`, error);
                UI.addMessage('assistant', `Error: Could not delete session '${sessionName}'. ${error.message}`);
            }
        }
    );
}

// --- MODIFICATION START: Add handler for toggling turn validity ---
async function handleToggleTurnValidity(badgeEl) {
    const turnId = badgeEl.dataset.turnId;
    const sessionId = state.currentSessionId;
    if (!turnId || !sessionId) {
        console.error("Missing turnId or sessionId for toggling validity.");
        return;
    }

    try {
        const response = await fetch(`/api/session/${sessionId}/turn/${turnId}/toggle_validity`, {
            method: 'POST',
            headers: {
                'X-TDA-User-UUID': state.userUUID
            }
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || 'Failed to toggle turn validity.');
        }

        // On success, toggle the UI
        const allBadgesForTurn = document.querySelectorAll(`.turn-badge[data-turn-id="${turnId}"]`);
        allBadgesForTurn.forEach(badge => {
            badge.classList.toggle('context-invalid');
        });

    } catch (error) {
        console.error(`Error toggling validity for turn ${turnId}:`, error);
        alert(`Error: Could not update turn status. ${error.message}`);
    }
}
// --- MODIFICATION END ---


// --- Initializer ---

export function initializeEventListeners() {
    DOM.chatForm.addEventListener('submit', handleChatSubmit);
    DOM.newChatButton.addEventListener('click', handleStartNewSession);
    DOM.resourceTabs.addEventListener('click', handleResourceTabClick);
    DOM.keyObservationsToggleButton.addEventListener('click', handleKeyObservationsToggleClick);

    // Delegated event listener for copy buttons and NEW reload/replay buttons
    DOM.chatLog.addEventListener('click', (e) => {
        const copyButton = e.target.closest('.copy-button');
        const clickableAvatar = e.target.closest('.clickable-avatar[data-turn-id]');
        const clickableBadge = e.target.closest('.clickable-badge[data-turn-id]');

        if (clickableBadge) {
            e.stopPropagation();
            handleToggleTurnValidity(clickableBadge);
        } else if (copyButton) {
            const copyType = copyButton.dataset.copyType;
            if (copyType === 'code') {
                copyToClipboard(copyButton);
            } else if (copyType === 'table') {
                copyTableToClipboard(copyButton);
            }
        } else if (clickableAvatar) {
            handleReloadPlanClick(clickableAvatar);
        }
    });

    if (DOM.stopExecutionButton) {
        DOM.stopExecutionButton.addEventListener('click', handleStopExecutionClick);
    } else {
        console.error("Stop execution button not found in DOM elements.");
    }

    // --- MODIFICATION START: Add event listeners for header replay buttons ---
    if (DOM.headerReplayPlannedButton) {
        DOM.headerReplayPlannedButton.addEventListener('click', (e) => {
            // --- MODIFICATION: Wire to the new handleReplayPlanClick ---
            handleReplayPlanClick(e.currentTarget);
        });
    }
    if (DOM.headerReplayOptimizedButton) {
        DOM.headerReplayOptimizedButton.addEventListener('click', (e) => {
             alert('Replay Optimized Query - Not Implemented Yet.');
            // Placeholder: handleReplayOptimizedClick(e.currentTarget);
        });
    }
    // --- MODIFICATION END ---


    DOM.mainContent.addEventListener('click', (e) => {
        const runButton = e.target.closest('.run-prompt-button');
        const viewButton = e.target.closest('.view-prompt-button');
        const promptToggleButton = e.target.closest('.prompt-toggle-button');
        const toolToggleButton = e.target.closest('.tool-toggle-button');

        if (runButton && !runButton.disabled) {
            const resourceItem = runButton.closest('.resource-item');
            const promptName = resourceItem.id.replace('resource-prompts-', '');
            let promptData = null;
            for (const category in state.resourceData.prompts) {
                const found = state.resourceData.prompts[category].find(p => p.name === promptName);
                if (found) {
                    promptData = found;
                    break;
                }
            }
            if (promptData) openPromptModal(promptData);
            return;
        }

        if (viewButton) {
            const resourceItem = viewButton.closest('.resource-item');
            const promptName = resourceItem.id.replace('resource-prompts-', '');
            openViewPromptModal(promptName);
            return;
        }

        if (promptToggleButton) {
            const resourceItem = promptToggleButton.closest('.resource-item');
            const promptName = resourceItem.id.replace('resource-prompts-', '');
            let promptData = null;
            for (const category in state.resourceData.prompts) {
                const found = state.resourceData.prompts[category].find(p => p.name === promptName);
                if (found) {
                    promptData = found;
                    break;
                }
            }
            if (promptData) handleTogglePrompt(promptName, !promptData.disabled, promptToggleButton);
            return;
        }

        if (toolToggleButton) {
            const resourceItem = toolToggleButton.closest('.resource-item');
            const toolName = resourceItem.id.replace('resource-tools-', '');
             let toolData = null;
            for (const category in state.resourceData.tools) {
                const found = state.resourceData.tools[category].find(t => t.name === toolName);
                if (found) {
                    toolData = found;
                    break;
                }
            }
            if (toolData) handleToggleTool(toolName, !toolData.disabled, toolToggleButton);
            return;
        }
    });

    DOM.sessionList.addEventListener('click', (e) => {
        const sessionItem = e.target.closest('.session-item');
        if (!sessionItem) return;

        const editButton = e.target.closest('.session-edit-button');
        const deleteButton = e.target.closest('.session-delete-button');

        if (deleteButton) {
            handleDeleteSessionClick(deleteButton);
        } else if (editButton) {
            UI.enterSessionEditMode(editButton);
        } else if (!sessionItem.querySelector('.session-edit-input')) {
            handleLoadSession(sessionItem.dataset.sessionId);
        }
    });

    // All modal listeners
    DOM.promptModalClose.addEventListener('click', UI.closePromptModal);
    DOM.promptModalOverlay.addEventListener('click', (e) => {
        if (e.target === DOM.promptModalOverlay) UI.closePromptModal();
    });
    DOM.viewPromptModalClose.addEventListener('click', UI.closeViewPromptModal);
    DOM.viewPromptModalOverlay.addEventListener('click', (e) => {
        if (e.target === DOM.viewPromptModalOverlay) UI.closeViewPromptModal();
    });
    DOM.infoButton.addEventListener('click', () => {
        DOM.infoModalOverlay.classList.remove('hidden', 'opacity-0');
        DOM.infoModalContent.classList.remove('scale-95', 'opacity-0');
    });
    DOM.infoModalClose.addEventListener('click', () => {
        DOM.infoModalOverlay.classList.add('opacity-0');
        DOM.infoModalContent.classList.add('scale-95', 'opacity-0');
        setTimeout(() => DOM.infoModalOverlay.classList.add('hidden'), 300);
    });
    DOM.infoModalOverlay.addEventListener('click', (e) => {
        if (e.target === DOM.infoModalOverlay) {
            DOM.infoModalClose.click();
        }
    });

    // Config modal listeners
    DOM.configMenuButton.addEventListener('click', () => {
        DOM.configModalOverlay.classList.remove('hidden', 'opacity-0');
        DOM.configModalContent.classList.remove('scale-95', 'opacity-0');
        state.pristineConfig = getCurrentCoreConfig();
        UI.updateConfigButtonState();
    });
    DOM.configModalClose.addEventListener('click', handleCloseConfigModalRequest);
    DOM.configActionButton.addEventListener('click', handleConfigActionButtonClick);
    DOM.configForm.addEventListener('submit', handleConfigFormSubmit);
    DOM.configForm.addEventListener('input', UI.updateConfigButtonState);


    // LLM config listeners
    DOM.llmProviderSelect.addEventListener('change', handleProviderChange);
    [DOM.awsAccessKeyIdInput, DOM.awsSecretAccessKeyInput, DOM.awsRegionInput].forEach(input => {
        input.addEventListener('blur', () => {
            const awsCreds = {
                aws_access_key_id: DOM.awsAccessKeyIdInput.value,
                aws_secret_access_key: DOM.awsSecretAccessKeyInput.value,
                aws_region: DOM.awsRegionInput.value
            };
            localStorage.setItem('amazonApiKey', JSON.stringify(awsCreds));
        });
    });
    DOM.llmApiKeyInput.addEventListener('blur', () => {
        const provider = DOM.llmProviderSelect.value;
        const apiKey = DOM.llmApiKeyInput.value;
        if (apiKey && !['Amazon', 'Ollama'].includes(provider)) {
            localStorage.setItem(`${provider.toLowerCase()}ApiKey`, apiKey);
        }
    });
    DOM.ollamaHostInput.addEventListener('blur', () => {
        localStorage.setItem('ollamaHost', DOM.ollamaHostInput.value);
    });
    DOM.refreshModelsButton.addEventListener('click', handleRefreshModelsClick);
    DOM.llmModelSelect.addEventListener('change', handleModelChange);


    // Prompt editor listeners
    DOM.promptEditorButton.addEventListener('click', openPromptEditor);
    DOM.promptEditorClose.addEventListener('click', closePromptEditor);
    DOM.promptEditorSave.addEventListener('click', saveSystemPromptChanges);
    DOM.promptEditorReset.addEventListener('click', () => resetSystemPrompt(false));
    DOM.promptEditorTextarea.addEventListener('input', UI.updatePromptEditorState);

    // Simple chat modal listeners
    DOM.chatModalButton.addEventListener('click', openChatModal);
    DOM.chatModalClose.addEventListener('click', UI.closeChatModal); // FIXED
    DOM.chatModalOverlay.addEventListener('click', (e) => {
        if (e.target === DOM.chatModalOverlay) UI.closeChatModal(); // FIXED
    });
    DOM.chatModalForm.addEventListener('submit', handleChatModalSubmit);

    // Global listeners
    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('keyup', handleKeyUp);
    DOM.statusWindowContent.addEventListener('mouseenter', () => { state.isMouseOverStatus = true; });
    DOM.statusWindowContent.addEventListener('mouseleave', () => { state.isMouseOverStatus = false; });
    DOM.chartingIntensitySelect.addEventListener('change', handleIntensityChange);
    DOM.systemPromptPopupClose.addEventListener('click', closeSystemPromptPopup);
    DOM.systemPromptPopupViewFull.addEventListener('click', () => {
        closeSystemPromptPopup();
        openPromptEditor();
    });
    DOM.systemPromptPopupOverlay.addEventListener('click', (e) => {
        if (e.target === DOM.systemPromptPopupOverlay) closeSystemPromptPopup();
    });
    DOM.windowMenuButton.addEventListener('click', (e) => {
        e.stopPropagation();
        DOM.windowDropdownMenu.classList.toggle('open');
    });
    document.addEventListener('click', (e) => {
        if (!DOM.windowDropdownMenu.contains(e.target) && e.target !== DOM.windowMenuButton) {
            DOM.windowDropdownMenu.classList.remove('open');
        }
    });

    // --- MODIFICATION START: Add context dot click listener ---
    DOM.contextStatusDot.addEventListener('click', handleContextPurgeClick);
    // --- MODIFICATION END ---

    // --- MODIFICATION START: Add tooltips toggle listener ---
    const toggleTooltipsCheckbox = document.getElementById('toggle-tooltips-checkbox');
    if (toggleTooltipsCheckbox) {
        // Set initial state from localStorage
        const savedTooltipPref = localStorage.getItem('showTooltips');
        state.showTooltips = savedTooltipPref === null ? true : savedTooltipPref === 'true';
        toggleTooltipsCheckbox.checked = state.showTooltips;

        toggleTooltipsCheckbox.addEventListener('change', (e) => {
            state.showTooltips = e.target.checked;
            localStorage.setItem('showTooltips', state.showTooltips);
        });
    }
    // --- MODIFICATION END ---

    // --- MODIFICATION START: Add welcome screen toggle listeners ---
    const welcomeScreenCheckbox = document.getElementById('toggle-welcome-screen-checkbox');
    const welcomeScreenPopupCheckbox = document.getElementById('welcome-screen-show-at-startup-checkbox');

    const handleWelcomeScreenToggle = (e) => {
        const isChecked = e.target.checked;
        state.showWelcomeScreenAtStartup = isChecked;
        localStorage.setItem('showWelcomeScreenAtStartup', isChecked);
        if (welcomeScreenCheckbox) welcomeScreenCheckbox.checked = isChecked;
        if (welcomeScreenPopupCheckbox) welcomeScreenPopupCheckbox.checked = isChecked;
    };

    if (welcomeScreenCheckbox) {
        welcomeScreenCheckbox.addEventListener('change', handleWelcomeScreenToggle);
    }
    if (welcomeScreenPopupCheckbox) {
        welcomeScreenPopupCheckbox.addEventListener('change', handleWelcomeScreenToggle);
    }
    // --- MODIFICATION END ---
}
