/**
 * utils.js
 * * This module contains utility and helper functions used across the application.
 * These functions perform common tasks like clipboard operations, chart rendering, and user privilege checks.
 */

import { state } from './state.js';
import { promptEditorStatus } from './domElements.js';

export function isPrivilegedUser() {
    // ... (no changes in this function) ...
    const privilegedTiers = ['Prompt Engineer', 'Enterprise'];
    const userTier = state.appConfig.license_info?.tier;
    return privilegedTiers.includes(userTier);
}

export function getSystemPrompts() {
    // ... (no changes in this function) ...
    if (!isPrivilegedUser()) return {};

    try {
        const prompts = localStorage.getItem('userSystemPrompts');
        return prompts ? JSON.parse(prompts) : {};
    } catch (e) {
        console.error("Could not parse system prompts from localStorage", e);
        return {};
    }
}

export function getNormalizedModelId(modelId) {
    // ... (no changes in this function) ...
    if (!modelId) return '';
    if (modelId.startsWith('arn:aws:bedrock:')) {
        const parts = modelId.split('/');
        const modelPart = parts[parts.length - 1];
        return modelPart.replace(/^(eu|us|apac)\./, '');
    }
    return modelId;
}

export function getPromptStorageKey(provider, model) {
    // ... (no changes in this function) ...
    const normalizedModel = getNormalizedModelId(model);
    return `${provider}-${normalizedModel}`;
}

export function saveSystemPromptForModel(provider, model, promptText, isCustom) {
    // ... (no changes in this function) ...
    if (!isPrivilegedUser()) return;

    const prompts = getSystemPrompts();
    const key = getPromptStorageKey(provider, model);
    prompts[key] = { prompt: promptText, isCustom: isCustom };
    localStorage.setItem('userSystemPrompts', JSON.stringify(prompts));
}

export function getSystemPromptForModel(provider, model) {
    // ... (no changes in this function) ...
    if (!isPrivilegedUser()) return null;

    const prompts = getSystemPrompts();
    const key = getPromptStorageKey(provider, model);
    return prompts[key]?.prompt || null;
}

export function isPromptCustomForModel(provider, model) {
    // ... (no changes in this function) ...
    if (!isPrivilegedUser()) return false;

    const prompts = getSystemPrompts();
    const key = getPromptStorageKey(provider, model);
    return prompts[key]?.isCustom || false;
}

export async function getDefaultSystemPrompt(provider, model) {
    // ... (no changes in this function) ...
    if (!isPrivilegedUser()) return null;

    const key = getPromptStorageKey(provider, model);
    if (state.defaultPromptsCache[key]) {
        return state.defaultPromptsCache[key];
    }

    try {
        const res = await fetch(`/system_prompt/${provider}/${getNormalizedModelId(model)}`);
        if (!res.ok) {
            throw new Error(`Failed to fetch default prompt: ${res.statusText}`);
        }
        const data = await res.json();
        if (data.system_prompt) {
            state.defaultPromptsCache[key] = data.system_prompt;
            return data.system_prompt;
        }
        throw new Error("Server response did not contain a system_prompt.");
    } catch (e) {
        console.error(`Error getting default system prompt for ${key}:`, e);
        promptEditorStatus.textContent = 'Error fetching default prompt.';
        promptEditorStatus.className = 'text-sm text-red-400';
        return null;
    }
}

/**
 * Copies text content from a code block associated with the clicked button
 * to the clipboard using the document.execCommand method for better
 * compatibility in restricted environments.
 * @param {HTMLButtonElement} button - The button element that was clicked.
 */
export function copyToClipboard(button) {
    // ... (no changes in this function) ...
    const codeBlock = button.closest('.sql-code-block')?.querySelector('code');
    if (!codeBlock) {
        console.error('Could not find code block to copy from.');
        return;
    }
    const textToCopy = codeBlock.innerText;

    const textarea = document.createElement('textarea');
    textarea.value = textToCopy;
    textarea.style.position = 'fixed'; // Prevent scrolling to bottom of page in MS Edge.
    textarea.style.left = '-9999px';
    document.body.appendChild(textarea);
    textarea.select();
    textarea.setSelectionRange(0, 99999); // For mobile devices

    let success = false;
    try {
        success = document.execCommand('copy');
        if (!success) {
            throw new Error('document.execCommand returned false');
        }
    } catch (err) {
        console.error('Fallback copy failed: ', err);
        // Optionally provide user feedback about the failure
        alert('Failed to copy text. Please try copying manually.');
    }

    document.body.removeChild(textarea);

    if (success) {
        const originalContent = button.innerHTML;
        // Keep the SVG icon, just change the text
        const textNode = button.childNodes[button.childNodes.length - 1];
        if (textNode && textNode.nodeType === Node.TEXT_NODE) {
            textNode.textContent = ' Copied!';
        } else {
             button.textContent = 'Copied!'; // Fallback if structure changes
        }
        button.classList.add('copied');
        setTimeout(() => {
            button.innerHTML = originalContent; // Restore original HTML (including SVG)
            button.classList.remove('copied');
        }, 2000);
    }
}

