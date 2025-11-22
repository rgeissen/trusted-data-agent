/**
 * main.js
 * * This is the entry point for the application.
 * It initializes the application by setting up event listeners and loading initial data.
 */

import { initializeEventListeners } from './eventHandlers.js';
import { finalizeConfiguration } from './handlers/configManagement.js';
import { initializeConfigurationUI } from './handlers/configurationHandler.js';
import * as API from './api.js';
import * as DOM from './domElements.js';
import { state } from './state.js';
import { setupPanelToggle } from './utils.js';
import * as UI from './ui.js';
import { handleViewSwitch } from './ui.js';
import { initializeVoiceRecognition } from './voice.js';
import { subscribeToNotifications } from './notifications.js';

async function initializeRAGAutoCompletion() {
    const suggestionsContainer = document.getElementById('rag-suggestions-container');
    const userInput = document.getElementById('user-input');
    let debounceTimer = null;
    let currentSuggestions = [];
    let selectedIndex = -1;

    function highlightSuggestion(index) {
        const items = suggestionsContainer.querySelectorAll('.rag-suggestion-item');
        items.forEach((item, idx) => {
            if (idx === index) {
                item.classList.add('rag-suggestion-highlighted');
            } else {
                item.classList.remove('rag-suggestion-highlighted');
            }
        });
    }

    function selectSuggestion(index) {
        if (index >= 0 && index < currentSuggestions.length) {
            userInput.value = currentSuggestions[index];
            suggestionsContainer.innerHTML = '';
            suggestionsContainer.classList.add('hidden');
            currentSuggestions = [];
            selectedIndex = -1;
        }
    }

    function showSuggestions(questionsToShow) {
        currentSuggestions = questionsToShow;
        selectedIndex = questionsToShow.length > 0 ? 0 : -1;

        if (questionsToShow.length === 0) {
            suggestionsContainer.innerHTML = '';
            suggestionsContainer.classList.add('hidden');
            return;
        }

        suggestionsContainer.innerHTML = '';
        questionsToShow.forEach((q, index) => {
            const suggestionItem = document.createElement('div');
            suggestionItem.className = 'rag-suggestion-item';
            if (index === 0) {
                suggestionItem.classList.add('rag-suggestion-highlighted');
            }
            suggestionItem.textContent = q;
            suggestionItem.addEventListener('mousedown', (e) => {
                e.preventDefault();
                selectSuggestion(index);
                userInput.focus();
            });
            suggestionItem.addEventListener('mouseenter', () => {
                selectedIndex = index;
                highlightSuggestion(index);
            });
            suggestionsContainer.appendChild(suggestionItem);
        });
        suggestionsContainer.classList.remove('hidden');
    }

    async function fetchAndShowSuggestions(queryText) {
        if (!queryText || queryText.length < 2) {
            showSuggestions([]);
            return;
        }

        // Get active profile ID from configState
        const profileId = window.configState?.defaultProfileId || null;
        
        // Fetch semantically ranked questions from backend
        const questions = await API.fetchRAGQuestions(queryText, profileId, 5);
        showSuggestions(questions);
    }

    if (suggestionsContainer && userInput) {
        userInput.addEventListener('focus', () => {
            const inputValue = userInput.value.trim();
            if (inputValue.length >= 2) {
                fetchAndShowSuggestions(inputValue);
            }
        });

        userInput.addEventListener('input', () => {
            const inputValue = userInput.value.trim();
            
            // Clear previous timer
            if (debounceTimer) {
                clearTimeout(debounceTimer);
            }
            
            if (inputValue.length >= 2) {
                // Debounce API calls (300ms delay)
                debounceTimer = setTimeout(() => {
                    fetchAndShowSuggestions(inputValue);
                }, 300);
            } else {
                showSuggestions([]);
            }
        });

        userInput.addEventListener('keydown', (e) => {
            if (currentSuggestions.length === 0) return;

            if (e.key === 'ArrowDown') {
                e.preventDefault();
                selectedIndex = (selectedIndex + 1) % currentSuggestions.length;
                highlightSuggestion(selectedIndex);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                selectedIndex = (selectedIndex - 1 + currentSuggestions.length) % currentSuggestions.length;
                highlightSuggestion(selectedIndex);
            } else if (e.key === 'Tab' && selectedIndex >= 0) {
                e.preventDefault();
                selectSuggestion(selectedIndex);
            } else if (e.key === 'Escape') {
                suggestionsContainer.innerHTML = '';
                suggestionsContainer.classList.add('hidden');
                currentSuggestions = [];
                selectedIndex = -1;
            }
        });

        userInput.addEventListener('blur', () => {
            setTimeout(() => {
                suggestionsContainer.innerHTML = '';
                suggestionsContainer.classList.add('hidden');
                currentSuggestions = [];
                selectedIndex = -1;
            }, 150);
        });
    }
}

