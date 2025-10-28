/**
 * ui.js
 * * This module handles all direct DOM manipulations and UI updates.
 * Functions here are responsible for rendering messages, modals, status updates, and other visual changes.
 */

import * as DOM from './domElements.js';
import { state } from './state.js';
import { renderChart, isPrivilegedUser, isPromptCustomForModel, getNormalizedModelId } from './utils.js';
import { handleSessionRenameSave, handleSessionRenameCancel } from './eventHandlers.js';

// NOTE: This module no longer imports from eventHandlers.js, breaking a circular dependency.
// Instead, eventHandlers.js will import these UI functions.

// --- MODIFICATION START: Add addMessage function with turnId parameter ---
/**
 * Adds a message bubble to the chat log.
 * @param {string} role - 'user' or 'assistant'.
 * @param {string} content - HTML content of the message.
 * @param {number} [turnId] - Optional turn ID (provided for assistant messages).
 */
export function addMessage(role, content, turnId = null) {
// --- MODIFICATION END ---
    const wrapper = document.createElement('div');
    wrapper.className = `message-bubble flex items-start gap-4 ${role === 'user' ? 'justify-end' : ''}`;

    const iconContainer = document.createElement('div');
    iconContainer.className = 'flex-shrink-0 relative'; // Make container relative for button positioning

    const icon = document.createElement('div');
    icon.className = 'w-10 h-10 rounded-full flex items-center justify-center text-white font-bold shadow-lg';
    icon.textContent = role === 'user' ? 'U' : 'A';
    icon.classList.add(role === 'user' ? 'bg-gray-700' : 'bg-[#F15F22]');
    iconContainer.appendChild(icon);

    // --- MODIFICATION START: Add placeholder for user actions ---
    if (role === 'user') {
        const actionsPlaceholder = document.createElement('div');
        // Add a class or ID to find this later
        actionsPlaceholder.className = 'user-message-actions-placeholder absolute -left-12 top-1/2 -translate-y-1/2 flex items-center gap-1';
        // Ensure it's empty initially
        iconContainer.appendChild(actionsPlaceholder);
    }
    // --- MODIFICATION END ---

    const messageContainer = document.createElement('div');
    messageContainer.className = 'p-4 rounded-xl shadow-lg max-w-2xl glass-panel';
    messageContainer.classList.add(role === 'user' ? 'bg-gray-800/50' : 'bg-[#333333]/50');

    const author = document.createElement('p');
    author.className = 'font-bold mb-2 text-sm';
    author.textContent = role === 'user' ? 'You' : 'Assistant';
    author.classList.add(role === 'user' ? 'text-gray-300' : 'text-[#F15F22]');
    messageContainer.appendChild(author);

    const messageContent = document.createElement('div');
    messageContent.innerHTML = content;
    messageContainer.appendChild(messageContent);

    // --- MODIFICATION START: Adjust wrapper structure based on role ---
    // User messages have iconContainer on the right, Assistant on the left
    wrapper.appendChild(role === 'user' ? messageContainer : iconContainer);
    wrapper.appendChild(role === 'user' ? iconContainer : messageContainer);
    // --- MODIFICATION END ---

    DOM.chatLog.appendChild(wrapper);

    // --- MODIFICATION START: Add action buttons if assistant message with turnId ---
    if (role === 'assistant' && turnId) {
        // Find the *last* user message bubble added before this assistant message
        const userMessages = DOM.chatLog.querySelectorAll('.message-bubble .bg-gray-700'); // Find user icons
        const lastUserMessageBubble = userMessages.length > 0 ? userMessages[userMessages.length - 1].closest('.message-bubble') : null;

        if (lastUserMessageBubble) {
            const placeholder = lastUserMessageBubble.querySelector('.user-message-actions-placeholder');
            if (placeholder) {
                // Create buttons
                const reloadButton = document.createElement('button');
                reloadButton.className = 'reload-plan-button p-1.5 rounded-md text-gray-400 hover:text-white hover:bg-white/10 transition-colors opacity-0 group-hover:opacity-100'; // Initially hidden, show on hover
                reloadButton.title = 'Reload Plan in Status Window';
                reloadButton.dataset.turnId = turnId;
                reloadButton.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>`; // Reload icon

                const replayButton = document.createElement('button');
                replayButton.className = 'replay-query-button p-1.5 rounded-md text-gray-400 hover:text-white hover:bg-white/10 transition-colors opacity-0 group-hover:opacity-100'; // Initially hidden, show on hover
                replayButton.title = 'Replay Query';
                replayButton.dataset.turnId = turnId;
                replayButton.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm.707-10.293a1 1 0 00-1.414-1.414l-3 3a1 1 0 000 1.414l3 3a1 1 0 001.414-1.414L9.414 11H13a1 1 0 100-2H9.414l1.293-1.293z" clip-rule="evenodd" /></svg>`; // Replay/back icon

                // Clear placeholder and add buttons
                placeholder.innerHTML = ''; // Clear any potential content
                placeholder.appendChild(reloadButton);
                placeholder.appendChild(replayButton);

                // Add group-hover class to the parent bubble to trigger button visibility
                lastUserMessageBubble.classList.add('group');
            } else {
                console.warn("Could not find placeholder for user actions in the previous user message.");
            }
        } else {
             console.warn("Could not find the previous user message bubble to add actions to.");
        }
    }
    // --- MODIFICATION END ---

    const chartContainers = messageContent.querySelectorAll('.chart-render-target');
    chartContainers.forEach(container => {
        if (container.dataset.spec) {
            renderChart(container.id, container.dataset.spec);
        }
    });

    wrapper.scrollIntoView({ behavior: 'smooth', block: 'start' });
}


