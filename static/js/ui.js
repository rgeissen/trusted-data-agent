/**
 * ui.js
 * * This module handles all direct DOM manipulations and UI updates.
 * Functions here are responsible for rendering messages, modals, status updates, and other visual changes.
 */

import * as DOM from './domElements.js';
import { state } from './state.js';
import { renderChart, isPrivilegedUser, isPromptCustomForModel, getNormalizedModelId } from './utils.js';
// We need access to the functions that will handle save/cancel from the input
import { handleSessionRenameSave, handleSessionRenameCancel } from './handlers/sessionManagement.js';
import { handleReplayQueryClick } from './eventHandlers.js';


// NOTE: This module no longer imports from eventHandlers.js, breaking a circular dependency.
// Instead, eventHandlers.js will import these UI functions.

/**
 * Renders the historical plan and execution trace in the status window.
 * @param {Array<object>} originalPlan - The original plan array generated for the turn.
 * @param {Array<object>} executionTrace - The execution trace array (action/result pairs).
 * @param {string|number} turnId - The ID of the turn being displayed.
 * @param {string} userQuery - The original user query for this turn.
 */
export function renderHistoricalTrace(originalPlan = [], executionTrace = [], turnId, userQuery = 'N/A') {
    DOM.statusWindowContent.innerHTML = ''; // Clear previous content
    state.currentStatusId = 0; // Reset status ID counter for this rendering
    state.isInFastPath = false; // Reset fast path flag
    state.currentPhaseContainerEl = null; // Reset phase container reference
    state.pendingSubtaskPlanningEvents = []; // Clear any pending events

    // 1. Add a title
    const titleEl = document.createElement('h3');
    titleEl.className = 'text-lg font-bold text-white mb-4 p-3 bg-gray-900/50 rounded-md';
    titleEl.textContent = `Reloaded Details for Turn ${turnId}`;
    DOM.statusWindowContent.appendChild(titleEl);

    // 2. Iterate through the new, rich execution trace
    executionTrace.forEach(traceEntry => {
        let eventData = {};
        let eventName = null;

        if (traceEntry.action && traceEntry.action.tool_name === 'TDA_SystemLog') {
            // This is a system event
            const metadata = traceEntry.action.metadata || {};
            eventData = {
                step: traceEntry.action.arguments.message,
                details: traceEntry.action.arguments.details,
                type: metadata.type,
                metadata: {
                    execution_depth: metadata.execution_depth
                }
            };
        } else if (traceEntry.action && traceEntry.result) {
            // This is a regular tool call, render as two steps
            const metadata = traceEntry.action.metadata || {};

            // Render intent
            const intentEventData = {
                step: `Tool Execution Intent`,
                details: traceEntry.action,
                type: 'tool_intent',
                metadata: {
                    execution_depth: metadata.execution_depth
                }
            };
            updateStatusWindow(intentEventData, false);

            // Render result
            const resultEventData = {
                step: `Tool Execution Result`,
                details: traceEntry.result,
                type: traceEntry.result.status === 'error' ? 'tool_error' : 'tool_result',
                metadata: {
                    execution_depth: metadata.execution_depth
                }
            };
            // For tool results, the event name is important
            eventName = resultEventData.type === 'tool_error' ? 'tool_error' : 'tool_result';
            updateStatusWindow(resultEventData, false, eventName);
            return; // We've handled this entry completely
        } else {
            // Skip unknown trace entry formats
            return;
        }

        updateStatusWindow(eventData, false);
    });

    // Finalize the last step
    const finalStepElement = document.getElementById(`status-step-${state.currentStatusId}`);
    if (finalStepElement && finalStepElement.classList.contains('active')) {
        finalStepElement.classList.remove('active');
        if (!finalStepElement.classList.contains('error') && !finalStepElement.classList.contains('cancelled')) {
            finalStepElement.classList.add('completed');
        }
    }

    // Auto-scroll logic
    if (!state.isMouseOverStatus) {
        DOM.statusWindowContent.scrollTop = 0; // Scroll to top for reloaded view
    }
}


export function addMessage(role, content, turnId = null, isValid = true, source = null) { // eslint-disable-line no-unused-vars
    const wrapper = document.createElement('div');
    wrapper.className = `message-bubble group flex items-start gap-4 ${role === 'user' ? 'justify-end' : ''}`;
    const icon = document.createElement('div');
    // Ensure relative positioning is always set for badge context
    icon.className = 'flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center text-white font-bold shadow-lg relative';
    icon.textContent = role === 'user' ? 'U' : 'A';
    icon.classList.add(role === 'user' ? 'bg-gray-700' : 'bg-[#F15F22]');

    if (role === 'assistant' && turnId) {
        icon.classList.add('assistant-avatar');
        icon.classList.add('clickable-avatar');
        if (state.showTooltips) {
            icon.title = 'Long-press to replay original query';
        }
        let pressTimer;

        const startPress = (e) => {
            e.preventDefault();
            icon.classList.add('long-press');
            pressTimer = setTimeout(() => {
                icon.classList.remove('long-press');
                handleReplayQueryClick({ dataset: { turnId } });
            }, 1500);
        };

        const cancelPress = () => {
            clearTimeout(pressTimer);
            icon.classList.remove('long-press');
        };

        icon.addEventListener('mousedown', startPress);
        icon.addEventListener('mouseup', cancelPress);
        icon.addEventListener('mouseleave', cancelPress);
        icon.addEventListener('touchstart', startPress);
        icon.addEventListener('touchend', cancelPress);
    }

    // This logic is now handled by the badge.

    const messageContainer = document.createElement('div');
    messageContainer.className = 'p-4 rounded-xl shadow-lg max-w-2xl glass-panel';
    messageContainer.classList.add(role === 'user' ? 'bg-gray-800/50' : 'bg-[#333333]/50');

    const author = document.createElement('p');
    author.className = 'font-bold mb-2 text-sm';
    author.textContent = role === 'user' ? 'You' : 'Assistant';
    author.classList.add(role === 'user' ? 'text-gray-300' : 'text-[#F15F22]');
    messageContainer.appendChild(author);

    if (role === 'user' && source === 'rest') {
        const restTag = document.createElement('span');
        restTag.className = 'rest-call-tag';
        restTag.textContent = 'Rest Call';
        author.appendChild(restTag);
    }

    const messageContent = document.createElement('div');
    messageContent.innerHTML = content;
    messageContainer.appendChild(messageContent);

    wrapper.appendChild(role === 'user' ? messageContainer : icon);
    wrapper.appendChild(role === 'user' ? icon : messageContainer);

    // --- MODIFICATION START: Add vertical feedback stack for assistant answers ---
    if (role === 'assistant' && turnId) {
        const feedbackWrapper = document.createElement('div');
        feedbackWrapper.className = 'mt-2 flex justify-end';
        feedbackWrapper.dataset.turnId = turnId;

        const pill = document.createElement('div');
        pill.className = 'flex items-stretch rounded-md bg-gray-900/50 border border-white/10 overflow-hidden backdrop-blur-sm';

        const makeBtn = (dir) => {
            const btn = document.createElement('button');
            btn.type = 'button';
            // Removed 'group' so hover only affects this button, not sibling
            btn.className = 'feedback-btn px-2 py-1 flex items-center justify-center gap-1 text-gray-300 hover:text-white hover:bg-gray-800/60 transition text-xs';
            btn.setAttribute('aria-label', dir === 'up' ? 'Mark answer as helpful' : 'Mark answer as unhelpful');
            btn.setAttribute('aria-pressed', 'false');
            btn.dataset.vote = dir;
            const svg = dir === 'up'
                ? `<svg class='w-4 h-4' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'>
                     <path d='M14 9V5a3 3 0 00-3-3l-4 9v11h11a3 3 0 003-3v-5a3 3 0 00-3-3h-7'/>
                   </svg>`
                : `<svg class='w-4 h-4' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'>
                     <path d='M10 15v4a3 3 0 003 3l4-9V2H6a3 3 0 00-3 3v5a3 3 0 003 3h7'/>
                   </svg>`;
            const labelText = dir === 'up' ? 'Helpful' : 'Unhelpful';
            const labelSpan = document.createElement('span');
            labelSpan.className = 'vote-label opacity-70 transition text-[10px] tracking-wide text-gray-400';
            labelSpan.textContent = labelText;
            btn.innerHTML = svg; // set icon first
            btn.appendChild(labelSpan);
            // Isolated hover: only brighten hovered button's label
            btn.addEventListener('mouseenter', () => {
                labelSpan.classList.remove('opacity-70', 'text-gray-400');
                labelSpan.classList.add('opacity-100', 'text-white');
            });
            btn.addEventListener('mouseleave', () => {
                labelSpan.classList.add('opacity-70', 'text-gray-400');
                labelSpan.classList.remove('opacity-100', 'text-white');
            });
            return btn;
        };

        const upBtn = makeBtn('up');
        const divider = document.createElement('div');
        divider.className = 'w-px bg-white/10';
        const downBtn = makeBtn('down');

        const applyState = () => {
            const current = state.feedbackByTurn[turnId] || 'none';
            upBtn.classList.toggle('active', current === 'up');
            downBtn.classList.toggle('active', current === 'down');
            upBtn.setAttribute('aria-pressed', current === 'up' ? 'true' : 'false');
            downBtn.setAttribute('aria-pressed', current === 'down' ? 'true' : 'false');
            if (current === 'up') {
                upBtn.classList.remove('text-gray-300');
                upBtn.classList.add('text-[#F15F22]', 'bg-gray-800/60');
                downBtn.classList.add('text-gray-300');
                downBtn.classList.remove('text-[#F15F22]', 'bg-gray-800/60');
            } else if (current === 'down') {
                downBtn.classList.remove('text-gray-300');
                downBtn.classList.add('text-[#F15F22]', 'bg-gray-800/60');
                upBtn.classList.add('text-gray-300');
                upBtn.classList.remove('text-[#F15F22]', 'bg-gray-800/60');
            } else {
                upBtn.classList.add('text-gray-300');
                upBtn.classList.remove('text-[#F15F22]', 'bg-gray-800/60');
                downBtn.classList.add('text-gray-300');
                downBtn.classList.remove('text-[#F15F22]', 'bg-gray-800/60');
            }
        };

        const toggleVote = (dir) => {
            const current = state.feedbackByTurn[turnId] || 'none';
            state.feedbackByTurn[turnId] = current === dir ? null : dir;
            applyState();
            
            // --- MODIFICATION START: Save feedback to backend ---
            const vote = state.feedbackByTurn[turnId];
            if (state.currentSessionId) {
                import('./api.js').then(({ updateTurnFeedback }) => {
                    updateTurnFeedback(state.currentSessionId, turnId, vote)
                        .catch(err => {
                            console.error(`Failed to save feedback for turn ${turnId}:`, err);
                        });
                });
            }
            // --- MODIFICATION END ---
        };

        upBtn.addEventListener('click', () => toggleVote('up'));
        downBtn.addEventListener('click', () => toggleVote('down'));

        pill.appendChild(upBtn);
        pill.appendChild(divider);
        pill.appendChild(downBtn);
        feedbackWrapper.appendChild(pill);
        messageContainer.appendChild(feedbackWrapper);
        applyState();
    }
    // --- MODIFICATION END ---

    DOM.chatLog.appendChild(wrapper);

    // Logic for avatar click, header buttons, and turn badges
    if (role === 'assistant' && turnId) {
        // --- Add Turn Badge to Assistant Avatar ---
        const assistantBadge = document.createElement('span');
        assistantBadge.className = 'turn-badge clickable-badge';
        assistantBadge.dataset.turnId = turnId;
        if (state.showTooltips) {
            assistantBadge.title = 'Click to toggle context validity';
        }
        assistantBadge.addEventListener('mousedown', (e) => e.stopPropagation());
        assistantBadge.textContent = turnId;
        icon.appendChild(assistantBadge); // Append badge to assistant icon

        if (isValid === false) {
            assistantBadge.classList.add('context-invalid');
        }


        // --- Find previous User message and add badge/click handler ---
        const userBubbles = DOM.chatLog.querySelectorAll('.message-bubble:has(.bg-gray-700)');
        const lastUserBubble = userBubbles.length > 0 ? userBubbles[userBubbles.length - 1] : null;

        if (lastUserBubble) {
            const userAvatarIcon = lastUserBubble.querySelector('.bg-gray-700');
            if (userAvatarIcon) {
                // 1. Make the User Avatar clickable (REGARDLESS of context)
                userAvatarIcon.classList.add('clickable-avatar');
                userAvatarIcon.dataset.turnId = turnId;

                // --- Add Turn Badge to User Avatar ---
                const userBadge = document.createElement('span');
                userBadge.className = 'turn-badge clickable-badge';
                userBadge.dataset.turnId = turnId;
                if (state.showTooltips) {
                    userBadge.title = 'Click to toggle context validity';
                }
                userBadge.addEventListener('mousedown', (e) => e.stopPropagation());
                userBadge.textContent = turnId;
                userAvatarIcon.appendChild(userBadge); // Append badge to user icon
                
                if (isValid === false) {
                    userBadge.classList.add('context-invalid');
                }
                if (state.showTooltips) {
                    if (isValid === false) {
                        userAvatarIcon.title = `Reload Details for Turn ${turnId} (Archived Context)`;
                    } else {
                        userAvatarIcon.title = `Reload Plan & Details for Turn ${turnId}`;
                    }
                }
            }
        }

        // --- Show and update the header replay buttons ---
        if (DOM.headerReplayPlannedButton) {
            DOM.headerReplayPlannedButton.classList.remove('hidden');
            DOM.headerReplayPlannedButton.dataset.turnId = turnId;
        }
        if (DOM.headerReplayOptimizedButton) {
            DOM.headerReplayOptimizedButton.classList.remove('hidden');
            DOM.headerReplayOptimizedButton.dataset.turnId = turnId;
        }
    }

    const chartContainers = messageContent.querySelectorAll('.chart-render-target');
    chartContainers.forEach(container => {
        if (container.dataset.spec) {
            renderChart(container.id, container.dataset.spec);
        }
    });

    wrapper.scrollIntoView({ behavior: 'smooth', block: 'end' });
}