/**
 * Ensures a user UUID exists in localStorage and application state.
 * Generates a new UUID if one is not found.
 */
function ensureUserUUID() {
    let userUUID = null;
    try {
        userUUID = localStorage.getItem('tdaUserUUID');
        if (userUUID) {
        } else {
            userUUID = crypto.randomUUID();
            localStorage.setItem('tdaUserUUID', userUUID);
            // Verify it was set
            const storedUUID = localStorage.getItem('tdaUserUUID');
            if (storedUUID === userUUID) {
            } else {
                console.error("ensureUserUUID: Failed to store UUID in localStorage!");
                // Optionally alert the user or fallback to temporary UUID
                alert("Warning: Could not save user identifier. Session history may not persist correctly.");
            }
        }
    } catch (e) {
        console.error("ensureUserUUID: Error accessing localStorage:", e);
        // Fallback: Generate a temporary UUID if localStorage fails
        userUUID = userUUID || crypto.randomUUID(); // Use existing if generated before error
        alert("Warning: Cannot access local storage. Session history will not persist across browser sessions.");
    }
    // Set the state regardless
    state.userUUID = userUUID;

    if (!state.userUUID) {
         console.error("FATAL: User UUID is null after ensureUserUUID!");
         alert("Fatal error: Could not establish user identifier.");
    }
}

/**
 * Fetches the current star count for the GitHub repository and updates the UI.
 */
async function fetchGitHubStarCount() {
    const starCountElement = document.getElementById('github-star-count');
    const starIconElement = document.getElementById('github-star-icon');
    
    
    if (!starCountElement) {
        console.error('fetchGitHubStarCount: star count element not found');
        return;
    }

    try {
        const response = await fetch('https://api.github.com/repos/rgeissen/trusted-data-agent', {
            method: 'GET',
            headers: {
                'Accept': 'application/vnd.github.v3+json'
            },
            mode: 'cors'
        });
        
        
        if (response.ok) {
            const data = await response.json();
            const starCount = data.stargazers_count || 0;
            // Format the number with comma separators
            starCountElement.textContent = starCount.toLocaleString('en-US');
            
            // Update star icon based on count (filled if > 0, outline if 0)
            if (starIconElement) {
                if (starCount > 0) {
                    starIconElement.setAttribute('fill', 'currentColor');
                } else {
                    starIconElement.setAttribute('fill', 'none');
                    starIconElement.setAttribute('stroke', 'currentColor');
                    starIconElement.setAttribute('stroke-width', '1.5');
                }
            }
            
        } else {
            const errorText = await response.text();
            starCountElement.textContent = '-';
        }
    } catch (error) {
        console.error('Error fetching GitHub star count:', error);
        console.error('Error details:', error.message, error.stack);
        starCountElement.textContent = '-';
    }
}

// REMOVED: loadInitialConfig() function - obsolete with new configuration system
// The new configuration system (configState) automatically loads from localStorage
// and doesn't need manual form population

