/**
 * domElements.js
 * * This module centralizes all DOM element selections for the application.
 * Consolidating DOM queries here makes it easier to manage and locate UI element references.
 */

// Chat interface elements
export const chatLog = document.getElementById('chat-log');
export const chatForm = document.getElementById('chat-form');
export const userInput = document.getElementById('user-input');
export const submitButton = document.getElementById('submit-button');
export const sendIcon = document.getElementById('send-icon');
export const loadingSpinner = document.getElementById('loading-spinner');
export const newChatButton = document.getElementById('new-chat-button');
export const voiceInputButton = document.getElementById('voice-input-button');
export const micIcon = document.getElementById('mic-icon');
// --- MODIFICATION START: Add Key Observations Toggle Button elements ---
export const keyObservationsToggleButton = document.getElementById('key-observations-toggle-button');
export const observationsAutoplayOffIcon = document.getElementById('observations-autoplay-off-icon');
export const observationsAutoplayOnIcon = document.getElementById('observations-autoplay-on-icon');
export const observationsOffIcon = document.getElementById('observations-off-icon');
// --- MODIFICATION END ---
export const thinkingIndicator = document.getElementById('thinking-indicator');
export const promptNameDisplay = document.getElementById('prompt-name-display');
export const inputHint = document.getElementById('input-hint');

// Resource tabs
export const resourceTabs = document.getElementById('resource-tabs');

// Prompt Modal elements
export const promptModalOverlay = document.getElementById('prompt-modal-overlay');
export const promptModalContent = document.getElementById('prompt-modal-content');
export const promptModalForm = document.getElementById('prompt-modal-form');
export const promptModalTitle = document.getElementById('prompt-modal-title');
export const promptModalInputs = document.getElementById('prompt-modal-inputs');
export const promptModalClose = document.getElementById('prompt-modal-close');

// Main content area
export const mainContent = document.getElementById('main-content');

// Status window elements
export const statusWindow = document.getElementById('status-window');
export const statusWindowContent = document.getElementById('status-window-content');
export const toggleStatusButton = document.getElementById('toggle-status-button');
export const statusCollapseIcon = document.getElementById('status-collapse-icon');
export const statusExpandIcon = document.getElementById('status-expand-icon');
export const toggleStatusCheckbox = document.getElementById('toggle-status-checkbox');

// Session history panel elements
export const sessionHistoryPanel = document.getElementById('session-history-panel');
export const sessionList = document.getElementById('session-list');
export const toggleHistoryButton = document.getElementById('toggle-history-button');
export const historyCollapseIcon = document.getElementById('history-collapse-icon');
export const historyExpandIcon = document.getElementById('history-expand-icon');
export const toggleHistoryCheckbox = document.getElementById('toggle-history-checkbox');

// Header elements
export const toolHeader = document.getElementById('tool-header');
export const toggleHeaderButton = document.getElementById('toggle-header-button');
export const headerCollapseIcon = document.getElementById('header-collapse-icon');
export const headerExpandIcon = document.getElementById('header-expand-icon');
export const toggleHeaderCheckbox = document.getElementById('toggle-header-checkbox');

// Info Modal elements
export const infoButton = document.getElementById('info-button');
export const infoModalOverlay = document.getElementById('info-modal-overlay');
export const infoModalClose = document.getElementById('info-modal-close');
export const infoModalContent = document.getElementById('info-modal-content');

// Configuration Modal elements
export const configMenuButton = document.getElementById('config-menu-button');
export const configModalOverlay = document.getElementById('config-modal-overlay');
export const configModalContent = document.getElementById('config-modal-content');
export const configModalClose = document.getElementById('config-modal-close');
export const configForm = document.getElementById('config-form');
export const configStatus = document.getElementById('config-status');
export const configLoadingSpinner = document.getElementById('config-loading-spinner');
export const configActionButton = document.getElementById('config-action-button');
export const configActionButtonText = document.getElementById('config-action-button-text');
export const mcpServerNameInput = document.getElementById('mcp-server-name');