/**
 * Sets the UI state for active execution (disables input, shows stop button, etc.).
 * @param {boolean} isActive - True if execution is starting, false if ending.
 */
export function setExecutionState(isActive) {
    DOM.userInput.disabled = isActive;
    DOM.submitButton.disabled = isActive;
    DOM.newChatButton.disabled = isActive;
    DOM.sendIcon.classList.toggle('hidden', isActive);
    DOM.loadingSpinner.classList.toggle('hidden', !isActive);

    if (DOM.stopExecutionButton) {
        DOM.stopExecutionButton.classList.toggle('hidden', !isActive);
        DOM.stopExecutionButton.disabled = !isActive;
    }

    if (isActive) {
        // Hide and disable buttons when execution starts
        if (DOM.headerReplayPlannedButton) {
            DOM.headerReplayPlannedButton.classList.add('hidden');
            DOM.headerReplayPlannedButton.disabled = true;
        }
        if (DOM.headerReplayOptimizedButton) {
            DOM.headerReplayOptimizedButton.classList.add('hidden');
            DOM.headerReplayOptimizedButton.disabled = true;
        }
    } else {
        // Enable buttons when execution ends (they will be shown by addMessage if applicable)
        if (DOM.headerReplayPlannedButton) {
            DOM.headerReplayPlannedButton.disabled = false;
        }
        if (DOM.headerReplayOptimizedButton) {
            DOM.headerReplayOptimizedButton.disabled = false;
        }
        // Don't explicitly show them here, addMessage handles showing them when a turn completes
    }

    if (!isActive) {
        setThinkingIndicator(false);
        DOM.mcpStatusDot.classList.remove('pulsing', 'busy');
        DOM.llmStatusDot.classList.remove('pulsing', 'busy');

        if (!DOM.mcpStatusDot.classList.contains('disconnected')) {
            DOM.mcpStatusDot.classList.add('connected');
        }
        if (!DOM.llmStatusDot.classList.contains('disconnected')) {
            DOM.llmStatusDot.classList.add('idle');
        }
    }
}


/**
 * Updates the visual status of the Server-Sent Events (SSE) connection indicator.
 * @param {('connected'|'reconnecting'|'disconnected')} status - The current status of the connection.
 */
export function updateSSEStatus(status) {
    if (!DOM.sseStatusDot) return;

    DOM.sseStatusDot.classList.remove('connected', 'reconnecting', 'disconnected');
    DOM.sseStatusDot.classList.add(status);

    switch (status) {
        case 'connected':
            DOM.sseStatusDot.title = 'Real-time connection active.';
            break;
        case 'reconnecting':
            DOM.sseStatusDot.title = 'Connection lost. Attempting to reconnect...';
            break;
        case 'disconnected':
            DOM.sseStatusDot.title = 'Real-time connection failed. Please refresh the page.';
            break;
    }
}


function _renderPlanningDetails(details) {
    if (!details.summary || !details.full_text) return null;

    let fullTextHtml = '';
    const text = details.full_text;
    const characterThreshold = 150;

    if (text.length > characterThreshold) {
        fullTextHtml = `
            <details class="text-xs">
                <summary class="cursor-pointer text-gray-400 hover:text-white">Full Text (${text.length} chars)</summary>
                <div class="mt-2 p-2 status-text-block whitespace-pre-wrap">${text}</div>
            </details>
        `;
    } else {
        fullTextHtml = `<div class="status-text-block whitespace-pre-wrap">${text}</div>`;
    }

    return `
        <div class="status-kv-grid">
            <div class="status-kv-key">Summary</div>
            <div class="status-kv-value">${details.summary}</div>
            <div class="status-kv-key">Full Text</div>
            <div class="status-kv-value">${fullTextHtml}</div>
        </div>
    `;
}

function _renderMetaPlanDetails(details) {
    if (!Array.isArray(details)) return null;

    let html = `<details class="text-xs" open>
                    <summary class="cursor-pointer text-gray-400 hover:text-white">Generated Plan (${details.length} steps)</summary>
                    <div class="space-y-3 mt-2">`;

    details.forEach(phase => {
        let argsHtml = '';
        if (phase.arguments) {
            const argsString = JSON.stringify(phase.arguments, null, 2);
            argsHtml = `
                <div class="status-kv-item">
                    <div class="status-kv-key">Args</div>
                    <div class="status-kv-value">
                        <details class="text-xs">
                            <summary class="cursor-pointer text-gray-400 hover:text-white">View Arguments</summary>
                            <div class="mt-2 p-2 status-text-block whitespace-pre-wrap">${argsString}</div>
                        </details>
                    </div>
                </div>
            `;
        }

        let structuralKeysHtml = '';
        if (phase.type) {
            structuralKeysHtml += `<div class="status-kv-item"><div class="status-kv-key">Type</div><div class="status-kv-value"><code class="status-code font-bold text-yellow-300">${phase.type}</code></div></div>`;
        }
        if (phase.loop_over) {
            structuralKeysHtml += `<div class="status-kv-item"><div class="status-kv-key">Loop Over</div><div class="status-kv-value"><code class="status-code">${phase.loop_over}</code></div></div>`;
        }

        html += `<div class="status-phase-card">
                    <div class="font-bold text-gray-300 mb-2">Step ${phase.phase}</div>
                    <div class="status-kv-item"><div class="status-kv-key">Goal</div><div class="status-kv-value">${phase.goal}</div></div>`;

        html += structuralKeysHtml;

        if (phase.relevant_tools) {
            html += `<div class="status-kv-item"><div class="status-kv-key">Tools</div><div class="status-kv-value"><code class="status-code">${phase.relevant_tools.join(', ')}</code></div></div>`;
        }
        if (phase.executable_prompt) {
            html += `<div class="status-kv-item"><div class="status-kv-key">Prompt</div><div class="status-kv-value"><code class="status-code">${phase.executable_prompt}</code></div></div>`;
        }
        html += `${argsHtml}</div>`;
    });
    html += '</div></details>';
    return html;
}

function _renderToolIntentDetails(details) {
    if (!details || (!details.tool_name && !details.prompt_name)) return null;

    const name = details.tool_name || details.prompt_name;
    const type = details.tool_name ? 'Tool' : 'Prompt';

    let argsHtml = '';
    if (details.arguments) {
        try {
             const argsString = JSON.stringify(details.arguments, null, 2);
             argsHtml = `
                <div class="status-kv-item">
                    <div class="status-kv-key">Args</div>
                    <div class="status-kv-value">
                        <details class="text-xs">
                            <summary class="cursor-pointer text-gray-400 hover:text-white">View Arguments</summary>
                            <div class="mt-2 p-2 status-text-block whitespace-pre-wrap">${argsString}</div>
                        </details>
                    </div>
                </div>
            `;
        } catch (e) {
            console.warn("Could not stringify arguments for tool intent:", details.arguments);
            argsHtml = `<div class="status-kv-item"><div class="status-kv-key">Args</div><div class="status-kv-value text-red-400">[Error displaying arguments]</div></div>`;
        }
    }

    return `
        <div class="status-kv-item"><div class="status-kv-key">${type}</div><div class="status-kv-value"><code class="status-code">${name}</code></div></div>
        ${argsHtml}
    `;
}