// Define welcome screen functions BEFORE DOMContentLoaded to ensure they're available
function hideWelcomeScreen() {
    const welcomeScreen = document.getElementById('welcome-screen');
    const chatLog = document.getElementById('chat-log');
    const chatFooter = document.getElementById('chat-footer');
    
    if (welcomeScreen && chatLog) {
        welcomeScreen.classList.add('hidden');
        chatLog.classList.remove('hidden');
        if (chatFooter) {
            chatFooter.classList.remove('hidden');
        }
    }
}

// Make function available globally
window.hideWelcomeScreen = hideWelcomeScreen;

document.addEventListener('DOMContentLoaded', async () => {
    const savedShowWelcomeScreen = localStorage.getItem('showWelcomeScreenAtStartup');
    state.showWelcomeScreenAtStartup = savedShowWelcomeScreen === null ? true : savedShowWelcomeScreen === 'true';
    const welcomeScreenCheckbox = document.getElementById('toggle-welcome-screen-checkbox');
    const welcomeScreenPopupCheckbox = document.getElementById('welcome-screen-show-at-startup-checkbox');
    if (welcomeScreenCheckbox) {
        welcomeScreenCheckbox.checked = state.showWelcomeScreenAtStartup;
    }
    if (welcomeScreenPopupCheckbox) {
        welcomeScreenPopupCheckbox.checked = state.showWelcomeScreenAtStartup;
    }

    ensureUserUUID(); // Get/Set the User UUID right away
    subscribeToNotifications();
    initializeRAGAutoCompletion();

    // Fetch GitHub star count - DEACTIVATED to conserve API credits
    // fetchGitHubStarCount();

    const uuidInput = document.getElementById('tda-user-uuid');
    const copyButton = document.getElementById('copy-uuid-button');

    if (uuidInput) {
        uuidInput.value = state.userUUID;
    }

    if (copyButton) {
        copyButton.addEventListener('click', () => {
            uuidInput.select();
            document.execCommand('copy');
            const originalTitle = copyButton.title;
            copyButton.title = 'Copied!';
            setTimeout(() => {
                copyButton.title = originalTitle;
            }, 2000);
        });
    }

    // REMOVED: loadInitialConfig() - obsolete with new configuration system
    // The new configuration system uses configState which loads from localStorage automatically

    // Initialize all event listeners first to ensure they are ready.
    initializeEventListeners();
    initializeVoiceRecognition();
    
    // Initialize Execution Dashboard
    if (window.ExecutionDashboard) {
        window.executionDashboard = new window.ExecutionDashboard();
    } else {
    }

    // Initialize new configuration UI (async - loads MCP servers from backend)
    await initializeConfigurationUI();

    const promptEditorMenuItem = DOM.promptEditorButton.parentElement;
    promptEditorMenuItem.style.display = 'none';

    try {
        const res = await fetch('/app-config');
        state.appConfig = await res.json();

        await API.checkAndUpdateDefaultPrompts();

        const chartingIntensityContainer = document.getElementById('charting-intensity-container');
        if (!state.appConfig.charting_enabled) {
            chartingIntensityContainer.style.display = 'none';
        } else {
            DOM.chartingIntensitySelect.value = state.appConfig.default_charting_intensity || 'medium';
        }

        if (state.appConfig.voice_conversation_enabled) {
            DOM.voiceInputButton.classList.remove('hidden');
            DOM.keyObservationsToggleButton.classList.remove('hidden');
        }

        if (DOM.ragStatusDot) {
            if (!state.appConfig.rag_enabled) {
                DOM.ragStatusDot.parentElement.style.display = 'none';
            } else {
                DOM.ragStatusDot.parentElement.style.display = 'flex';
            }
        }

    } catch (e) {
        console.error("Could not fetch app config", e);
    }

    // Initialize panels as collapsed and disabled until configuration is loaded
    DOM.sessionHistoryPanel.classList.add('collapsed');
    DOM.statusWindow.classList.add('collapsed');
    DOM.toolHeader.classList.add('collapsed');
    DOM.toggleHistoryButton.classList.add('btn-disabled');
    DOM.toggleHistoryButton.style.opacity = '0.5';
    DOM.toggleHistoryButton.style.cursor = 'not-allowed';
    DOM.toggleHistoryButton.style.pointerEvents = 'none';
    DOM.toggleStatusButton.classList.add('btn-disabled');
    DOM.toggleStatusButton.style.opacity = '0.5';
    DOM.toggleStatusButton.style.cursor = 'not-allowed';
    DOM.toggleStatusButton.style.pointerEvents = 'none';
    DOM.toggleHeaderButton.classList.add('btn-disabled');
    DOM.toggleHeaderButton.style.opacity = '0.5';
    DOM.toggleHeaderButton.style.cursor = 'not-allowed';
    DOM.toggleHeaderButton.style.pointerEvents = 'none';

    try {
        const status = await API.checkServerStatus();
        
        // Set configuration persistence flag from server
        if (typeof status.configurationPersistence !== 'undefined') {
            state.configurationPersistence = status.configurationPersistence;
            
            // Show warning banner if persistence is disabled
            const persistenceBanner = document.getElementById('persistence-warning-banner');
            if (!state.configurationPersistence && persistenceBanner) {
                persistenceBanner.classList.remove('hidden');
            }
            
            // If persistence is disabled, clear any stored credentials
            if (!state.configurationPersistence) {
                const { clearAllCredentials } = await import('./storageUtils.js');
                clearAllCredentials();
            }
        }
        
        // Update RAG indicator based on status
        if (DOM.ragStatusDot && state.appConfig.rag_enabled) {
            if (status.rag_active) {
                DOM.ragStatusDot.classList.remove('disconnected');
                DOM.ragStatusDot.classList.add('connected');
            } else {
                DOM.ragStatusDot.classList.remove('connected');
                DOM.ragStatusDot.classList.add('disconnected');
            }
        }

        if (status.isConfigured) {

            // NOTE: With new config UI, we don't need to pre-fill old form fields
            // The configurationHandler manages its own state via localStorage
            
            // Old code removed:
            // DOM.llmProviderSelect.value = status.provider;
            // DOM.mcpServerNameInput.value = status.mcp_server.name;
            // await loadCredentialsAndModels();

            const currentConfig = { provider: status.provider, model: status.model };
            // Pass the mcp_server details from status to ensure they are used if re-finalizing
            currentConfig.mcp_server = status.mcp_server;
            await finalizeConfiguration(currentConfig, true);


            // handleViewSwitch is now called inside finalizeConfiguration


        } else {
            // The new configuration UI handles its own state
            // No need to pre-fill old form fields
            const savedTtsCreds = localStorage.getItem('ttsCredentialsJson');
            if (savedTtsCreds && DOM.ttsCredentialsJsonTextarea) {
                DOM.ttsCredentialsJsonTextarea.value = savedTtsCreds;
            }
            
            // Show welcome screen in conversation view
            await showWelcomeScreen();
        }
    } catch (startupError) {
        console.error("DEBUG: Error during startup configuration/session loading. Showing config modal.", startupError);
        // Fallback to showing credentials view
        try {
             const savedTtsCreds = localStorage.getItem('ttsCredentialsJson');
             if (savedTtsCreds && DOM.ttsCredentialsJsonTextarea) { 
                 DOM.ttsCredentialsJsonTextarea.value = savedTtsCreds; 
             }
             // NOTE: Old loadCredentialsAndModels() removed - new config UI handles this
        } catch (prefillError) {
            console.error("DEBUG: Error during fallback pre-fill:", prefillError);
        }
        
        handleViewSwitch('credentials-view');
    }

    // Setup panel toggle handlers (called after configuration check so panels can be enabled if configured)
    DOM.toggleHistoryCheckbox.checked = !DOM.sessionHistoryPanel.classList.contains('collapsed');
    setupPanelToggle(DOM.toggleHistoryButton, DOM.sessionHistoryPanel, DOM.toggleHistoryCheckbox, DOM.historyCollapseIcon, DOM.historyExpandIcon);

    DOM.toggleHeaderCheckbox.checked = !DOM.toolHeader.classList.contains('collapsed');
    setupPanelToggle(DOM.toggleHeaderButton, DOM.toolHeader, DOM.toggleHeaderCheckbox, DOM.headerCollapseIcon, DOM.headerExpandIcon);

    DOM.toggleStatusCheckbox.checked = !DOM.statusWindow.classList.contains('collapsed');
    setupPanelToggle(DOM.toggleStatusButton, DOM.statusWindow, DOM.toggleStatusCheckbox, DOM.statusCollapseIcon, DOM.statusExpandIcon);

    const savedKeyObservationsMode = localStorage.getItem('keyObservationsMode');
    if (['autoplay-off', 'autoplay-on', 'off'].includes(savedKeyObservationsMode)) {
        state.keyObservationsMode = savedKeyObservationsMode;
    }

    UI.updateHintAndIndicatorState();
    UI.updateVoiceModeUI();
    UI.updateKeyObservationsModeUI();

    // Save user preferences before page unloads
    window.addEventListener('beforeunload', () => {
        localStorage.setItem('showWelcomeScreenAtStartup', state.showWelcomeScreenAtStartup);
    });
});

