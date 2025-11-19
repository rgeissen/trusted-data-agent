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

/**
 * Ensures a user UUID exists in localStorage and application state.
 * Generates a new UUID if one is not found.
 */
function ensureUserUUID() {
    console.log("ensureUserUUID: Checking for existing UUID...");
    let userUUID = null;
    try {
        userUUID = localStorage.getItem('tdaUserUUID');
        if (userUUID) {
            console.log("ensureUserUUID: Found existing User UUID:", userUUID);
        } else {
            userUUID = crypto.randomUUID();
            console.log("ensureUserUUID: Generated New User UUID:", userUUID);
            localStorage.setItem('tdaUserUUID', userUUID);
            // Verify it was set
            const storedUUID = localStorage.getItem('tdaUserUUID');
            if (storedUUID === userUUID) {
                console.log("ensureUserUUID: Successfully stored new UUID.");
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
        console.warn("ensureUserUUID: Using temporary User UUID for this session:", userUUID);
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
    
    console.log('fetchGitHubStarCount: Starting...', { starCountElement, starIconElement });
    
    if (!starCountElement) {
        console.error('fetchGitHubStarCount: star count element not found');
        return;
    }

    try {
        console.log('fetchGitHubStarCount: Fetching from GitHub API...');
        const response = await fetch('https://api.github.com/repos/rgeissen/trusted-data-agent', {
            method: 'GET',
            headers: {
                'Accept': 'application/vnd.github.v3+json'
            },
            mode: 'cors'
        });
        
        console.log('fetchGitHubStarCount: Response status:', response.status);
        
        if (response.ok) {
            const data = await response.json();
            console.log('fetchGitHubStarCount: API response data:', data);
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
            
            console.log('GitHub star count fetched successfully:', starCount);
        } else {
            console.warn('Failed to fetch GitHub star count. Status:', response.status, 'Status Text:', response.statusText);
            const errorText = await response.text();
            console.warn('Error response:', errorText);
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
    
    console.log('hideWelcomeScreen called', { welcomeScreen, chatLog });
    if (welcomeScreen && chatLog) {
        welcomeScreen.classList.add('hidden');
        chatLog.classList.remove('hidden');
        console.log('Welcome screen hidden, chat log shown');
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
    console.log("DOMContentLoaded: User UUID ensured:", state.userUUID);
    subscribeToNotifications();

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
        console.log('Execution Dashboard initialized');
    } else {
        console.warn('ExecutionDashboard class not found');
    }

    // Initialize new configuration UI (async - loads MCP servers from backend)
    await initializeConfigurationUI();

    const promptEditorMenuItem = DOM.promptEditorButton.parentElement;
    promptEditorMenuItem.style.display = 'none';

    try {
        const res = await fetch('/app-config');
        state.appConfig = await res.json();
        console.log('License Info:', state.appConfig.license_info);

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

    try {
        console.log("DEBUG: Checking server status on startup...");
        const status = await API.checkServerStatus();
        
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
            console.log("DEBUG: Server is already configured. Proceeding with setup.", status);

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

            console.log("DEBUG: Configuration finalized. Session loading is handled by finalizeConfiguration.");

            // handleViewSwitch is now called inside finalizeConfiguration


        } else {
            console.log("DEBUG: Server is not configured. Showing welcome screen.");
            // The new configuration UI handles its own state
            // No need to pre-fill old form fields
            const savedTtsCreds = localStorage.getItem('ttsCredentialsJson');
            if (savedTtsCreds && DOM.ttsCredentialsJsonTextarea) {
                DOM.ttsCredentialsJsonTextarea.value = savedTtsCreds;
            }
            
            // Show welcome screen in conversation view
            await showWelcomeScreen();
            
            // NOTE: Old loadCredentialsAndModels() is not needed with new config UI
            // The new configurationHandler manages everything via localStorage
            
            // Don't automatically switch to credentials view - let user stay on conversation view with welcome screen
            // handleViewSwitch('credentials-view');
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
    const welcomeBtn = document.getElementById('welcome-configure-btn');
    const welcomeBtnText = document.getElementById('welcome-button-text');
    const welcomeCogwheel = document.getElementById('welcome-cogwheel-icon');
    const welcomeSubtext = document.querySelector('.welcome-subtext');
    const reconfigureLink = document.getElementById('welcome-reconfigure-link');
    
    if (welcomeScreen && chatLog) {
        welcomeScreen.classList.remove('hidden');
        chatLog.classList.add('hidden');
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
                    
                    // Get the active LLM provider from ConfigurationState
                    const activeLLM = await configState.getActiveLLMProvider();
                    
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
                console.log('Connect and Load: Automatically configuring with saved settings...');
                
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
                    
                    console.log('Configuration completed via reconnectAndLoad');
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

// Make showWelcomeScreen available globally
window.showWelcomeScreen = showWelcomeScreen;