function _renderStandardStep(eventData, parentContainer, isFinal = false) {
    const { step, details, type } = eventData;

    // --- UX ENHANCEMENT ---
    // The "Calling LLM" step is transient; it shouldn't stay active.
    // We mark it as 'final' so it renders as completed immediately.
    // The subsequent "Plan Generated" step will become the active one.
    if (step?.startsWith("Calling LLM for")) {
        isFinal = true;
    }
    // --- END ENHANCEMENT ---

    const lastStep = document.getElementById(`status-step-${state.currentStatusId}`);
    if (lastStep && lastStep.classList.contains('active') && parentContainer && parentContainer.contains(lastStep)) {
        lastStep.classList.remove('active');
        lastStep.classList.add('completed');
        if (state.isInFastPath && !lastStep.classList.contains('plan-optimization')) {
            lastStep.classList.add('plan-optimization');
        }
    }

    if (type !== 'plan_optimization') {
        state.isInFastPath = false;
    } else {
        state.isInFastPath = true;
    }

    state.currentStatusId++;
    const stepEl = document.createElement('div');
    stepEl.id = `status-step-${state.currentStatusId}`;
    stepEl.className = 'status-step p-3 rounded-md mb-2'; // Added mb-2 for spacing

    const stepTitle = document.createElement('h4');
    stepTitle.className = 'font-bold text-sm text-white mb-2';
    stepTitle.textContent = step || (type === 'tool_result' ? 'Result' : (type === 'error' ? 'Error' : 'Details'));
    stepEl.appendChild(stepTitle);

    const metricsEl = document.createElement('div');
    metricsEl.className = 'per-call-metrics text-xs text-gray-400 mb-2 hidden';

    if (typeof details === 'object' && details !== null && details.call_id) {
        metricsEl.dataset.callId = details.call_id;
    }
    
    if (typeof details === 'object' && details !== null) {
        // Check for planner tokens (at the root of 'details')
        const planner_input = details.input_tokens;
        const planner_output = details.output_tokens;
        
        // Check for tool tokens (inside 'details.metadata')
        const tool_input = details.metadata?.input_tokens;
        const tool_output = details.metadata?.output_tokens;

        if (planner_input !== undefined && planner_output !== undefined) {
            metricsEl.innerHTML = `(LLM Call: ${planner_input.toLocaleString()} in / ${planner_output.toLocaleString()} out)`;
            metricsEl.classList.remove('hidden');
        } else if (tool_input !== undefined && tool_output !== undefined) {
            metricsEl.innerHTML = `(LLM Call: ${tool_input.toLocaleString()} in / ${tool_output.toLocaleString()} out)`;
            metricsEl.classList.remove('hidden');
        }
    }

    stepEl.appendChild(metricsEl);

    if (details) {
        let customRenderedHtml = null;
        let detailsString = '';

        if (typeof details === 'object' && details !== null) {
            if (step?.startsWith("Calling LLM for")) {
                customRenderedHtml = _renderPlanningDetails(details);
            } else if (type === "plan_generated") {
                customRenderedHtml = _renderMetaPlanDetails(details);
            } else if (type === "tool_intent") {
                customRenderedHtml = _renderToolIntentDetails(details);
            } else {
                try {
                    const cache = new Set();
                    detailsString = JSON.stringify(details, (key, value) => {
                        if (typeof value === 'object' && value !== null) {
                            if (cache.has(value)) {
                                return '[Circular Reference]';
                            }
                            cache.add(value);
                        }
                        return value;
                    }, 2);
                } catch (e) {
                    detailsString = "[Could not stringify details]";
                    console.error("Error stringifying details:", e, details);
                }
            }
        } else {
            detailsString = String(details);
        }

        if (customRenderedHtml) {
            const detailsContainer = document.createElement('div');
            detailsContainer.innerHTML = customRenderedHtml;
            stepEl.appendChild(detailsContainer);
        } else if (detailsString) {
            const characterThreshold = 300;
            if (detailsString.length > characterThreshold) {
                const detailsEl = document.createElement('details');
                detailsEl.className = 'text-xs';

                const summaryEl = document.createElement('summary');
                summaryEl.className = 'cursor-pointer text-gray-400 hover:text-white';

                let summaryText = `Details (${detailsString.length} chars)`;
                if ((step?.includes('Tool Execution Result') || step?.includes('Tool Execution Error')) && typeof details === 'object' && details !== null) {
                    if (details.results) {
                        const itemCount = Array.isArray(details.results) ? details.results.length : (details.results ? 1 : 0);
                        const status = details.status || 'unknown';
                        summaryText = `Tool Result (${status}, ${itemCount} items)`;
                    } else if (details.type === 'chart') {
                        summaryText = 'Chart Specification';
                    }
                } else if (step?.includes('Final Answer')) {
                    summaryText = `Final Answer Summary`;
                } else if (type === 'cancelled') {
                    summaryText = 'Cancellation Details';
                } else if (type === 'error') {
                    summaryText = 'Error Details';
                }

                summaryEl.textContent = `${summaryText} - Click to expand`;
                detailsEl.appendChild(summaryEl);

                const pre = document.createElement('pre');
                pre.className = 'mt-2 p-2 bg-gray-900/70 rounded-md text-gray-300 overflow-x-auto whitespace-pre-wrap';
                pre.textContent = detailsString;
                detailsEl.appendChild(pre);
                stepEl.appendChild(detailsEl);
            } else {
                const pre = document.createElement('pre');
                pre.className = 'p-2 bg-gray-900/70 rounded-md text-xs text-gray-300 overflow-x-auto whitespace-pre-wrap';
                pre.textContent = detailsString;
                stepEl.appendChild(pre);
            }
        }
    }

    parentContainer.appendChild(stepEl);

    if (type === 'workaround') {
        stepEl.classList.add('workaround');
    } else if (type === 'error') {
        stepEl.classList.add('error');
    } else if (type === 'cancelled') {
        stepEl.classList.add('cancelled');
    } else if (state.isInFastPath) {
        stepEl.classList.add('plan-optimization');
    }

    if (!isFinal) {
        stepEl.classList.add('active');
    } else {
        stepEl.classList.remove('active');
        if (!stepEl.classList.contains('error') && !stepEl.classList.contains('cancelled')) {
            stepEl.classList.add('completed');
        }
    }
}

/**
 * Resets the status window and its related state variables for a new execution.
 */
export function resetStatusWindowForNewTask() {
    DOM.statusWindowContent.innerHTML = '';
    state.currentStatusId = 0;
    state.isRestTaskActive = false;
    state.activeRestTaskId = null;
    state.currentPhaseContainerEl = null;
    state.phaseContainerStack = [];
    state.pendingSubtaskPlanningEvents = [];
    state.isInFastPath = false;
    setThinkingIndicator(false);
    // Reset title to default
    const statusTitle = DOM.statusTitle || document.getElementById('status-title');
    if (statusTitle) {
        statusTitle.textContent = 'Live Status';
    }
}

export function updateStatusWindow(eventData, isFinal = false, source = 'interactive', taskId = null) {
    const { step, details, type, metadata } = eventData;

    const statusTitle = DOM.statusTitle || document.getElementById('status-title');

    if (source === 'rest' && taskId) {
        // Check if this is the first event for a new or different REST task
        if (!state.isRestTaskActive || taskId !== state.activeRestTaskId) {
            resetStatusWindowForNewTask(); // Use the centralized reset function
            state.isRestTaskActive = true; // Set REST-specific state after reset
            state.activeRestTaskId = taskId;
            updateTaskIdDisplay(taskId); // Display the task ID
        }
        statusTitle.textContent = 'Live Status - REST'; // Removed redundant Task ID from title
    } else if (source === 'interactive') {
        // If the last active view was a REST task, reset the view
        if (state.isRestTaskActive) {
            resetStatusWindowForNewTask();
            updateTaskIdDisplay(null); // Hide the task ID
        }
        statusTitle.textContent = 'Live Status';
    }

    const execution_depth_from_details = details?.execution_depth ?? 0;
    const execution_depth_from_metadata = metadata?.execution_depth ?? 0;
    const execution_depth = Math.max(execution_depth_from_details, execution_depth_from_metadata);

    const isPlanningEvent = step?.startsWith("Calling LLM for") || type === "plan_generated";

    if (isPlanningEvent && execution_depth > 0 && type !== 'phase_start') {
        state.pendingSubtaskPlanningEvents.push(eventData);
        return;
    }

    if (!step && type !== 'phase_start' && type !== 'phase_end') {
        if (type !== 'tool_result' && type !== 'tool_error') {
            return;
        }
    }

    if (type === 'phase_start') {
        const { phase_num, total_phases, goal } = details;

        while (state.phaseContainerStack.length > execution_depth) {
            const oldContainer = state.phaseContainerStack.pop();
            if (oldContainer) {
                oldContainer.classList.add('completed');
            }
        }

        const parentContainer = state.phaseContainerStack.length > 0 ? state.phaseContainerStack[state.phaseContainerStack.length - 1].querySelector('.status-phase-content') : DOM.statusWindowContent;

        const lastStep = Array.from(parentContainer.querySelectorAll(':scope > .status-step')).pop();
        if (lastStep && lastStep.classList.contains('active')) {
            lastStep.classList.remove('active');
            if (!lastStep.classList.contains('plan-optimization')) {
                 lastStep.classList.add('completed');
            }
        }

        const phaseContainer = document.createElement('details');
        phaseContainer.className = 'status-phase-container';
        phaseContainer.open = false; 

        const phaseHeader = document.createElement('summary');
        phaseHeader.className = 'status-phase-header phase-start';

        let depthIndicator = '';
        if (execution_depth > 0) {
            depthIndicator = '↳ '.repeat(execution_depth);
        }

        phaseHeader.innerHTML = `
            <span class="font-bold flex-shrink-0">${depthIndicator}Plan Step ${phase_num}/${total_phases}</span>
            <span class="text-gray-400 text-xs truncate ml-2">${goal}</span>
        `;

        phaseContainer.appendChild(phaseHeader);

        const phaseContent = document.createElement('div');
        phaseContent.className = 'status-phase-content';
        phaseContainer.appendChild(phaseContent);

        if (execution_depth > 0 && state.pendingSubtaskPlanningEvents.length > 0) {
            state.pendingSubtaskPlanningEvents.forEach(event => {
                _renderStandardStep(event, phaseContent, false);
            });
            state.pendingSubtaskPlanningEvents = [];
        }

        parentContainer.appendChild(phaseContainer);
        state.phaseContainerStack.push(phaseContainer);
        state.currentPhaseContainerEl = phaseContainer;

        if (!state.isMouseOverStatus) {
            DOM.statusWindowContent.scrollTop = DOM.statusWindowContent.scrollHeight;
        }
        return;
    }

    if (type === 'phase_end') {
        const containerToEnd = state.phaseContainerStack.pop();
        if (containerToEnd) {
            const phaseContent = containerToEnd.querySelector('.status-phase-content');
            if (phaseContent) {
                const lastStepInPhase = Array.from(phaseContent.childNodes).filter(node => node.classList && node.classList.contains('status-step')).pop();
                if (lastStepInPhase && lastStepInPhase.classList.contains('active')) {
                    lastStepInPhase.classList.remove('active');
                    lastStepInPhase.classList.add('completed');
                }
            }

            const { phase_num, total_phases, status } = details;
            const phaseFooter = document.createElement('div');
            phaseFooter.className = 'status-phase-header phase-end';
            phaseFooter.innerHTML = `<span class="font-bold">Plan Step ${phase_num}/${total_phases} Completed</span>`;

            if (status === 'skipped') {
                phaseFooter.classList.add('skipped');
                phaseFooter.innerHTML = `<span class="font-bold">Plan Step ${phase_num}/${total_phases} Skipped</span>`;
            } else {
                containerToEnd.classList.add('completed');
            }

            containerToEnd.appendChild(phaseFooter);
        }
        state.currentPhaseContainerEl = state.phaseContainerStack.length > 0 ? state.phaseContainerStack[state.phaseContainerStack.length - 1] : null;
        state.isInFastPath = false;
        if (!state.isMouseOverStatus) {
            DOM.statusWindowContent.scrollTop = DOM.statusWindowContent.scrollHeight;
        }
        return;
    }

    const parentEl = state.currentPhaseContainerEl ? state.currentPhaseContainerEl.querySelector('.status-phase-content') : DOM.statusWindowContent;
    _renderStandardStep(eventData, parentEl, isFinal);

    if (!state.isMouseOverStatus) {
        DOM.statusWindowContent.scrollTop = DOM.statusWindowContent.scrollHeight;
    }
}

