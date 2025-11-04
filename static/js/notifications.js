import { state } from './state.js';

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
            default:
                console.warn("Unknown notification type:", data.type);
        }
    });

    eventSource.onerror = (error) => {
        console.error("EventSource failed:", error);
        eventSource.close();
    };
}