// ============================================================================
// WELCOME SCREEN MANAGEMENT
// ============================================================================

/**
 * Show the welcome screen for unconfigured applications
 */
async function showWelcomeScreen() {
    const welcomeScreen = document.getElementById('welcome-screen');
    const chatLog = document.getElementById('chat-log');
    const chatFooter = document.getElementById('chat-footer');
    const welcomeBtn = document.getElementById('welcome-configure-btn');
    const welcomeBtnText = document.getElementById('welcome-button-text');
    const welcomeCogwheel = document.getElementById('welcome-cogwheel-icon');
    const welcomeSubtext = document.querySelector('.welcome-subtext');
    const reconfigureLink = document.getElementById('welcome-reconfigure-link');
    const welcomeCheckbox = document.getElementById('welcome-screen-show-at-startup-checkbox');
    
    // Populate disabled capabilities section
    populateWelcomeDisabledCapabilities();
    
    // Sync checkbox state with user preference
    if (welcomeCheckbox) {
        welcomeCheckbox.checked = state.showWelcomeScreenAtStartup;
    }
    
    if (welcomeScreen && chatLog) {
        welcomeScreen.classList.remove('hidden');
        chatLog.classList.add('hidden');
        // Hide chat input footer when showing welcome screen
        if (chatFooter) {
            chatFooter.classList.add('hidden');
        }
    }
    
    // Check if user has previously saved MCP servers and LLM providers
    let hasSavedConfig = false;
    let configDetails = '';
    try {
        const response = await fetch('/api/v1/mcp/servers');
        if (response.ok) {
            const data = await response.json();
            // API returns {status, servers: [...], active_server_id}
            const hasMCPServer = data && data.servers && data.servers.length > 0;
            
            if (hasMCPServer && data.active_server_id) {
                // Find the active server
                const activeServer = data.servers.find(s => s.id === data.active_server_id);
                if (activeServer) {
                    const mcpName = activeServer.name || 'Unknown Server';
                    
                    // Get the active LLM configuration from ConfigurationState
                    const activeLLM = configState.getActiveLLMConfiguration();
                    
                    if (activeLLM) {
                        const llmProvider = activeLLM.provider || 'Unknown Provider';
                        const llmModel = activeLLM.model || 'Unknown Model';
                        configDetails = `${mcpName} • ${llmProvider} / ${llmModel}`;
                        // Only set hasSavedConfig to true if BOTH MCP and LLM are configured
                        hasSavedConfig = true;
                    } else {
                        configDetails = `${mcpName} • LLM not configured`;
                        // MCP configured but LLM missing - don't enable Connect & Load
                        hasSavedConfig = false;
                    }
                }
            }
        }
    } catch (error) {
        console.error("Error checking for saved configurations:", error);
    }
    
    // Update button text based on whether user has saved configurations
    if (welcomeBtnText) {
        const buttonText = hasSavedConfig ? 'Connect and Load' : 'Configure Application';
        welcomeBtnText.textContent = buttonText;
    }
    
    // Update subtext with configuration details or default message
    if (welcomeSubtext) {
        welcomeSubtext.textContent = hasSavedConfig && configDetails 
            ? configDetails 
            : "You'll need an MCP server and an LLM provider";
    }
    
    // Show/hide reconfigure link based on saved config
    if (reconfigureLink) {
        if (hasSavedConfig) {
            reconfigureLink.classList.remove('hidden');
        } else {
            reconfigureLink.classList.add('hidden');
        }
        
        // Wire up the reconfigure link
        if (!reconfigureLink.dataset._wired) {
            reconfigureLink.addEventListener('click', (e) => {
                e.preventDefault();
                handleViewSwitch('credentials-view');
            });
            reconfigureLink.dataset._wired = 'true';
        }
    }
    
    // Wire up the configure button
    if (welcomeBtn && !welcomeBtn.dataset._wired) {
        welcomeBtn.addEventListener('click', async () => {
            if (hasSavedConfig) {
                // User has saved config - connect and load automatically
                
                // Show spinning cogwheel and update button text
                if (welcomeCogwheel) {
                    welcomeCogwheel.classList.add('animate-spin');
                }
                if (welcomeBtnText) {
                    welcomeBtnText.textContent = 'Connecting...';
                }
                welcomeBtn.disabled = true;
                
                try {
                    // Import reconnectAndLoad function which handles the full connection process
                    const { reconnectAndLoad } = await import('./handlers/configurationHandler.js');
                    
                    // Call reconnectAndLoad which will:
                    // 1. Validate MCP and LLM configurations
                    // 2. Send /configure request to backend
                    // 3. Load resources (tools, prompts, resources)
                    // 4. Load or create session
                    // 5. Switch to conversation view
                    await reconnectAndLoad();
                    
                } catch (error) {
                    console.error('Error during auto-configuration:', error);
                    // reconnectAndLoad handles its own error notifications
                } finally {
                    // Stop spinning and restore button
                    if (welcomeCogwheel) {
                        welcomeCogwheel.classList.remove('animate-spin');
                    }
                    if (welcomeBtnText) {
                        welcomeBtnText.textContent = hasSavedConfig ? 'Connect and Load' : 'Configure Application';
                    }
                    welcomeBtn.disabled = false;
                }
            } else {
                // No saved config - go to credentials view
                handleViewSwitch('credentials-view');
            }
        });
        welcomeBtn.dataset._wired = 'true';
    }
}

