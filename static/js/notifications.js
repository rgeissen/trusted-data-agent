import { state } from './state.js';

function showNotification(message) {
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

export function subscribeToNotifications() {
    if (!state.userUUID) {
        console.warn("Cannot subscribe to notifications without a user UUID.");
        return;
    }

    const eventSource = new EventSource(`/api/notifications/subscribe?user_uuid=${state.userUUID}`);

    eventSource.addEventListener('notification', (event) => {
        const data = JSON.parse(event.data);
        showNotification(data.message);
    });

    eventSource.onerror = (error) => {
        console.error("EventSource failed:", error);
        eventSource.close();
    };
}
