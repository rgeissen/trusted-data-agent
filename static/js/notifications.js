import { state } from './state.js';
import * as UI from './ui.js';
import * as DOM from './domElements.js';
import { handleLoadSession } from './eventHandlers.js';

function showRestQueryNotification(message) {
    const notificationContainer = document.createElement('div');
    notificationContainer.id = 'rest-notification';
    notificationContainer.className = 'notification-banner';

    const messageElement = document.createElement('p');
    messageElement.textContent = message;

    const buttonContainer = document.createElement('div');

    const refreshButton = document.createElement('button');
    refreshButton.textContent = 'Refresh';
    refreshButton.onclick = () => {
        window.location.reload();
    };

    const closeButton = document.createElement('button');
    closeButton.textContent = 'Close';
    closeButton.onclick = () => {
        notificationContainer.remove();
    };

    buttonContainer.appendChild(refreshButton);
    buttonContainer.appendChild(closeButton);

    notificationContainer.appendChild(messageElement);
    notificationContainer.appendChild(buttonContainer);

    document.body.appendChild(notificationContainer);
}

function showReconfigurationNotification(data) {
    const overlay = document.createElement('div');
    overlay.className = 'fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50';

    const modal = document.createElement('div');
    modal.className = 'glass-panel rounded-xl shadow-2xl w-full max-w-lg p-6';

    const title = document.createElement('h3');
    title.className = 'text-xl font-bold mb-4 header-title';
    title.textContent = 'Application Reconfigured';

    const message = document.createElement('p');
    message.className = 'text-gray-300 mb-4';
    message.textContent = data.message;

    const configDetails = document.createElement('pre');
    configDetails.className = 'bg-gray-900/50 p-4 rounded-md text-xs text-gray-300 overflow-x-auto';
    configDetails.textContent = JSON.stringify(data.config, null, 2);

    const buttonContainer = document.createElement('div');
    buttonContainer.className = 'flex justify-end mt-6';

    const refreshButton = document.createElement('button');
    refreshButton.className = 'px-4 py-2 rounded-md bg-teradata-orange hover:bg-teradata-orange-dark transition-colors font-semibold';
    refreshButton.textContent = 'Refresh Now';
    refreshButton.onclick = () => {
        window.location.reload();
    };

    buttonContainer.appendChild(refreshButton);

    modal.appendChild(title);
    modal.appendChild(message);
    modal.appendChild(configDetails);
    modal.appendChild(buttonContainer);

    overlay.appendChild(modal);
    document.body.appendChild(overlay);
}

export function subscribeToNotifications() {
    if (!state.userUUID) {
        console.warn("Cannot subscribe to notifications without a user UUID.");
        return;
    }

    const eventSource = new EventSource(`/api/notifications/subscribe?user_uuid=${state.userUUID}`);

    eventSource.addEventListener('notification', (event) => {
        const data = JSON.parse(event.data);

        switch (data.type) {
            case 'reconfiguration':
                showReconfigurationNotification(data.payload);
                break;
            case 'info':
                showRestQueryNotification(data.message);
                break;
            case 'new_session_created': {
                const newSession = data.payload;
                console.log("New session created via REST API:", newSession);
                // Add the new session to the UI list, but do not make it active
                const sessionItem = UI.addSessionToList(newSession, false);
                DOM.sessionList.prepend(sessionItem);
                break;
            }
            case 'session_name_update': {
                const { session_id, newName } = data.payload;
                console.log(`[notifications.js] Received session_name_update: session_id=${session_id}, newName=${newName}`);
                UI.updateSessionListItemName(session_id, newName);
                UI.moveSessionToTop(session_id);
                break;
            }
            case 'session_model_update': {
                const { session_id, models_used, last_updated, provider, model } = data.payload;
                console.log(`[notifications.js] Received session_model_update for session_id=${session_id}`);
                console.log(`[notifications.js] Payload: provider=${provider}, model=${model}, models_used=`, models_used);
                UI.updateSessionModels(session_id, models_used);
                UI.updateSessionTimestamp(session_id, last_updated);
                UI.moveSessionToTop(session_id);

                if (session_id === state.currentSessionId) {
                    console.log(`[notifications.js] Session ${session_id} is current session. Updating state.currentProvider from ${state.currentProvider} to ${provider}`);
                    console.log(`[notifications.js] Updating state.currentModel from ${state.currentModel} to ${model}`);
                    state.currentProvider = provider;
                    state.currentModel = model;
                    UI.updateStatusPromptName();
                    console.log(`[notifications.js] UI.updateStatusPromptName() called.`);
                } else {
                    console.log(`[notifications.js] Session ${session_id} is NOT current session. State not updated.`);
                }
                break;
            }
            // --- MODIFICATION START: Add handlers for REST task events ---
            case 'rest_task_update': {
                const { task_id, session_id, event } = data.payload;
                if (session_id !== state.currentSessionId) break;

                const isFinal = (event.type === 'final_answer' || event.type === 'error' || event.type === 'cancelled');
                
                // The backend now sends a canonical event object, so we can pass it directly.
                UI.updateStatusWindow(event, isFinal, 'rest', task_id);
                break;
            }
            case 'rest_task_complete':
                {
                    const { session_id, turn_id, user_input, final_answer } = data.payload;
                    if (session_id === state.currentSessionId) {
                        // Add the Q&A to the main chat log
                        UI.addMessage('user', user_input, turn_id, true);
                        UI.addMessage('assistant', final_answer, turn_id, true);
                        UI.moveSessionToTop(session_id);
                    } else {
                        // If not the current session, provide a visual cue
                        UI.highlightSession(session_id);
                    }
                    break;
                }
            // --- MODIFICATION END ---
            default:
                console.warn("Unknown notification type:", data.type);
        }
    });

    eventSource.onerror = (error) => {
        console.error("EventSource failed:", error);
        eventSource.close();
    };
}