/**
 * Populate the disabled capabilities section on the welcome screen
 */
function populateWelcomeDisabledCapabilities() {
    const container = document.getElementById('welcome-disabled-capabilities');
    if (!container) return;

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
        container.classList.add('hidden');
        return;
    }

    container.classList.remove('hidden');
    
    let html = `
        <div class="pt-6 border-t border-white/10 max-w-3xl mx-auto text-left">
            <h4 class="text-lg font-bold text-yellow-300 mb-2">Reactive Capabilities</h4>
            <p class="text-sm text-gray-400 mb-4">The following capabilities are not actively participating in queries. You can enable them in the Capabilities panel.</p>
            <div class="grid md:grid-cols-2 gap-6">
    `;

    if (disabledTools.length > 0) {
        html += '<div><h5 class="font-semibold text-sm text-white mb-2">Tools</h5><ul class="space-y-1">';
        disabledTools.forEach(name => {
            html += `<li class="text-xs text-gray-300"><code class="text-teradata-orange">${name}</code></li>`;
        });
        html += '</ul></div>';
    }

    if (disabledPrompts.length > 0) {
        html += '<div><h5 class="font-semibold text-sm text-white mb-2">Prompts</h5><ul class="space-y-1">';
        disabledPrompts.forEach(name => {
            html += `<li class="text-xs text-gray-300"><code class="text-teradata-orange">${name}</code></li>`;
        });
        html += '</ul></div>';
    }

    html += '</div></div>';
    container.innerHTML = html;
}

// Make showWelcomeScreen available globally
window.showWelcomeScreen = showWelcomeScreen;