/**
 * Copies table data (formatted as TSV) associated with the clicked button
 * to the clipboard using the document.execCommand method.
 * @param {HTMLButtonElement} button - The button element that was clicked.
 */
export function copyTableToClipboard(button) {
    // ... (no changes in this function) ...
    const dataStr = button.dataset.table;
    if (!dataStr) {
        console.error("No data-table attribute found on the button.");
        return;
    }

    let tsvContent = '';
    try {
        const data = JSON.parse(dataStr);
        if (!Array.isArray(data) || data.length === 0 || typeof data[0] !== 'object') {
            console.warn("Table data is empty or not in the expected format (array of objects).");
            return;
        }

        const headers = Object.keys(data[0]);
        tsvContent = headers.join('\t') + '\n'; // Header row

        data.forEach(row => {
            const values = headers.map(header => {
                let value = row[header] === null || row[header] === undefined ? '' : String(row[header]);
                // Sanitize value for TSV: remove tabs and newlines within cells
                value = value.replace(/[\t\n\r]/g, ' ');
                return value;
            });
            tsvContent += values.join('\t') + '\n'; // Data row
        });

    } catch (e) {
        console.error("Failed to parse or process table data for copying:", e);
        alert('Failed to process table data for copying.');
        return;
    }

    const textarea = document.createElement('textarea');
    textarea.value = tsvContent;
    textarea.style.position = 'fixed';
    textarea.style.left = '-9999px';
    document.body.appendChild(textarea);
    textarea.select();
    textarea.setSelectionRange(0, 99999);

    let success = false;
    try {
        success = document.execCommand('copy');
         if (!success) {
            throw new Error('document.execCommand returned false');
        }
    } catch (err) {
        console.error('Fallback table copy failed: ', err);
        alert('Failed to copy table. Please try copying manually.');
    }

    document.body.removeChild(textarea);

    if (success) {
        const originalContent = button.innerHTML;
        const textNode = button.childNodes[button.childNodes.length - 1];
         if (textNode && textNode.nodeType === Node.TEXT_NODE) {
            textNode.textContent = ' Copied!';
        } else {
             button.textContent = 'Copied!';
        }
        button.classList.add('copied');
        setTimeout(() => {
            button.innerHTML = originalContent;
            button.classList.remove('copied');
        }, 2000);
    }
}


export function renderChart(containerId, spec) {
    // ... (no changes in this function) ...
    try {
        const chartSpec = typeof spec === 'string' ? JSON.parse(spec) : spec;
        if (!chartSpec || !chartSpec.type || !chartSpec.options) {
             throw new Error("Invalid chart specification provided.");
        }
        if (typeof G2Plot === 'undefined' || !G2Plot[chartSpec.type]) {
             throw new Error(`Chart type "${chartSpec.type}" is not supported or G2Plot is not loaded.`);
        }
        const plot = new G2Plot[chartSpec.type](containerId, chartSpec.options);
        plot.render();
    } catch (e) {
        console.error("Failed to render chart:", e);
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = `<div class="p-4 text-red-400">Error rendering chart: ${e.message}</div>`;
        }
    }
}


export function setupPanelToggle(button, panel, checkbox, collapseIcon, expandIcon) {
    // ... (no changes in this function) ...
    const toggle = (isOpen) => {
        const isCollapsed = !isOpen;
        panel.classList.toggle('collapsed', isCollapsed);
        if (collapseIcon) collapseIcon.classList.toggle('hidden', isCollapsed);
        if (expandIcon) expandIcon.classList.toggle('hidden', !isCollapsed);
        if (checkbox) checkbox.checked = isOpen;
    };

    button.addEventListener('click', () => toggle(panel.classList.contains('collapsed')));
    if (checkbox) {
        checkbox.addEventListener('change', () => toggle(checkbox.checked));
    }
}

/**
 * Classifies a user's spoken confirmation as 'yes', 'no', or 'unknown'.
 * @param {string} text - The transcribed text from the user.
 * @returns {'yes' | 'no' | 'unknown'}
 */
export function classifyConfirmation(text) {
    // ... (no changes in this function) ...
    const affirmativeRegex = /\b(yes|yeah|yep|sure|ok|okay|please|do it|go ahead)\b/i;
    const negativeRegex = /\b(no|nope|don't|stop|cancel)\b/i;

    const lowerText = text.toLowerCase().trim();

    if (affirmativeRegex.test(lowerText)) {
        return 'yes';
    }
    if (negativeRegex.test(lowerText)) {
        return 'no';
    }
    return 'unknown';
}

// --- MODIFICATION START: Remove global assignments ---
// window.copyToClipboard = copyToClipboard; // REMOVED
// window.copyTableToClipboard = copyTableToClipboard; // REMOVED
// --- MODIFICATION END ---