/**
 * Updates the display of the current task ID in the status window header.
 * Includes functionality to copy the task ID to the clipboard.
 * @param {string|null} taskId - The task ID to display, or null to hide the display.
 */
export function updateTaskIdDisplay(taskId) {
    if (DOM.taskIdDisplay && DOM.taskIdValue && DOM.copyTaskIdButton) {
        if (taskId) {
            DOM.taskIdValue.textContent = `Task ID: ${taskId.substring(0, 8)}...`;
            DOM.taskIdDisplay.classList.remove('hidden');

            // Remove any existing event listener to prevent duplicates
            DOM.copyTaskIdButton.onclick = null; 
            DOM.copyTaskIdButton.onclick = () => {
                navigator.clipboard.writeText(taskId).then(() => {
                    // Provide visual feedback
                    const originalIcon = DOM.copyTaskIdButton.innerHTML;
                    DOM.copyTaskIdButton.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-green-500" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" /></svg>`;
                    setTimeout(() => {
                        DOM.copyTaskIdButton.innerHTML = originalIcon;
                    }, 2000);
                }).catch(err => {
                    console.error('Failed to copy task ID: ', err);
                });
            };
        } else {
            DOM.taskIdDisplay.classList.add('hidden');
            DOM.taskIdValue.textContent = '';
            DOM.copyTaskIdButton.onclick = null; // Clear event listener
        }
    }
}

/**
 * Provides a visual cue on a session in the list to show it has new, unseen activity.
 * @param {string} sessionId The ID of the session to highlight.
 */
export function highlightSession(sessionId) {
    const sessionItem = document.getElementById(`session-${sessionId}`);
    if (sessionItem && !sessionItem.classList.contains('active')) {
        const nameSpan = sessionItem.querySelector('.session-name-span');
        if (nameSpan) {
            nameSpan.classList.add('font-bold', 'text-teradata-orange');
        }
        // Add a blinking dot or similar indicator
        let indicator = sessionItem.querySelector('.new-activity-indicator');
        if (!indicator) {
            indicator = document.createElement('span');
            indicator.className = 'new-activity-indicator';
            sessionItem.querySelector('.flex').prepend(indicator);
        }
    }
}

/**
 * Moves a session item to the top of the session list.
 * @param {string} sessionId - The ID of the session to move.
 */
export function moveSessionToTop(sessionId) {
    const sessionItem = document.getElementById(`session-${sessionId}`);
    if (sessionItem && DOM.sessionList) {
        // Remove the item from its current position
        sessionItem.remove();
        // Prepend it to the session list
        DOM.sessionList.prepend(sessionItem);
        console.log(`UI Updated: Session ${sessionId} moved to top.`);
    }
}


export function updateTokenDisplay(data) {
    const normalDisplay = document.getElementById('token-normal-display');
    const awsMessage = document.getElementById('token-aws-message');

    if (state.currentProvider === 'Amazon') {
        normalDisplay.classList.add('hidden');
        awsMessage.classList.remove('hidden');
        return;
    }

    normalDisplay.classList.remove('hidden');
    awsMessage.classList.add('hidden');

    document.getElementById('statement-input-tokens').textContent = (data.statement_input || 0).toLocaleString();
    document.getElementById('statement-output-tokens').textContent = (data.statement_output || 0).toLocaleString();
    document.getElementById('total-input-tokens').textContent = (data.total_input || 0).toLocaleString();
    document.getElementById('total-output-tokens').textContent = (data.total_output || 0).toLocaleString();
}

// --- MODIFICATION START: Add function to refresh all feedback button states ---
/**
 * Refreshes all feedback button states based on current state.feedbackByTurn.
 * Should be called after loading a session to restore visual feedback state.
 */
export function refreshFeedbackButtons() {
    // Find all feedback wrappers in the chat
    const feedbackWrappers = document.querySelectorAll('[data-turn-id]');
    
    feedbackWrappers.forEach(wrapper => {
        const turnId = parseInt(wrapper.dataset.turnId);
        if (isNaN(turnId)) return;
        
        const upBtn = wrapper.querySelector('[data-vote="up"]');
        const downBtn = wrapper.querySelector('[data-vote="down"]');
        
        if (!upBtn || !downBtn) return;
        
        const current = state.feedbackByTurn[turnId] || 'none';
        
        // Update active states
        upBtn.classList.toggle('active', current === 'up');
        downBtn.classList.toggle('active', current === 'down');
        
        // Update aria attributes
        upBtn.setAttribute('aria-pressed', current === 'up' ? 'true' : 'false');
        downBtn.setAttribute('aria-pressed', current === 'down' ? 'true' : 'false');
        
        // Update visual styling
        if (current === 'up') {
            upBtn.classList.remove('text-gray-300');
            upBtn.classList.add('text-[#F15F22]', 'bg-gray-800/60');
            downBtn.classList.add('text-gray-300');
            downBtn.classList.remove('text-[#F15F22]', 'bg-gray-800/60');
        } else if (current === 'down') {
            downBtn.classList.remove('text-gray-300');
            downBtn.classList.add('text-[#F15F22]', 'bg-gray-800/60');
            upBtn.classList.add('text-gray-300');
            upBtn.classList.remove('text-[#F15F22]', 'bg-gray-800/60');
        } else {
            upBtn.classList.add('text-gray-300');
            upBtn.classList.remove('text-[#F15F22]', 'bg-gray-800/60');
            downBtn.classList.add('text-gray-300');
            downBtn.classList.remove('text-[#F15F22]', 'bg-gray-800/60');
        }
    });
}
// --- MODIFICATION END ---

export function setThinkingIndicator(isThinking) {
    if (isThinking) {
        DOM.promptNameDisplay.classList.add('hidden');
        DOM.thinkingIndicator.classList.remove('hidden');
        DOM.thinkingIndicator.classList.add('flex');
    } else {
        DOM.thinkingIndicator.classList.add('hidden');
        DOM.thinkingIndicator.classList.remove('flex');
        DOM.promptNameDisplay.classList.remove('hidden');
    }
}

export function updateStatusPromptName(provider = null, model = null, isHistorical = false) {
    const promptNameDiv = document.getElementById('prompt-name-display');

    // Use the provided args, or fall back to the global state
    const providerToShow = provider || state.currentProvider;
    const modelToShow = model || state.currentModel;

    if (providerToShow && modelToShow) {
        const isCustom = isPromptCustomForModel(providerToShow, modelToShow);
        const promptType = isPrivilegedUser() ? (isCustom ? 'Custom' : 'Default') : 'Default (Server-Side)';
        
        // Add a visual indicator if we are showing a *historical* turn's model
        const historicalIndicator = isHistorical ? ' (History)' : '';

        promptNameDiv.innerHTML = `
            <span class="font-semibold text-gray-300">${promptType} Prompt${historicalIndicator}</span>
            <span class="text-gray-500">/</span>
            <span class="font-mono text-teradata-orange text-xs">${providerToShow}/${getNormalizedModelId(modelToShow)}</span>
        `;
    } else {
        promptNameDiv.innerHTML = '<span>No Model/Prompt Loaded</span>';
    }
}


export function createResourceItem(resource, type) {
    const detailsEl = document.createElement('details');
    detailsEl.id = `resource-${type}-${resource.name}`;
    detailsEl.className = 'resource-item bg-gray-800/50 rounded-lg border border-gray-700/60';

    if (resource.disabled) {
        detailsEl.classList.add('opacity-60');
        detailsEl.title = `This ${type.slice(0, -1)} is disabled and will not be used by the agent.`;
    }

    const toggleIcon = resource.disabled ?
        `<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M3.707 2.293a1 1 0 00-1.414 1.414l14 14a1 1 0 001.414-1.414l-1.473-1.473A10.014 10.014 0 0019.542 10C18.268 5.943 14.478 3 10 3a9.958 9.958 0 00-4.512 1.074L3.707 2.293zM10 12a2 2 0 110-4 2 2 0 010 4z" clip-rule="evenodd" /><path d="M2 10s3.939 4 8 4 8-4 8-4-3.939-4-8-4-8 4-8 4zm13.707 4.293a1 1 0 00-1.414-1.414L12.586 14.6A8.007 8.007 0 0110 16c-4.478 0-8.268-2.943-9.542-7 .946-2.317 2.83-4.224 5.166-5.447L2.293 1.293A1 1 0 00.879 2.707l14 14a1 1 0 001.414 0z" /></svg>` :
        `<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path d="M10 12a2 2 0 100-4 2 2 0 000 4z" /><path fill-rule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.022 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clip-rule="evenodd" /></svg>`;

    let argsHTML = '';
    if (resource.arguments && resource.arguments.length > 0) {
        argsHTML += `<div class="mt-4 pt-3 border-t border-gray-700/60">
                                <h5 class="font-semibold text-sm text-white mb-2">Parameters</h5>
                                <ul class="space-y-2 text-xs">`;
        resource.arguments.forEach(arg => {
            const requiredText = arg.required ? '<span class="text-red-400 font-bold">Required</span>' : '<span class="text-gray-400">Optional</span>';
            const typeText = arg.type && arg.type !== 'unknown' ? `<span class="font-mono text-xs text-cyan-400 bg-cyan-400/10 px-1.5 py-0.5 rounded-md">${arg.type}</span>` : '';

            argsHTML += `<li class="p-2 bg-black/20 rounded-md">
                                    <div class="flex justify-between items-center">
                                        <div class="flex items-center gap-x-2">
                                            <code class="font-semibold text-teradata-orange">${arg.name}</code>
                                            ${typeText}
                                        </div>
                                        ${requiredText}
                                    </div>
                                    <p class="text-gray-400 mt-1">${arg.description}</p>
                                 </li>`;
        });
        argsHTML += `</ul></div>`;
    }

    let contentHTML = '';
    if (type === 'prompts') {
        const runButtonDisabledAttr = ''; // Always enabled
        const runButtonTitle = 'Run this prompt.'; // Always use this title

        contentHTML = `
            <div class="p-3 pt-2 text-sm text-gray-300 space-y-3">
                <p>${resource.description}</p>
                ${argsHTML}
                <div class="flex justify-end items-center gap-x-2 pt-3 border-t border-gray-700/60">
                    <button class="prompt-toggle-button p-1.5 text-gray-300 hover:text-white hover:bg-white/10 rounded-md transition-colors">${toggleIcon}</button>
                    <button class="view-prompt-button px-3 py-1 bg-gray-600 text-white text-xs font-semibold rounded-md hover:bg-gray-500 transition-colors">Prompt</button>
                    <button class="run-prompt-button px-3 py-1 bg-teradata-orange text-white text-xs font-semibold rounded-md hover:bg-teradata-orange-dark transition-colors" ${runButtonDisabledAttr} title="${runButtonTitle}">Run</button>
                </div>
            </div>`;
    } else if (type === 'tools') {
        contentHTML = `
            <div class="p-3 pt-2 text-sm text-gray-300 space-y-3">
                <p>${resource.description}</p>
                ${argsHTML}
                <div class="flex justify-end items-center pt-3 border-t border-gray-700/60">
                    <button class="tool-toggle-button p-1.5 text-gray-300 hover:text-white hover:bg-white/10 rounded-md transition-colors">${toggleIcon}</button>
                </div>
            </div>`;
    } else { // For resources
        contentHTML = `
            <div class="p-3 pt-2 text-sm text-gray-300 border-t border-gray-700/60 flex justify-between items-center">
                <p>${resource.description}</p>
            </div>`;
    }

    detailsEl.innerHTML = `
        <summary class="flex justify-between items-center p-3 font-semibold text-white hover:bg-gray-700/50 rounded-lg transition-colors cursor-pointer">
            <span>${resource.name}</span>
            <svg class="chevron w-5 h-5 text-[#F15F22] flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>
        </summary>
        ${contentHTML}
    `;

    return detailsEl;
}

export function updatePromptsTabCounter() {
    const tabButton = document.querySelector('.resource-tab[data-type="prompts"]');
    if (!tabButton || !state.resourceData.prompts) return;
    let totalCount = 0;
    let disabledCount = 0;
    Object.values(state.resourceData.prompts).forEach(items => {
        totalCount += items.length;
        disabledCount += items.filter(item => item.disabled).length;
    });
    const disabledIndicator = disabledCount > 0 ? '*' : '';
    tabButton.textContent = `Prompts (${totalCount})${disabledIndicator}`;
}

export function updateToolsTabCounter() {
    const tabButton = document.querySelector('.resource-tab[data-type="tools"]');
    if (!tabButton || !state.resourceData.tools) return;
    let totalCount = 0;
    let disabledCount = 0;
    Object.values(state.resourceData.tools).forEach(items => {
        totalCount += items.length;
        disabledCount += items.filter(item => item.disabled).length;
    });
    const disabledIndicator = disabledCount > 0 ? '*' : '';
    tabButton.textContent = `Tools (${totalCount})${disabledIndicator}`;
}

export function highlightResource(resourceName, type) {
    if (state.currentlySelectedResource) {
        state.currentlySelectedResource.classList.remove('resource-selected');
    }

    let resourceCategory = null;
    if (state.resourceData[type]) {
        for (const category in state.resourceData[type]) {
            if (state.resourceData[type][category].some(r => r.name === resourceName)) {
                resourceCategory = category;
                break;
            }
        }
    }


    if (resourceCategory) {
        const resourceTab = document.querySelector(`.resource-tab[data-type="${type}"]`);
        if (resourceTab) resourceTab.click();

        const categoryTab = document.querySelector(`.category-tab[data-type="${type}"][data-category="${resourceCategory}"]`);
        if(categoryTab) categoryTab.click();

        const resourceElement = document.getElementById(`resource-${type}-${resourceName}`);
        if (resourceElement) {
            resourceElement.open = true;
            resourceElement.classList.add('resource-selected');
            state.currentlySelectedResource = resourceElement;

            setTimeout(() => {
                resourceElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 350);
        }
    } else {
        console.warn(`Could not find category for resource '${resourceName}' of type '${type}'. Highlight failed.`);
    }
}

export function addSessionToList(session, isActive = false) {
    const sessionItem = document.createElement('div');
    sessionItem.id = `session-${session.id}`;
    sessionItem.dataset.sessionId = session.id;
    sessionItem.className = 'session-item w-full text-left p-3 rounded-lg hover:bg-white/10 transition-colors cursor-pointer';

    if (isActive) {
        document.querySelectorAll('.session-item').forEach(item => item.classList.remove('active'));
        sessionItem.classList.add('active');
    }

    const contentWrapper = document.createElement('div');
    contentWrapper.className = 'w-full flex flex-col';

    const topRow = document.createElement('div');
    topRow.className = 'flex justify-between items-center';

    const nameSpan = document.createElement('span');
    nameSpan.className = 'session-name-span font-semibold text-sm text-white truncate';
    nameSpan.textContent = session.name;
    topRow.appendChild(nameSpan);

    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'session-actions flex-shrink-0 flex items-center';

    const editButton = document.createElement('button');
    editButton.type = 'button';
    editButton.className = 'session-action-button session-edit-button';
    editButton.title = 'Rename session';
    editButton.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor"><path d="M13.586 3.586a2 2 0 112.828 2.828l-11.202 11.202a.5.5 0 01-.293.146H3.5a.5.5 0 01-.5-.5v-1.414a.5.5 0 01.146-.293l11.202-11.202zM15.707 2.293a1 1 0 010 1.414L5.414 14H4v-1.414L14.293 2.293a1 1 0 011.414 0z" /></svg>`;
    actionsDiv.appendChild(editButton);

    const deleteButton = document.createElement('button');
    deleteButton.type = 'button';
    deleteButton.className = 'session-action-button session-delete-button';
    deleteButton.title = 'Delete session';
    deleteButton.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M6 2a2 2 0 00-2 2v12a2 2 0 002 2h8a2 2 0 002-2V4a2 2 0 00-2-2H6zm2 3a1 1 0 11-2 0 1 1 0 012 0zm4 0a1 1 0 11-2 0 1 1 0 012 0z" clip-rule="evenodd" /></svg>`;
    actionsDiv.appendChild(deleteButton);

    const copyButton = document.createElement('button');
    copyButton.type = 'button';
    copyButton.className = 'session-action-button session-copy-button';
    copyButton.title = 'Copy session ID';
    copyButton.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor"><path d="M7 3a1 1 0 000 2h6a1 1 0 100-2H7zM4 7a1 1 0 011-1h10a1 1 0 110 2H5a1 1 0 01-1-1zM5 11a1 1 0 100 2h4a1 1 0 100-2H5z" /></svg>`;
    copyButton.addEventListener('click', (e) => {
        e.stopPropagation();
        const sessionId = sessionItem.dataset.sessionId;
        navigator.clipboard.writeText(sessionId).then(() => {
            copyButton.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-green-500" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" /></svg>`;
            setTimeout(() => {
                copyButton.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor"><path d="M7 3a1 1 0 000 2h6a1 1 0 100-2H7zM4 7a1 1 0 011-1h10a1 1 0 110 2H5a1 1 0 01-1-1zM5 11a1 1 0 100 2h4a1 1 0 100-2H5z" /></svg>`;
            }, 2000);
        }).catch(err => {
            console.error('Failed to copy session ID: ', err);
        });
    });
    actionsDiv.appendChild(copyButton);

    topRow.appendChild(actionsDiv);
    contentWrapper.appendChild(topRow);

    const lastUpdatedSpan = document.createElement('span');
    lastUpdatedSpan.className = 'session-last-updated text-xs text-gray-300 mt-1';
    if (session.last_updated && session.last_updated !== "Unknown") {
        lastUpdatedSpan.textContent = `Updated: ${new Date(session.last_updated).toLocaleString()}`;
    } else {
        lastUpdatedSpan.textContent = 'Updated: Unknown';
    }
    contentWrapper.appendChild(lastUpdatedSpan);

    const modelsDiv = document.createElement('div');
    modelsDiv.className = 'session-models text-xs text-gray-400 mt-1 flex flex-wrap gap-1';
    if (session.models_used && Array.isArray(session.models_used)) {
        session.models_used.forEach(modelString => {
            const modelSpan = document.createElement('span');
            modelSpan.className = 'inline-block bg-gray-700 rounded-full px-2 py-0.5 text-xs font-medium text-gray-300';
            modelSpan.textContent = modelString;
            modelsDiv.appendChild(modelSpan);
        });
    }
    contentWrapper.appendChild(modelsDiv);

    sessionItem.appendChild(contentWrapper);

    return sessionItem;
}

/**
 * Updates the displayed name of a session item in the history list.
 * @param {string} sessionId - The ID of the session to update.
 * @param {string} newName - The new name for the session.
 */
export function updateSessionListItemName(sessionId, newName) {
    console.log(`[ui.js] updateSessionListItemName called with sessionId=${sessionId}, newName=${newName}`);
    const sessionItem = document.getElementById(`session-${sessionId}`);
    if (sessionItem) {
        console.log(`[ui.js] Found sessionItem for sessionId=${sessionId}`);
        const nameSpan = sessionItem.querySelector('.session-name-span');
        if (nameSpan) {
            nameSpan.textContent = newName;
            console.log(`[ui.js] UI Updated: Session item ${sessionId} name changed to '${newName}'`);
        } else {
            console.warn(`[ui.js] Could not find name span within session item ${sessionId}`);
        }
    } else {
        console.warn(`[ui.js] Could not find session item ${sessionId} in the list to update name.`);
    }
}

export function updateSessionModels(sessionId, models_used) {
    const sessionItem = document.getElementById(`session-${sessionId}`);
    if (sessionItem) {
        let modelsDiv = sessionItem.querySelector('.session-models');
        if (!modelsDiv) {
            modelsDiv = document.createElement('div');
            modelsDiv.className = 'session-models text-xs text-gray-400 mt-1 flex flex-wrap gap-1';
            const contentWrapper = sessionItem.querySelector('.w-full');
            if(contentWrapper) {
                contentWrapper.appendChild(modelsDiv);
            }
        }
        modelsDiv.innerHTML = ''; // Clear existing models
        if (models_used && Array.isArray(models_used)) {
            models_used.forEach(modelString => {
                const modelSpan = document.createElement('span');
                modelSpan.className = 'inline-block bg-gray-700 rounded-full px-2 py-0.5 text-xs font-medium text-gray-300';
                modelSpan.textContent = modelString;
                modelsDiv.appendChild(modelSpan);
            });
        }

        if (state.currentSessionId === sessionId) {
            document.querySelectorAll('.session-item').forEach(item => item.classList.remove('active'));
            sessionItem.classList.add('active');
        }
    }
}

export function updateSessionTimestamp(sessionId, last_updated) {
    const sessionItem = document.getElementById(`session-${sessionId}`);
    if (sessionItem) {
        let lastUpdatedSpan = sessionItem.querySelector('.session-last-updated');
        if (!lastUpdatedSpan) {
            lastUpdatedSpan = document.createElement('span');
            lastUpdatedSpan.className = 'session-last-updated text-xs text-gray-300';
            const infoDiv = sessionItem.querySelector('.flex-col');
            if (infoDiv) {
                const nameSpan = infoDiv.querySelector('.session-name-span');
                if (nameSpan) {
                    nameSpan.after(lastUpdatedSpan);
                } else {
                    infoDiv.prepend(lastUpdatedSpan);
                }
            }
        }
        lastUpdatedSpan.textContent = `Updated: ${new Date(last_updated).toLocaleString()}`;
    }
}

/**
 * Removes a session item from the history list in the DOM.
 * @param {string} sessionId - The ID of the session to remove.
 */
export function removeSessionFromList(sessionId) {
    const sessionItem = document.getElementById(`session-${sessionId}`);
    if (sessionItem) {
        sessionItem.remove();
        console.log(`UI Updated: Removed session item ${sessionId} from list.`);
    } else {
        console.warn(`Could not find session item ${sessionId} in the list to remove.`);
    }
}


/**
 * Switches a session list item's name span to an input field for editing.
 * @param {HTMLButtonElement} editButton - The edit button element that was clicked.
 */
export function enterSessionEditMode(editButton) {
    const sessionItem = editButton.closest('.session-item');
    if (!sessionItem || sessionItem.querySelector('.session-edit-input')) {
        return;
    }

    const spanElement = sessionItem.querySelector('.session-name-span');
    const actionsDiv = sessionItem.querySelector('.session-actions');
    if (!spanElement || !actionsDiv) return;

    const currentName = spanElement.textContent;
    const inputElement = document.createElement('input');
    inputElement.type = 'text';
    inputElement.value = currentName;
    inputElement.dataset.originalName = currentName;
    inputElement.className = 'session-edit-input flex-grow min-w-0 w-full p-1 bg-gray-800 border border-gray-600 rounded-md text-sm text-white'; // Added flex-grow and adjusted colors

    spanElement.style.display = 'none';
    actionsDiv.style.display = 'none';

    const topRow = sessionItem.querySelector('.flex.justify-between.items-center');
    if (!topRow) return; // Should not happen if addSessionToList creates it correctly

    // Ensure the topRow is a flex container that allows the input to grow
    topRow.classList.add('flex', 'items-center'); // Ensure flex properties are present
    spanElement.replaceWith(inputElement);

    inputElement.focus();
    inputElement.select();

    inputElement.addEventListener('blur', handleSessionRenameSave);
    inputElement.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            handleSessionRenameSave(e);
        } else if (e.key === 'Escape') {
            handleSessionRenameCancel(e);
        }
    });
}

/**
 * Switches a session list item back from input mode to display mode.
 * @param {HTMLInputElement} inputElement - The input element currently being edited.
 * @param {string} finalName - The name to display in the span (either original or new).
 */
export function exitSessionEditMode(inputElement, finalName) {
    const sessionItem = inputElement.closest('.session-item');
    if (!sessionItem) return;

    // Create a new span element to replace the input field
    const newSpanElement = document.createElement('span');
    newSpanElement.className = 'session-name-span text-white text-sm font-semibold truncate'; // Ensure original classes are applied
    newSpanElement.textContent = finalName;

    // Replace the input element with the new span element
    inputElement.replaceWith(newSpanElement);

    const actionsDiv = sessionItem.querySelector('.session-actions');
    if (actionsDiv) {
        actionsDiv.style.display = ''; // Show actions div again
    }

    inputElement.removeEventListener('blur', handleSessionRenameSave);
}


export function updateConfigButtonState() {
    const isConnected = DOM.mcpStatusDot.classList.contains('connected');

    if (!isConnected) {
        DOM.configActionButtonText.textContent = 'Connect & Load';
        DOM.configActionButton.type = 'submit';
        DOM.configActionButton.classList.remove('bg-gray-600', 'hover:bg-gray-500');
        DOM.configActionButton.classList.add('bg-[#F15F22]', 'hover:bg-[#D9501A]');
        DOM.configActionButton.disabled = false; // Ensure it's enabled if not connected
        return;
    }

    const formData = new FormData(DOM.configForm);
    const currentConfig = Object.fromEntries(formData.entries());
    const hasChanged = JSON.stringify(currentConfig) !== JSON.stringify(state.pristineConfig);

    if (hasChanged) {
        DOM.configActionButtonText.textContent = 'Reconnect & Load';
        DOM.configActionButton.type = 'submit';
        DOM.configActionButton.classList.remove('bg-gray-600', 'hover:bg-gray-500');
        DOM.configActionButton.classList.add('bg-[#F15F22]', 'hover:bg-[#D9501A]');
        DOM.configActionButton.disabled = false; // Enable for submission
    } else {
        // MODIFICATION: If connected and unchanged, just disable the button. No "Close" action.
        DOM.configActionButtonText.textContent = 'Reconnect & Load'; // Keep the text
        DOM.configActionButton.type = 'submit'; // Always a submit button
        DOM.configActionButton.classList.remove('bg-[#F15F22]', 'hover:bg-[#D9501A]');
        DOM.configActionButton.classList.add('bg-gray-600', 'hover:bg-gray-500');
        DOM.configActionButton.disabled = true; // Disable as it's unchanged
    }
}

export function showConfirmation(title, body, onConfirm) {
    DOM.confirmModalTitle.textContent = title;
    DOM.confirmModalBody.textContent = body;

    DOM.confirmModalOverlay.classList.remove('hidden', 'opacity-0');
    DOM.confirmModalContent.classList.remove('scale-95', 'opacity-0');

    const confirmHandler = () => {
        onConfirm();
        closeConfirmation();
    };

    const cancelHandler = () => {
        closeConfirmation();
    };

    const closeConfirmation = () => {
        DOM.confirmModalOverlay.classList.add('opacity-0');
        DOM.confirmModalContent.classList.add('scale-95', 'opacity-0');
        setTimeout(() => DOM.confirmModalOverlay.classList.add('hidden'), 300);
        DOM.confirmModalConfirm.removeEventListener('click', confirmHandler);
        DOM.confirmModalCancel.removeEventListener('click', cancelHandler);
    };

    DOM.confirmModalConfirm.addEventListener('click', confirmHandler, { once: true });
    DOM.confirmModalCancel.addEventListener('click', cancelHandler, { once: true });
}

export function updatePromptEditorState() {
    const hasChanged = DOM.promptEditorTextarea.value.trim() !== DOM.promptEditorTextarea.dataset.initialValue.trim();
    DOM.promptEditorSave.disabled = !hasChanged;

    let statusText = isPromptCustomForModel(state.currentProvider, state.currentModel) ? 'Custom' : 'Default';
    let statusClass = 'text-sm text-gray-400';

    if (hasChanged) {
        statusText = 'Unsaved Changes';
        statusClass = 'text-sm text-yellow-400';
    }

    DOM.promptEditorStatus.textContent = statusText;
    DOM.promptEditorStatus.className = statusClass;
}

export function addMessageToModal(role, content) {
    const messageEl = document.createElement('div');
    messageEl.className = `p-3 rounded-lg max-w-xs ${role === 'user' ? 'bg-blue-600 self-end' : 'bg-gray-600 self-start'}`;
    messageEl.textContent = content;
    DOM.chatModalLog.appendChild(messageEl);
    DOM.chatModalLog.scrollTop = DOM.chatModalLog.scrollHeight;
}

export function updateHintAndIndicatorState() {
    const hintTextSpan = DOM.inputHint.querySelector('span:first-child');
    const hintTooltipSpan = DOM.inputHint.querySelector('.tooltip');

    if (state.isLastTurnModeLocked) {
        hintTextSpan.innerHTML = `<strong>Turn Summaries Context:</strong> <span class="text-orange-400 font-semibold">Locked</span>`;
        hintTooltipSpan.innerHTML = `'Turn Summaries' context is locked on. Press <kbd>Shift</kbd> + <kbd>Alt</kbd> to switch back to the default 'Full Session Context'.`;
        DOM.contextStatusDot.className = 'connection-dot context-last-turn-locked';
        DOM.sendIcon.classList.remove('flipped');
    } else if (state.isTempLastTurnMode) {
        hintTextSpan.innerHTML = `<strong>Context:</strong> <span class="text-yellow-400 font-semibold">Turn Summaries</span>`;
        hintTooltipSpan.innerHTML = `Temporarily using 'Turn Summaries' context for this query.`;
        DOM.contextStatusDot.className = 'connection-dot context-last-turn-temp';
        DOM.sendIcon.classList.remove('flipped');
    } else {
        hintTextSpan.innerHTML = `<strong>Full Session Context:</strong> <span class="text-green-400 font-semibold">On</span>`;
        hintTooltipSpan.innerHTML = `Full session context is the default. Hold <kbd>Alt</kbd> to temporarily use 'Turn Summaries' context. Press <kbd>Shift</kbd> + <kbd>Alt</kbd> to lock 'Turn Summaries' context on.`;
        DOM.contextStatusDot.className = 'connection-dot idle';
        DOM.sendIcon.classList.add('flipped');
    }
}

export function updateVoiceModeUI() {
    const isActive = state.isVoiceModeLocked || state.isTempVoiceMode || state.ttsState === 'AWAITING_OBSERVATION_CONFIRMATION';

    if (isActive) {
        DOM.voiceInputButton.classList.remove('bg-gray-600');
        DOM.voiceInputButton.classList.add('bg-[#F15F22]');
    } else {
        DOM.voiceInputButton.classList.add('bg-gray-600');
        DOM.voiceInputButton.classList.remove('bg-[#F115F22]'); // Typo fixed from original
    }

    let tooltipText = "Voice Conversation";
    if (state.ttsState === 'AWAITING_OBSERVATION_CONFIRMATION') {
        tooltipText += " (Listening for confirmation)";
    } else if (state.isVoiceModeLocked) {
        tooltipText += " (Locked On)";
    } else if (state.isTempVoiceMode) {
        tooltipText += " (Active)";
    } else {
        tooltipText += " (Hold Ctrl)";
    }
    DOM.voiceInputButton.title = tooltipText;

    if (isActive) {
        console.log("Voice mode activated.");
    } else {
        console.log("Voice mode deactivated.");
    }
}

export function updateKeyObservationsModeUI() {
    DOM.observationsAutoplayOffIcon.classList.add('hidden');
    DOM.observationsAutoplayOnIcon.classList.add('hidden');
    DOM.observationsOffIcon.classList.add('hidden');
    DOM.keyObservationsToggleButton.classList.remove('autoplay-on', 'off');

    switch (state.keyObservationsMode) {
        case 'autoplay-on':
            DOM.observationsAutoplayOnIcon.classList.remove('hidden');
            DOM.keyObservationsToggleButton.title = 'Key Observations - Autoplay On';
            DOM.keyObservationsToggleButton.classList.add('autoplay-on');
            break;
        case 'off':
            DOM.observationsOffIcon.classList.remove('hidden');
            DOM.keyObservationsToggleButton.title = 'Key Observations - Off';
            DOM.keyObservationsToggleButton.classList.add('off');
            break;
        case 'autoplay-off':
        default:
            DOM.observationsAutoplayOffIcon.classList.remove('hidden');
            DOM.keyObservationsToggleButton.title = 'Key Observations - Autoplay Off';
            break;
    }
}

// export function closeConfigModal() {
//     DOM.configModalOverlay.classList.add('opacity-0');
//     DOM.configModalContent.classList.add('scale-95', 'opacity-0');
//     setTimeout(() => DOM.configModalOverlay.classList.add('hidden'), 300);
// }

export function closePromptModal() {
    DOM.promptModalOverlay.classList.add('opacity-0');
    DOM.promptModalContent.classList.add('scale-95', 'opacity-0');
    setTimeout(() => DOM.promptModalOverlay.classList.add('hidden'), 300);
}

export function closeViewPromptModal() {
    DOM.viewPromptModalOverlay.classList.add('opacity-0');
    DOM.viewPromptModalContent.classList.add('scale-95', 'opacity-0');
    setTimeout(() => DOM.viewPromptModalOverlay.classList.add('hidden'), 300);
}

/**
 * Displays the RAG Case modal with the provided case data.
 * @param {object} caseData - The full RAG case data to display.
 */
export function showRagCaseModal(caseData) {
    if (!DOM.ragCaseModalOverlay || !DOM.ragCaseModalContent || !DOM.ragCaseIdDisplay || !DOM.ragCaseModalJson) {
        console.error("RAG Case modal DOM elements not found.");
        return;
    }

    DOM.ragCaseIdDisplay.textContent = caseData.case_id || 'N/A';
    DOM.ragCaseModalJson.textContent = JSON.stringify(caseData.full_case_data, null, 2);

    DOM.ragCaseModalOverlay.classList.remove('hidden');
    // Trigger reflow to ensure transition plays
    void DOM.ragCaseModalOverlay.offsetWidth;
    DOM.ragCaseModalOverlay.classList.remove('opacity-0');
    DOM.ragCaseModalContent.classList.remove('scale-95', 'opacity-0');
}

/**
 * Hides the RAG Case modal.
 */
export function closeRagCaseModal() {
    if (!DOM.ragCaseModalOverlay || !DOM.ragCaseModalContent) {
        console.error("RAG Case modal DOM elements not found.");
        return;
    }

    DOM.ragCaseModalOverlay.classList.add('opacity-0');
    DOM.ragCaseModalContent.classList.add('scale-95', 'opacity-0');
    setTimeout(() => DOM.ragCaseModalOverlay.classList.add('hidden'), 300);
}

/**
 * Provides brief visual feedback on the context status dot by making it blink.
 */
export function blinkContextDot() {
    if (!DOM.contextStatusDot) return;

    DOM.contextStatusDot.classList.add('blinking-white');

    setTimeout(() => {
        DOM.contextStatusDot.classList.remove('blinking-white');
    }, 1500); // 0.5s animation * 3 iterations
}

/**
 * Provides brief visual feedback on the RAG status dot by making it blink yellow.
 */
export function blinkRagDot() {
    if (!DOM.ragStatusDot) return;

    // Ensure it's in the 'connected' state before blinking
    if (!DOM.ragStatusDot.classList.contains('connected')) {
        DOM.ragStatusDot.classList.add('connected');
    }

    DOM.ragStatusDot.classList.add('blinking-yellow');

    // The animation runs for 1.5s (0.5s * 3 iterations)
    setTimeout(() => {
        DOM.ragStatusDot.classList.remove('blinking-yellow');
    }, 1500);
}

export function closeChatModal() {
    DOM.chatModalOverlay.classList.add('opacity-0');
    DOM.chatModalContent.classList.add('scale-95', 'opacity-0');
    setTimeout(() => DOM.chatModalOverlay.classList.add('hidden'), 300);
}

/**
 * Removes the visual highlight from a session item.
 * @param {string} sessionId The ID of the session to un-highlight.
 */
export function removeHighlight(sessionId) {
    const sessionItem = document.getElementById(`session-${sessionId}`);
    if (sessionItem) {
        const nameSpan = sessionItem.querySelector('.session-name-span');
        if (nameSpan) {
            nameSpan.classList.remove('font-bold', 'text-teradata-orange');
        }
        const indicator = sessionItem.querySelector('.new-activity-indicator');
        if (indicator) {
            indicator.remove();
        }
    }
}

/**
 * Toggles the collapsed state of the main side navigation bar.
 */
export function toggleSideNav() {
    DOM.appSideNav.classList.toggle('collapsed');
}

/**
 * Handles switching the main application view.
 * @param {string} viewId - The ID of the view to switch to (e.g., 'conversation-view').
 */
export function handleViewSwitch(viewId) {
    console.log(`[UI DEBUG] handleViewSwitch called with viewId: ${viewId}`);

    // 1. Log all app views found
    const appViews = document.querySelectorAll('.app-view');
    console.log('[UI DEBUG] Found app views:', appViews);

    // 2. Hide all views
    appViews.forEach(view => {
        console.log(`[UI DEBUG] Hiding view:`, view.id);
        view.classList.remove('active');
    });

    // 3. Show the selected view
    const viewToShow = document.getElementById(viewId);
    if (viewToShow) {
        console.log(`[UI DEBUG] Found view to show:`, viewToShow.id);
        console.log(`[UI DEBUG] Current classes for ${viewToShow.id}:`, viewToShow.className);
        viewToShow.classList.add('active');
        console.log(`[UI DEBUG] New classes for ${viewToShow.id}:`, viewToShow.className);
    } else {
        console.error(`[UI DEBUG] View with ID '${viewId}' not found!`);
    }

    // 4. Update the active state of the menu buttons
    if (DOM.viewSwitchButtons) {
        DOM.viewSwitchButtons.forEach(button => {
            const isActive = button.dataset.view === viewId;
            console.log(`[UI DEBUG] Updating button ${button.dataset.view}: active=${isActive}`);
            button.classList.toggle('active', isActive);
        });
    } else {
        console.warn('[UI DEBUG] DOM.viewSwitchButtons not found.');
    }

    // 5. Final check
    setTimeout(() => {
        const activeViews = document.querySelectorAll('.app-view.active');
        console.log('[UI DEBUG] Final check: Active views are:', activeViews);
        if (activeViews.length > 1) {
            console.warn('[UI DEBUG] Multiple views are active!', activeViews);
        } else if (activeViews.length === 0) {
            console.warn('[UI DEBUG] No view is active!');
        } else if (activeViews[0].id !== viewId) {
            console.error(`[UI DEBUG] WRONG VIEW IS ACTIVE! Expected ${viewId}, but found ${activeViews[0].id}`);
        }
    }, 100); // Use a small delay to catch any subsequent changes

    // 6. If switching to RAG Maintenance, load collections
    if (viewId === 'rag-maintenance-view') {
        loadRagCollections();
    }
}

/**
 * Fetches ChromaDB collections from the backend and renders them as cards.
 */
async function loadRagCollections() {
    if (!DOM.ragMaintenanceCollectionsContainer) return;
    try {
        if (DOM.ragMaintenanceEmptyHint) {
            DOM.ragMaintenanceEmptyHint.textContent = 'Loading collections...';
        }
        const res = await fetch('/rag/collections');
        const data = await res.json();
        const collections = (data && data.collections) ? data.collections : [];
        DOM.ragMaintenanceCollectionsContainer.innerHTML = '';
        if (!collections.length) {
            const emptyMsg = document.createElement('div');
            emptyMsg.className = 'col-span-full text-gray-400 text-sm';
            emptyMsg.textContent = 'No collections found.';
            DOM.ragMaintenanceCollectionsContainer.appendChild(emptyMsg);
            return;
        }
        collections.forEach(col => {
            const card = document.createElement('div');
            card.className = 'glass-panel rounded-xl p-4 flex flex-col gap-2 border border-white/10 hover:border-teradata-orange transition-colors';
            const title = document.createElement('h2');
            title.className = 'text-lg font-semibold text-white';
            title.textContent = col.name;
            const count = document.createElement('p');
            count.className = 'text-sm text-gray-300';
            count.textContent = `Documents: ${col.count ?? 'N/A'}`;
            const meta = document.createElement('p');
            meta.className = 'text-xs text-gray-500 break-all';
            meta.textContent = col.metadata && Object.keys(col.metadata).length ? `Metadata: ${JSON.stringify(col.metadata)}` : 'Metadata: none';
            const actions = document.createElement('div');
            actions.className = 'mt-2 flex gap-2';
            const refreshBtn = document.createElement('button');
            refreshBtn.type = 'button';
            refreshBtn.className = 'px-3 py-1 rounded-md bg-gray-700 hover:bg-gray-600 text-sm text-gray-200';
            refreshBtn.textContent = 'Refresh';
            refreshBtn.addEventListener('click', () => loadRagCollections());
            const inspectBtn = document.createElement('button');
            inspectBtn.type = 'button';
            inspectBtn.className = 'px-3 py-1 rounded-md bg-[#F15F22] hover:bg-[#D9501A] text-sm text-white';
            inspectBtn.textContent = 'Inspect';
            inspectBtn.addEventListener('click', () => {
                openCollectionInspection(col.name);
            });
            actions.appendChild(refreshBtn);
            actions.appendChild(inspectBtn);
            card.appendChild(title);
            card.appendChild(count);
            card.appendChild(meta);
            card.appendChild(actions);
            DOM.ragMaintenanceCollectionsContainer.appendChild(card);
        });
    } catch (e) {
        console.error('Failed to load RAG collections', e);
        DOM.ragMaintenanceCollectionsContainer.innerHTML = '';
        const errMsg = document.createElement('div');
        errMsg.className = 'col-span-full text-red-400 text-sm';
        errMsg.textContent = 'Error loading collections.';
        DOM.ragMaintenanceCollectionsContainer.appendChild(errMsg);
    }
}

// --- RAG Collection Inspection Logic ---
async function openCollectionInspection(collectionName) {
    if (!collectionName) return;
    state.currentInspectedCollection = collectionName;
    if (DOM.ragCollectionInspectTitle) {
        DOM.ragCollectionInspectTitle.textContent = `Inspect: ${collectionName}`;
    }
    handleViewSwitch('rag-collection-inspect-view');
    await fetchAndRenderCollectionRows({ collection: collectionName, refresh: true });
    wireCollectionInspectionEvents();
}

function wireCollectionInspectionEvents() {
    if (DOM.ragCollectionInspectBack) {
        DOM.ragCollectionInspectBack.onclick = () => {
            state.currentInspectedCollection = null;
            handleViewSwitch('rag-maintenance-view');
        };
    }
    if (DOM.ragCollectionRefreshButton) {
        DOM.ragCollectionRefreshButton.onclick = () => {
            if (state.currentInspectedCollection) {
                fetchAndRenderCollectionRows({ collection: state.currentInspectedCollection, refresh: true });
            }
        };
    }
    if (DOM.ragCollectionSearchInput && !DOM.ragCollectionSearchInput.dataset._wired) {
        let debounceTimer = null;
        DOM.ragCollectionSearchInput.addEventListener('input', () => {
            const term = DOM.ragCollectionSearchInput.value.trim();
            state.ragCollectionSearchTerm = term;
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                if (state.currentInspectedCollection) {
                    fetchAndRenderCollectionRows({ collection: state.currentInspectedCollection, query: term });
                }
            }, 300);
        });
        DOM.ragCollectionSearchInput.dataset._wired = 'true';
    }
}

