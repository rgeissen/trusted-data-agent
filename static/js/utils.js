/**
 * utils.js
 * * This module contains utility and helper functions used across the application.
 * These functions perform common tasks like clipboard operations, chart rendering, and user privilege checks.
 */

import { state } from './state.js';
import { promptEditorStatus } from './domElements.js';

export function isPrivilegedUser() {
    const privilegedTiers = ['Prompt Engineer', 'Enterprise'];
    const userTier = state.appConfig.license_info?.tier;
    return privilegedTiers.includes(userTier);
}

export function getSystemPrompts() {
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
    if (!modelId) return '';
    if (modelId.startsWith('arn:aws:bedrock:')) {
        const parts = modelId.split('/');
        const modelPart = parts[parts.length - 1];
        return modelPart.replace(/^(eu|us|apac)\./, '');
    }
    return modelId;
}

export function getPromptStorageKey(provider, model) {
    const normalizedModel = getNormalizedModelId(model);
    return `${provider}-${normalizedModel}`;
}

export function saveSystemPromptForModel(provider, model, promptText, isCustom) {
    if (!isPrivilegedUser()) return;

    const prompts = getSystemPrompts();
    const key = getPromptStorageKey(provider, model);
    prompts[key] = { prompt: promptText, isCustom: isCustom };
    localStorage.setItem('userSystemPrompts', JSON.stringify(prompts));
}

export function getSystemPromptForModel(provider, model) {
    if (!isPrivilegedUser()) return null;

    const prompts = getSystemPrompts();
    const key = getPromptStorageKey(provider, model);
    return prompts[key]?.prompt || null;
}

export function isPromptCustomForModel(provider, model) {
    if (!isPrivilegedUser()) return false;

    const prompts = getSystemPrompts();
    const key = getPromptStorageKey(provider, model);
    return prompts[key]?.isCustom || false;
}

export async function getDefaultSystemPrompt(provider, model) {
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

export function copyToClipboard(button) {
    const codeBlock = button.closest('.sql-code-block').querySelector('code');
    const textToCopy = codeBlock.innerText;

    navigator.clipboard.writeText(textToCopy).then(() => {
        const originalContent = button.innerHTML;
        button.textContent = 'Copied!';
        button.classList.add('copied');
        setTimeout(() => {
            button.innerHTML = originalContent;
            button.classList.remove('copied');
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy text: ', err);
    });
}

export function copyTableToClipboard(button) {
    const dataStr = button.dataset.table;
    if (!dataStr) {
        console.error("No data-table attribute found on the button.");
        return;
    }

    try {
        const data = JSON.parse(dataStr);
        if (!Array.isArray(data) || data.length === 0) {
            return;
        }

        const headers = Object.keys(data[0]);
        let tsvContent = headers.join('\t') + '\n';

        data.forEach(row => {
            const values = headers.map(header => {
                let value = row[header] === null || row[header] === undefined ? '' : String(row[header]);
                value = value.replace(/\t/g, ' ').replace(/\n/g, ' ');
                return value;
            });
            tsvContent += values.join('\t') + '\n';
        });

        navigator.clipboard.writeText(tsvContent).then(() => {
            const originalContent = button.innerHTML;
            button.textContent = 'Copied!';
            button.classList.add('copied');
            setTimeout(() => {
                button.innerHTML = originalContent;
                button.classList.remove('copied');
            }, 2000);
        }).catch(err => {
            console.error('Failed to copy table data: ', err);
        });

    } catch (e) {
        console.error("Failed to parse or process table data for copying:", e);
    }
}

export function renderChart(containerId, spec) {
    try {
        const chartSpec = typeof spec === 'string' ? JSON.parse(spec) : spec;
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

// --- MODIFICATION START: Add deterministic confirmation classifier ---
/**
 * Classifies a user's spoken confirmation as 'yes', 'no', or 'unknown'.
 * @param {string} text - The transcribed text from the user.
 * @returns {'yes' | 'no' | 'unknown'}
 */
export function classifyConfirmation(text) {
    // Use regex with word boundaries (\b) for more accurate matching.
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
// --- MODIFICATION END ---
