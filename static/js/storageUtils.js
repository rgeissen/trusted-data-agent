/**
 * storageUtils.js
 * Wrapper for localStorage that respects server configuration persistence settings
 * When server has TDA_CONFIGURATION_PERSISTENCE=false, localStorage operations are skipped
 */

import { state } from './state.js';

/**
 * Safe localStorage.setItem that respects configuration persistence
 * @param {string} key - The localStorage key
 * @param {string} value - The value to store
 */
export function safeSetItem(key, value) {
    if (!state.configurationPersistence) {
        return;
    }
    try {
        localStorage.setItem(key, value);
    } catch (error) {
        console.error(`[Storage] Error setting localStorage key '${key}':`, error);
    }
}

/**
 * Safe localStorage.getItem that respects configuration persistence
 * @param {string} key - The localStorage key
 * @returns {string|null} - The stored value or null
 */
export function safeGetItem(key) {
    if (!state.configurationPersistence) {
        return null;
    }
    try {
        return localStorage.getItem(key);
    } catch (error) {
        console.error(`[Storage] Error getting localStorage key '${key}':`, error);
        return null;
    }
}

/**
 * Safe localStorage.removeItem that respects configuration persistence
 * @param {string} key - The localStorage key
 */
export function safeRemoveItem(key) {
    if (!state.configurationPersistence) {
        return;
    }
    try {
        localStorage.removeItem(key);
    } catch (error) {
        console.error(`[Storage] Error removing localStorage key '${key}':`, error);
    }
}

/**
 * Clear all stored credentials from localStorage
 * This is useful when transitioning to non-persistent mode or for security
 */
export function clearAllCredentials() {
    const credentialKeys = [
        'mcpConfig',
        'amazonApiKey',
        'ollamaHost',
        'azureApiKey',
        'friendliApiKey',
        'googleApiKey',
        'openaiApiKey',
        'anthropicApiKey',
        'ttsCredentialsJson',
        'lastSelectedProvider'
    ];
    
    credentialKeys.forEach(key => {
        try {
            localStorage.removeItem(key);
        } catch (error) {
            console.error(`[Storage] Error clearing credential '${key}':`, error);
        }
    });
}