async function fetchAndRenderCollectionRows({ collection, query = '', refresh = false }) {
    if (!collection) return;
    if (DOM.ragCollectionLoading) {
        DOM.ragCollectionLoading.textContent = query && query.length >= 3 ? 'Searching...' : 'Loading rows...';
        DOM.ragCollectionLoading.style.display = 'block';
    }
    try {
        const params = new URLSearchParams();
        params.set('limit', '25');
        params.set('light', 'true');
        if (query && query.length >= 3) {
            params.set('q', query);
        }
        const res = await fetch(`/rag/collections/${encodeURIComponent(collection)}/rows?${params.toString()}`);
        const data = await res.json();
        if (data.error) throw new Error(data.error);
        renderCollectionRows(data.rows || [], data.total, query, collection);
    } catch (e) {
        console.error('Failed to fetch collection rows', e);
        if (DOM.ragCollectionTableBody) {
            DOM.ragCollectionTableBody.innerHTML = `<tr><td colspan="6" class="px-2 py-2 text-red-400">Error loading rows.</td></tr>`;
        }
    } finally {
        if (DOM.ragCollectionLoading) {
            DOM.ragCollectionLoading.style.display = 'none';
        }
    }
}

function renderCollectionRows(rows, total, query, collectionName) {
    if (!DOM.ragCollectionTableBody) return;
    DOM.ragCollectionTableBody.innerHTML = '';
    if (!rows.length) {
        DOM.ragCollectionTableBody.innerHTML = `<tr><td colspan="6" class="px-2 py-2 text-gray-400">${query && query.length >= 3 ? 'No matches found.' : 'No rows in sample.'}</td></tr>`;
    } else {
        rows.forEach(r => {
            const tr = document.createElement('tr');
            tr.className = 'border-b border-gray-700 hover:bg-gray-800/40';
            const efficientBadge = r.is_most_efficient ? '<span class="px-2 py-0.5 rounded bg-green-600 text-white text-xs">Yes</span>' : '<span class="px-2 py-0.5 rounded bg-gray-600 text-white text-xs">No</span>';
            tr.innerHTML = `
                <td class="px-2 py-1 font-mono text-xs text-gray-300">${r.id}</td>
                <td class="px-2 py-1 text-gray-200">${escapeHtml(r.user_query || '')}</td>
                <td class="px-2 py-1 text-gray-300">${r.strategy_type || ''}</td>
                <td class="px-2 py-1">${efficientBadge}</td>
                <td class="px-2 py-1 text-gray-300">${r.output_tokens ?? ''}</td>
                <td class="px-2 py-1 text-gray-400">${r.timestamp || ''}</td>
            `;
            tr.addEventListener('click', () => selectCaseRow(r.id));
            DOM.ragCollectionTableBody.appendChild(tr);
        });
    }
    if (DOM.ragCollectionFooter) {
        const mode = query && query.length >= 3 ? 'search results' : 'sample';
        DOM.ragCollectionFooter.textContent = `Showing ${rows.length} ${mode} (collection has ${total} total entries).`;
    }
}