// --- Remaining UI functions (setExecutionState, _renderPlanningDetails, etc.) ---
// ... (No changes needed in the rest of the functions for this request) ...
/**
 * Sets the UI state for active execution (disables input, shows stop button, etc.).
 * @param {boolean} isActive - True if execution is starting, false if ending.
 */
export function setExecutionState(isActive) {
    DOM.userInput.disabled = isActive;
    DOM.submitButton.disabled = isActive;
    DOM.newChatButton.disabled = isActive; // Disable new chat during execution
    DOM.sendIcon.classList.toggle('hidden', isActive);
    DOM.loadingSpinner.classList.toggle('hidden', !isActive);

    if (DOM.stopExecutionButton) {
        DOM.stopExecutionButton.classList.toggle('hidden', !isActive);
        // Ensure the stop button is enabled when shown, disabled when hidden
        DOM.stopExecutionButton.disabled = !isActive;
    }

    if (!isActive) {
        // --- Cleanup on Stop ---
        // Ensure pulsing and busy states are removed as a final cleanup,
        // regardless of whether the final status update event arrived.
        setThinkingIndicator(false); // Make sure LLM thinking stops visually
        DOM.mcpStatusDot.classList.remove('pulsing', 'busy');
        DOM.llmStatusDot.classList.remove('pulsing', 'busy');

        // Reset to default connected/idle state if they aren't disconnected
        if (!DOM.mcpStatusDot.classList.contains('disconnected')) {
            DOM.mcpStatusDot.classList.add('connected');
        }
        if (!DOM.llmStatusDot.classList.contains('disconnected')) {
            DOM.llmStatusDot.classList.add('idle'); // LLM defaults to idle when connected
        }
    }
    // Note: Adding the pulsing class is now handled solely within the
    // 'status_indicator_update' event handler in eventHandlers.js based on the 'busy' state.
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
                    <summary class="cursor-pointer text-gray-400 hover:text-white">Generated Plan (${details.length} phases)</summary>
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
                    <div class="font-bold text-gray-300 mb-2">Phase ${phase.phase}</div>
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
    if (!details.tool_name && !details.prompt_name) return null;

    const name = details.tool_name || details.prompt_name;
    const type = details.tool_name ? 'Tool' : 'Prompt';

    let argsHtml = '';
    if (details.arguments) {
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
    }

    return `
        <div class="status-kv-item"><div class="status-kv-key">${type}</div><div class="status-kv-value"><code class="status-code">${name}</code></div></div>
        ${argsHtml}
    `;
}