// LLM Configuration elements
export const refreshModelsButton = document.getElementById('refresh-models-button');
export const refreshIcon = document.getElementById('refresh-icon');
export const refreshSpinner = document.getElementById('refresh-spinner');
export const llmProviderSelect = document.getElementById('llm-provider');
export const llmModelSelect = document.getElementById('llm-model');
export const llmApiKeyInput = document.getElementById('llm-api-key');
export const apiKeyContainer = document.getElementById('api-key-container');
export const awsCredentialsContainer = document.getElementById('aws-credentials-container');
export const awsAccessKeyIdInput = document.getElementById('aws-access-key-id');
export const awsSecretAccessKeyInput = document.getElementById('aws-secret-access-key');
export const awsRegionInput = document.getElementById('aws-region');
export const awsListingMethodContainer = document.getElementById('aws-listing-method-container');
export const ollamaHostContainer = document.getElementById('ollama-host-container');
export const ollamaHostInput = document.getElementById('ollama-host');
export const chartingIntensitySelect = document.getElementById('charting-intensity');

// Status indicators
export const mcpStatusDot = document.getElementById('mcp-status-dot');
export const llmStatusDot = document.getElementById('llm-status-dot');
export const contextStatusDot = document.getElementById('context-status-dot');

// Window menu
export const windowMenuButton = document.getElementById('window-menu-button');
export const windowDropdownMenu = document.getElementById('window-dropdown-menu');

// Prompt Editor elements
export const promptEditorButton = document.getElementById('prompt-editor-button');
export const promptEditorOverlay = document.getElementById('prompt-editor-overlay');
export const promptEditorContent = document.getElementById('prompt-editor-content');
export const promptEditorTitle = document.getElementById('prompt-editor-title');
export const promptEditorTextarea = document.getElementById('prompt-editor-textarea');
export const promptEditorSave = document.getElementById('prompt-editor-save');
export const promptEditorReset = document.getElementById('prompt-editor-reset');
export const promptEditorClose = document.getElementById('prompt-editor-close');
export const promptEditorStatus = document.getElementById('prompt-editor-status');

// Confirmation Modal elements
export const confirmModalOverlay = document.getElementById('confirm-modal-overlay');
export const confirmModalContent = document.getElementById('confirm-modal-content');
export const confirmModalTitle = document.getElementById('confirm-modal-title');
export const confirmModalBody = document.getElementById('confirm-modal-body');
export const confirmModalConfirm = document.getElementById('confirm-modal-confirm');
export const confirmModalCancel = document.getElementById('confirm-modal-cancel');

// System Prompt Popup elements
export const systemPromptPopupOverlay = document.getElementById('system-prompt-popup-overlay');
export const systemPromptPopupContent = document.getElementById('system-prompt-popup-content');
export const systemPromptPopupTitle = document.getElementById('system-prompt-popup-title');
export const systemPromptPopupBody = document.getElementById('system-prompt-popup-body');
export const systemPromptPopupClose = document.getElementById('system-prompt-popup-close');
export const systemPromptPopupViewFull = document.getElementById('system-prompt-popup-view-full');

// Simple Chat Modal elements
export const chatModalButton = document.getElementById('chat-modal-button');
export const chatModalOverlay = document.getElementById('chat-modal-overlay');
export const chatModalContent = document.getElementById('chat-modal-content');
export const chatModalClose = document.getElementById('chat-modal-close');
export const chatModalForm = document.getElementById('chat-modal-form');
export const chatModalInput = document.getElementById('chat-modal-input');
export const chatModalLog = document.getElementById('chat-modal-log');

// View Prompt Modal elements
export const viewPromptModalOverlay = document.getElementById('view-prompt-modal-overlay');
export const viewPromptModalContent = document.getElementById('view-prompt-modal-content');
export const viewPromptModalTitle = document.getElementById('view-prompt-modal-title');
export const viewPromptModalText = document.getElementById('view-prompt-modal-text');
export const viewPromptModalClose = document.getElementById('view-prompt-modal-close');