function escapeHtml(str) {
    return str.replace(/[&<>"]+/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

async function selectCaseRow(caseId) {
    if (!caseId) return;
    if (DOM.ragSelectedCaseDetails) {
        DOM.ragSelectedCaseDetails.classList.remove('hidden');
        DOM.ragSelectedCaseMetadata.textContent = 'Loading case details...';
        DOM.ragSelectedCasePlan.innerHTML = '';
        DOM.ragSelectedCaseTrace.innerHTML = '';
        if (DOM.ragSelectedCaseSeparator) {
            DOM.ragSelectedCaseSeparator.classList.remove('hidden');
        }
    }
    try {
        const res = await fetch(`/rag/cases/${encodeURIComponent(caseId)}`);
        const data = await res.json();
        if (data.error) throw new Error(data.error);
        const caseData = data.case || {};
        const turnSummary = data.session_turn_summary || null;
        if (DOM.ragSelectedCaseMetadata) {
            const meta = caseData.metadata || {};
            // Compute total execution time from trace timestamps (first to last)
            let totalExecutionTime = 'N/A';
            if (turnSummary && Array.isArray(turnSummary.execution_trace) && turnSummary.execution_trace.length > 0) {
                const parseTs = (entry) => {
                    try {
                        const ts = entry?.action?.metadata?.timestamp || entry?.result?.metadata?.timestamp;
                        return ts ? Date.parse(ts) : null;
                    } catch { return null; }
                };
                // Find first and last valid timestamps
                const firstEntry = turnSummary.execution_trace.find(e => parseTs(e) !== null);
                const lastEntry = [...turnSummary.execution_trace].reverse().find(e => parseTs(e) !== null);
                const firstTs = parseTs(firstEntry);
                const lastTs = parseTs(lastEntry);
                if (firstTs !== null && lastTs !== null && lastTs >= firstTs) {
                    totalExecutionTime = ((lastTs - firstTs) / 1000).toFixed(2) + 's';
                }
            }
            DOM.ragSelectedCaseMetadata.innerHTML = `
                <div class='grid grid-cols-2 md:grid-cols-4 gap-2'>
                    <div><span class='text-gray-500'>Case ID:</span> <code>${escapeHtml(caseData.case_id || caseId)}</code></div>
                    <div><span class='text-gray-500'>Task ID:</span> <code>${escapeHtml(meta.task_id || '')}</code></div>
                    <div><span class='text-gray-500'>Session:</span> <code>${escapeHtml(meta.session_id || '')}</code></div>
                    <div><span class='text-gray-500'>Turn:</span> <code>${escapeHtml(String(meta.turn_id ?? ''))}</code></div>
                    <div><span class='text-gray-500'>Provider:</span> ${escapeHtml(meta.llm_config?.provider || '')}</div>
                    <div><span class='text-gray-500'>Model:</span> ${escapeHtml(meta.llm_config?.model || '')}</div>
                    <div><span class='text-gray-500'>Output Tokens:</span> ${escapeHtml(String(meta.llm_config?.output_tokens ?? ''))}</div>
                    <div><span class='text-gray-500'>Efficient:</span> ${meta.is_most_efficient ? '<span class="text-green-400">Yes</span>' : '<span class="text-gray-400">No</span>'}</div>
                </div>
                <div class='mt-2 text-xs text-gray-400'>Total Execution Time: <span class='font-mono text-gray-200'>${totalExecutionTime}</span></div>`;
        }
        if (DOM.ragSelectedCasePlan) {
            const phases = caseData.successful_strategy?.phases || [];
            if (phases.length) {
                const phaseHtml = phases.map(p => `
                    <div class='p-2 rounded-md bg-gray-800/40 border border-white/10'>
                        <div class='text-xs font-semibold text-teradata-orange mb-1'>Phase ${p.phase}</div>
                        <div class='text-sm text-gray-200 mb-1'>Goal: ${escapeHtml(p.goal || '')}</div>
                        <div class='text-xs text-gray-400'>Tools: ${(p.relevant_tools || []).map(t => `<code>${escapeHtml(t)}</code>`).join(', ')}</div>
                    </div>`).join('');
                DOM.ragSelectedCasePlan.innerHTML = `<h3 class='text-white font-semibold mb-2'>Successful Strategy</h3><div class='grid md:grid-cols-2 gap-2'>${phaseHtml}</div>`;
            } else {
                DOM.ragSelectedCasePlan.innerHTML = '<div class="text-gray-400 text-sm">No successful strategy phases.</div>';
            }
        }
        if (DOM.ragSelectedCaseTrace) {
            if (turnSummary && Array.isArray(turnSummary.execution_trace)) {
                // Store raw trace and render via helper for toggling & collapsing
                state.currentCaseTrace = turnSummary.execution_trace.slice();
                renderCaseTrace();
            } else {
                DOM.ragSelectedCaseTrace.innerHTML = '<div class="text-gray-400 text-sm">No execution trace available.</div>';
            }
        }
    } catch (e) {
        console.error('Failed to load case details', e);
        if (DOM.ragSelectedCaseMetadata) {
            DOM.ragSelectedCaseMetadata.textContent = 'Error loading case details.';
        }
    }
}

function renderCaseTrace() {
    if (!DOM.ragSelectedCaseTrace) return;
    const rawTrace = Array.isArray(state.currentCaseTrace) ? state.currentCaseTrace : [];
    let workingTrace = rawTrace;
    if (!state.showSystemLogsInCaseTrace) {
        workingTrace = workingTrace.filter(entry => !(entry.action && entry.action.tool_name === 'TDA_SystemLog'));
    }
    // Collapse duplicates if enabled
    let collapsed = [];
    if (state.collapseDuplicateTraceEntries) {
        for (let i = 0; i < workingTrace.length; i++) {
            const entry = workingTrace[i];
            const prev = collapsed.length ? collapsed[collapsed.length - 1] : null;
            const toolName = entry.action && entry.action.tool_name;
            const message = entry.action && entry.action.arguments && entry.action.arguments.message;
            const status = entry.result && entry.result.status;
            if (prev && prev.__toolName === toolName && prev.__message === message && prev.__status === status) {
                prev.__count += 1;
                prev.entries.push(entry);
            } else {
                const wrapper = { ...entry, __toolName: toolName, __message: message, __status: status, __count: 1, entries: [entry] };
                collapsed.push(wrapper);
            }
        }
    } else {
        collapsed = workingTrace.map(e => ({ ...e, __toolName: e.action && e.action.tool_name, __message: e.action && e.action.arguments && e.action.arguments.message, __status: e.result && e.result.status, __count: 1, entries: [e] }));
    }

    // Timing calculations
    const parseTs = ts => {
        try { return ts ? Date.parse(ts) : null; } catch { return null; }
    };
    const firstTs = collapsed.length ? parseTs(collapsed[0].action && collapsed[0].action.metadata && collapsed[0].action.metadata.timestamp) : null;

    const html = collapsed.map(block => {
        const action = block.action || {}; const result = block.result || {};
        const tool = block.__toolName || 'unknown';
        const status = block.__status || 'info';
        const msg = block.__message || '';
        const tsRaw = action.metadata && action.metadata.timestamp;
        const currentTs = parseTs(tsRaw);
        let elapsed = '-';
        let delta = '-';
        if (currentTs && firstTs) {
            elapsed = ((currentTs - firstTs) / 1000).toFixed(2) + 's';
        }
        // Find previous distinct block timestamp for delta
        const idx = collapsed.indexOf(block);
        if (idx > 0) {
            const prevTsRaw = collapsed[idx - 1].action && collapsed[idx - 1].action.metadata && collapsed[idx - 1].action.metadata.timestamp;
            const prevTs = parseTs(prevTsRaw);
            if (currentTs && prevTs) {
                delta = ((currentTs - prevTs) / 1000).toFixed(2) + 's';
            }
        }
        const repeatBadge = block.__count > 1 ? `<span class='ml-2 px-1 py-0.5 rounded bg-blue-600/60 text-[10px]'>x${block.__count}</span>` : '';
        const timingBadge = `<span class='text-[10px] text-gray-500'>t=${elapsed} Δ=${delta}</span>`;
        return `<div class='text-xs p-2 rounded bg-gray-900/40 border border-gray-700/40'>
            <div class='flex justify-between items-center'><span class='font-mono text-gray-300'>${escapeHtml(tool)}</span><span class='text-[10px] ${status === 'error' ? 'text-red-400' : 'text-green-400'}'>${escapeHtml(status)}</span></div>
            <div class='text-gray-400 mt-1'>${escapeHtml(msg)}</div>
            <div class='flex justify-between mt-1'>${timingBadge}${repeatBadge}</div>
        </div>`;
    }).join('');

    DOM.ragSelectedCaseTrace.innerHTML = `<h3 class='text-white font-semibold mb-2 flex items-center gap-4'>Execution Trace
        <label class='flex items-center gap-1 text-[11px] font-normal'><input type='checkbox' id='toggle-system-logs' ${state.showSystemLogsInCaseTrace ? 'checked' : ''}>System Logs</label>
        <label class='flex items-center gap-1 text-[11px] font-normal'><input type='checkbox' id='toggle-collapse-dupes' ${state.collapseDuplicateTraceEntries ? 'checked' : ''}>Collapse Duplicates</label>
    </h3>
    <div class='space-y-1 max-h-64 overflow-y-auto pr-1'>${html}</div>`;

    const sysToggle = document.getElementById('toggle-system-logs');
    const dupesToggle = document.getElementById('toggle-collapse-dupes');
    if (sysToggle) {
        sysToggle.onchange = () => { state.showSystemLogsInCaseTrace = sysToggle.checked; renderCaseTrace(); };
    }
    if (dupesToggle) {
        dupesToggle.onchange = () => { state.collapseDuplicateTraceEntries = dupesToggle.checked; renderCaseTrace(); };
    }
}