export function updateStatusWindow(eventData, isFinal = false) {
    const { step, details, type } = eventData;
    if (!step && type !== 'phase_start' && type !== 'phase_end') {
        return;
    }

    if (type === 'phase_start') {
        const { phase_num, total_phases, goal, execution_depth } = details;

        // Find the very last step, even if nested
        const lastStep = Array.from(DOM.statusWindowContent.querySelectorAll('.status-step')).pop();
        if (lastStep && lastStep.classList.contains('active')) {
            lastStep.classList.remove('active');
            // Apply fast-path-aware logic: only add 'completed' if it's not a 'plan-optimization' step
            if (!lastStep.classList.contains('plan-optimization')) {
                 lastStep.classList.add('completed');
            }
        }

        const phaseContainer = document.createElement('details');
        phaseContainer.className = 'status-phase-container';
        phaseContainer.open = true; // Start phases open

        const phaseHeader = document.createElement('summary');
        phaseHeader.className = 'status-phase-header phase-start';

        let depthIndicator = '';
        if (execution_depth && execution_depth > 0) {
            depthIndicator = '↳ '.repeat(execution_depth);
        }

        phaseHeader.innerHTML = `
            <span class="font-bold flex-shrink-0">${depthIndicator}Starting Plan Phase ${phase_num}/${total_phases}</span>
            <span class="text-gray-400 text-xs truncate ml-2">${goal}</span>
        `;

        phaseContainer.appendChild(phaseHeader);

        const phaseContent = document.createElement('div');
        phaseContent.className = 'status-phase-content';
        phaseContainer.appendChild(phaseContent);

        DOM.statusWindowContent.appendChild(phaseContainer);
        state.currentPhaseContainerEl = phaseContainer;

        if (!state.isMouseOverStatus) {
            DOM.statusWindowContent.scrollTop = DOM.statusWindowContent.scrollHeight;
        }
        return;
    }

    if (type === 'phase_end') {
        if (state.currentPhaseContainerEl) {
            const { phase_num, total_phases, status } = details;
            const phaseFooter = document.createElement('div');
            phaseFooter.className = 'status-phase-header phase-end';
            phaseFooter.innerHTML = `<span class="font-bold">Plan Phase ${phase_num}/${total_phases} Completed</span>`;

            if (status === 'skipped') {
                phaseFooter.classList.add('skipped');
                phaseFooter.innerHTML = `<span class="font-bold">Plan Phase ${phase_num}/${total_phases} Skipped</span>`;
            } else {
                state.currentPhaseContainerEl.classList.add('completed');
            }

            state.currentPhaseContainerEl.appendChild(phaseFooter);
            state.currentPhaseContainerEl = null; // Reset for next phase
        }
        state.isInFastPath = false; // Reset fast path flag at end of phase
        if (!state.isMouseOverStatus) {
            DOM.statusWindowContent.scrollTop = DOM.statusWindowContent.scrollHeight;
        }
        return;
    }

    // Handle standard step events
    const parentContainer = state.currentPhaseContainerEl ? state.currentPhaseContainerEl.querySelector('.status-phase-content') : DOM.statusWindowContent;

    // Mark previous step as completed if it was active
    const lastStep = document.getElementById(`status-step-${state.currentStatusId}`);
    if (lastStep && lastStep.classList.contains('active') && parentContainer.contains(lastStep)) {
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
    stepEl.className = 'status-step p-3 rounded-md';

    const stepTitle = document.createElement('h4');
    stepTitle.className = 'font-bold text-sm text-white mb-2';
    stepTitle.textContent = step;
    stepEl.appendChild(stepTitle);

    const metricsEl = document.createElement('div');
    metricsEl.className = 'per-call-metrics text-xs text-gray-400 mb-2 hidden';

    if (typeof details === 'object' && details !== null && details.call_id) {
        metricsEl.dataset.callId = details.call_id;
    }

    stepEl.appendChild(metricsEl);

    if (details) {
        let customRenderedHtml = null;
        let detailsString = '';

        if (typeof details === 'object' && details !== null) {
            // --- MODIFICATION START: Use _renderMetaPlanDetails also for reload ---
            if (step.startsWith("Calling LLM for") || step === "Plan Loaded") {
            // --- MODIFICATION END ---
                customRenderedHtml = _renderPlanningDetails(details);
            } else if (step === "Strategic Meta-Plan Generated") {
                customRenderedHtml = _renderMetaPlanDetails(details);
            } else if (step === "Tool Execution Intent") {
                customRenderedHtml = _renderToolIntentDetails(details);
            } else {
                try {
                    detailsString = JSON.stringify(details, null, 2);
                } catch (e) {
                    detailsString = "[Could not stringify details]";
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
                if ((step.includes('Tool Execution Result') || step.includes('Tool Execution Error')) && typeof details === 'object' && details.results) {
                    const itemCount = Array.isArray(details.results) ? details.results.length : (details.results ? 1 : 0);
                    const status = details.status || 'unknown';
                    summaryText = `Tool Result (${status}, ${itemCount} items)`;
                } else if (step.includes('Final Answer')) {
                    summaryText = `Final Answer Summary`;
                } else if (type === 'cancelled') {
                    summaryText = 'Cancellation Details';
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

    if (!state.isMouseOverStatus) {
        DOM.statusWindowContent.scrollTop = DOM.statusWindowContent.scrollHeight;
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

export function updateStatusPromptName() {
    const promptNameDiv = document.getElementById('prompt-name-display');
    if (state.currentProvider && state.currentModel) {
        const isCustom = isPromptCustomForModel(state.currentProvider, state.currentModel);
        const promptType = isPrivilegedUser() ? (isCustom ? 'Custom' : 'Default') : 'Default (Server-Side)';
        promptNameDiv.innerHTML = `
            <span class="font-semibold text-gray-300">${promptType} Prompt</span>
            <span class="text-gray-500">/</span>
            <span class="font-mono text-teradata-orange text-xs">${getNormalizedModelId(state.currentModel)}</span>
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
    if (state.resourceData[type]) { // Check if data exists
        for (const category in state.resourceData[type]) {
            if (state.resourceData[type][category].some(r => r.name === resourceName)) {
                resourceCategory = category;
                break;
            }
        }
    }


    if (resourceCategory) {
        const resourceTab = document.querySelector(`.resource-tab[data-type="${type}"]`);
        if (resourceTab) resourceTab.click(); // Select the main type tab (Tools/Prompts)

        const categoryTab = document.querySelector(`.category-tab[data-type="${type}"][data-category="${resourceCategory}"]`);
        if(categoryTab) categoryTab.click(); // Select the specific category tab

        const resourceElement = document.getElementById(`resource-${type}-${resourceName}`);
        if (resourceElement) {
            resourceElement.open = true; // Ensure the details are open
            resourceElement.classList.add('resource-selected');
            state.currentlySelectedResource = resourceElement;

            // Scroll into view after a short delay to allow tab switching/opening animation
            setTimeout(() => {
                resourceElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 350);
        }
    } else {
        console.warn(`Could not find category for resource '${resourceName}' of type '${type}'. Highlight failed.`);
    }
}

export function addSessionToList(sessionId, name, isActive = false) {
    const sessionItem = document.createElement('button');
    sessionItem.id = `session-${sessionId}`;
    sessionItem.dataset.sessionId = sessionId;
    sessionItem.className = 'session-item w-full text-left p-3 rounded-lg hover:bg-white/10 transition-colors truncate';
    if (isActive) {
        document.querySelectorAll('.session-item').forEach(item => item.classList.remove('active'));
        sessionItem.classList.add('active');
    }

    const nameSpan = document.createElement('span');
    nameSpan.className = 'session-name-span font-semibold text-sm text-white flex-grow truncate';
    nameSpan.textContent = name;
    sessionItem.appendChild(nameSpan);

    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'session-actions';

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

    sessionItem.appendChild(actionsDiv);

    return sessionItem;
}

export function updateSessionListItemName(sessionId, newName) {
    const sessionItem = document.getElementById(`session-${sessionId}`);
    if (sessionItem) {
        const nameSpan = sessionItem.querySelector('.session-name-span');
        if (nameSpan) {
            nameSpan.textContent = newName;
            console.log(`UI Updated: Session item ${sessionId} name changed to '${newName}'`);
        } else {
            console.warn(`Could not find name span within session item ${sessionId}`);
        }
    } else {
        console.warn(`Could not find session item ${sessionId} in the list to update name.`);
    }
}

export function removeSessionFromList(sessionId) {
    const sessionItem = document.getElementById(`session-${sessionId}`);
    if (sessionItem) {
        sessionItem.remove();
        console.log(`UI Updated: Removed session item ${sessionId} from list.`);
    } else {
        console.warn(`Could not find session item ${sessionId} in the list to remove.`);
    }
}

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
    inputElement.className = 'session-edit-input';

    spanElement.style.display = 'none';
    actionsDiv.style.display = 'none';
    sessionItem.insertBefore(inputElement, spanElement);

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

export function exitSessionEditMode(inputElement, finalName) {
    const sessionItem = inputElement.closest('.session-item');
    if (!sessionItem) return;

    const spanElement = sessionItem.querySelector('.session-name-span');
    const actionsDiv = sessionItem.querySelector('.session-actions');

    if (spanElement) {
        spanElement.textContent = finalName;
        spanElement.style.display = '';
    }
    if (actionsDiv) {
        actionsDiv.style.display = '';
    }

    inputElement.removeEventListener('blur', handleSessionRenameSave);
    inputElement.remove();
}


export function updateConfigButtonState() {
    const isConnected = DOM.mcpStatusDot.classList.contains('connected');

    if (!isConnected) {
        DOM.configActionButtonText.textContent = 'Connect & Load';
        DOM.configActionButton.type = 'submit';
        DOM.configActionButton.classList.remove('bg-gray-600', 'hover:bg-gray-500');
        DOM.configActionButton.classList.add('bg-[#F15F22]', 'hover:bg-[#D9501A]');
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
    } else {
        DOM.configActionButtonText.textContent = 'Close';
        DOM.configActionButton.type = 'button';
        DOM.configActionButton.classList.remove('bg-[#F15F22]', 'hover:bg-[#D9501A]');
        DOM.configActionButton.classList.add('bg-gray-600', 'hover:bg-gray-500');
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
        hintTextSpan.innerHTML = `<strong>Last Turn Context:</strong> <span class="text-orange-400 font-semibold">Locked</span>`;
        hintTooltipSpan.innerHTML = `'Last Turn' context is locked on. Press <kbd>Shift</kbd> + <kbd>Alt</kbd> to switch back to the default 'Full Session Context'.`;
        DOM.contextStatusDot.className = 'connection-dot context-last-turn-locked';
        DOM.sendIcon.classList.remove('flipped');
    } else if (state.isTempLastTurnMode) {
        hintTextSpan.innerHTML = `<strong>Context:</strong> <span class="text-yellow-400 font-semibold">Last Turn</span>`;
        hintTooltipSpan.innerHTML = `Temporarily using 'Last Turn' context for this query.`;
        DOM.contextStatusDot.className = 'connection-dot context-last-turn-temp';
        DOM.sendIcon.classList.remove('flipped');
    } else {
        hintTextSpan.innerHTML = `<strong>Full Session Context:</strong> <span class="text-green-400 font-semibold">On</span>`;
        hintTooltipSpan.innerHTML = `Full session context is the default. Hold <kbd>Alt</kbd> to temporarily use 'Last Turn' context. Press <kbd>Shift</kbd> + <kbd>Alt</kbd> to lock 'Last Turn' context on.`;
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
        DOM.voiceInputButton.classList.remove('bg-[#F15F22]');
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

export function closeConfigModal() {
    DOM.configModalOverlay.classList.add('opacity-0');
    DOM.configModalContent.classList.add('scale-95', 'opacity-0');
    setTimeout(() => DOM.configModalOverlay.classList.add('hidden'), 300);
}

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

export function closeChatModal() {
    DOM.chatModalOverlay.classList.add('opacity-0');
    DOM.chatModalContent.classList.add('scale-95', 'opacity-0');
    setTimeout(() => DOM.chatModalOverlay.classList.add('hidden'), 300);
}
