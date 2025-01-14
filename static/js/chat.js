class ChatManager {
    constructor(roomName, username) {
        this.roomName = roomName;
        this.username = username;
        this.messageInput = document.getElementById('messageInput');
        this.chatForm = document.getElementById('chatForm');
        this.messagesContainer = document.getElementById('messagesContainer');
        this.typingIndicator = document.getElementById('typingIndicator');
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.typingTimeout = null;
        this.messageQueue = new Map(); // For tracking message status
        this.processedMessages = new Set(); // Add this to track processed messages
        this.lastReadTimestamp = null;
        this.unreadSeparatorAdded = false;
        this.init();
    }

    init() {
        this.connectWebSocket();
        this.setupEventListeners();
        this.setupTypingDetection();
    }

    setupEventListeners() {
        this.chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage();
        });

        // Handle visibility change for online/offline status
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                this.reconnectWebSocket();
            }
        });

        // Handle scroll for loading more messages
        this.messagesContainer.addEventListener('scroll', () => {
            if (this.messagesContainer.scrollTop === 0) {
                this.loadMoreMessages();
            }
        });

        // Add keyboard event listener for auto-focusing input
        document.addEventListener('keydown', (e) => {
            // Ignore if the input is already focused or if user is typing in another input/textarea
            if (document.activeElement === this.messageInput || 
                document.activeElement.tagName === 'INPUT' || 
                document.activeElement.tagName === 'TEXTAREA') {
                return;
            }

            // Ignore special keys like Ctrl, Alt, etc.
            if (e.ctrlKey || e.altKey || e.metaKey) {
                return;
            }

            // Ignore function keys and other special keys
            if (e.key.length > 1) {
                return;
            }

            // Focus the input and set its value to the pressed key
            this.messageInput.focus();
            // Don't set the value directly to prevent duplicate characters
            // The normal keypress event will handle the character input
        });
    }

    setupTypingDetection() {
        this.messageInput.addEventListener('input', () => {
            if (this.typingTimeout) {
                clearTimeout(this.typingTimeout);
            }

            this.sendTypingStatus(true);
            this.typingTimeout = setTimeout(() => {
                this.sendTypingStatus(false);
            }, 1000);
        });
    }

    connectWebSocket() {
        const wsScheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const wsPath = `${wsScheme}://${window.location.host}/ws/chat/${this.roomName}/`;
        
        this.ws = new WebSocket(wsPath);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
            this.messageQueue.forEach((msg, id) => {
                if (msg.status === 'pending') {
                    this.resendMessage(id);
                }
            });
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.handleDisconnect();
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.handleDisconnect();
        };
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'message':
                if (data.sender !== this.username && !this.processedMessages.has(data.message_id)) {
                    this.displayMessage(data);
                    // Send delivery receipt
                    if (this.ws.readyState === WebSocket.OPEN) {
                        this.ws.send(JSON.stringify({
                            type: 'delivery_receipt',
                            message_id: data.message_id
                        }));
                    }
                    this.processedMessages.add(data.message_id);
                    
                    // Send read receipt if chat is visible
                    if (document.visibilityState === 'visible') {
                        this.sendReadReceipt();
                        this.markMessageAsRead(data.message_id);
                    }
                }
                break;
            case 'delivery_status':
                this.updateMessageStatus(data.message_id, data.status);
                break;
            case 'read_status':
                this.updateAllMessagesAsRead(data.user);
                this.lastReadTimestamp = new Date().toISOString();
                break;
            case 'typing':
                this.updateTypingIndicator(data);
                break;
            case 'status':
                this.updateUserStatus(data);
                break;
            case 'error':
                this.handleError(data.message);
                break;
        }
    }

    handleDisconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
            setTimeout(() => this.connectWebSocket(), delay);
        } else {
            this.handleError('Connection lost. Please refresh the page.');
        }
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message) return;

        const messageId = Date.now().toString();
        const messageData = {
            type: 'message',
            message: message,
            room_id: this.roomName
        };
        const localMessageData = {
            message: message,
            sender: this.username,
            timestamp: new Date().toISOString(),
            message_id: messageId,
            status: 'pending'
        };
        // Add to message queue
        this.messageQueue.set(messageId, {
            content: message,
            status: 'pending',
            attempts: 0
        });

        this.displayMessage(localMessageData);
        this.processedMessages.add(messageId);
        this.messageInput.value = '';
        this.scrollToBottom();

        try {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify(messageData));
            } else {
                throw new Error('WebSocket is not connected');
            }
        } catch (error) {
            console.error('Error sending message:', error);
            this.updateMessageStatus(messageId, 'failed');
            const errorDiv = document.createElement('div');
            errorDiv.className = 'message-error';
            errorDiv.textContent = 'Failed to send message. Click to retry.';
            const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
            if (messageElement) {
                messageElement.appendChild(errorDiv);
                errorDiv.onclick = () => this.resendMessage(messageId);
            }
        }
    }

    resendMessage(messageId) {
        const message = this.messageQueue.get(messageId);
        if (message && message.status === 'failed') {
            const messageData = {
                type: 'message',
                message: message.content,
                room_id: this.roomName
            };
            
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify(messageData));
                this.updateMessageStatus(messageId, 'pending');
            }
        }
    }

    sendTypingStatus(isTyping) {
        if (this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'typing',
                is_typing: isTyping
            }));
        }
    }

    sendReadReceipt() {
        if (this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'read_receipt'
            }));
        }
    }

    updateTypingIndicator(data) {
        if (data.user !== this.username) {
            if (data.is_typing) {
                this.typingIndicator.innerHTML = `
                    <div class="typing-dots">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                `;
            } else {
                this.typingIndicator.innerHTML = '';
            }
        }
    }

    updateUserStatus(data) {
        const statusElement = document.querySelector('.user-status');
        if (statusElement) {
            if (data.status === 'online') {
                statusElement.innerHTML = '<span class="status-text online">Online</span>';
            } else {
                const timestamp = data.last_seen;
                const serverNow = new Date().toISOString();
                statusElement.innerHTML = `
                    <span class="status-text moment-fromnow" 
                          data-timestamp="${timestamp}" 
                          data-server-now="${serverNow}">
                        Last seen ${timestamp}
                    </span>
                `;
                updateMomentTimes(); // This function is defined in base.html
            }
        }
    }

    displayMessage(data) {
        // Add unread separator if needed
        if (!data.sender === this.username) {
            this.addUnreadMessagesSeparator(data.timestamp);
        }

        const messageDiv = document.createElement('div');
        const isSent = data.sender === this.username;
        const isThumbsUp = data.message === '👍';
        
        messageDiv.className = `message ${isSent ? 'sent' : 'received'}`;
        if (isThumbsUp) {
            messageDiv.classList.add('thumbs-up-message');
        }
        
        // Add unread class if message is unread
        if (!isSent && !data.is_read) {
            messageDiv.classList.add('unread');
        }
        
        if (data.message_id) {
            messageDiv.setAttribute('data-message-id', data.message_id);
        }
        
        const formatTime = (timestamp) => {
            if (!timestamp) {
                timestamp = new Date().toISOString();
            }
            const date = moment(timestamp);
            return date.fromNow();
        };

        const timestamp = formatTime(data.timestamp);
        const status = data.status || 'sent';
        const statusIcon = this.getStatusIcon(status);
        
        if (isThumbsUp) {
            messageDiv.innerHTML = `
                <div class="message-content large-thumbs-up">
                    <i class="fas fa-thumbs-up like-icon"></i>
                </div>
                <div class="message-info">
                    ${isSent ? `<span class="message-status ${status}">${statusIcon}</span>` : ''}
                </div>
            `;
        } else {
            messageDiv.innerHTML = `
                <div class="message-content">
                    ${this.escapeHtml(data.message)}
                </div>
                <div class="message-info">
                    <span class="time">${timestamp}</span>
                    ${isSent ? `<span class="message-status ${status}">${statusIcon}</span>` : ''}
                </div>
            `;
        }
        
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    getStatusIcon(status) {
        switch (status) {
            case 'sent':
                return '<i class="fas fa-check"></i>';
            case 'delivered':
                return '<i class="fas fa-check"></i><i class="fas fa-check"></i>';
            case 'read':
                return '<i class="fas fa-check text-primary"></i><i class="fas fa-check text-primary"></i>';
            default:
                return '<i class="fas fa-clock"></i>';
        }
    }

    updateMessageStatus(messageId, status) {
        const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
        if (messageElement) {
            const statusElement = messageElement.querySelector('.message-status');
            if (statusElement) {
                statusElement.className = `message-status ${status}`;
                statusElement.innerHTML = this.getStatusIcon(status);
            }
        }
    }

    handleError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        this.messagesContainer.appendChild(errorDiv);
        setTimeout(() => errorDiv.remove(), 5000);
    }

    async loadMoreMessages() {
        // Implementation for loading more messages
        // This would be implemented when backend pagination is added
    }

    scrollToBottom() {
        // Smooth scroll to bottom with a small delay to ensure content is rendered
        setTimeout(() => {
            this.messagesContainer.scrollTo({
                top: this.messagesContainer.scrollHeight,
                behavior: 'smooth'
            });
        }, 100);
    }

    escapeHtml(unsafe) {
        if (!unsafe) return '';
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    updateAllMessagesAsRead(username) {
        if (username !== this.username) {
            const messages = document.querySelectorAll('.message.sent');
            messages.forEach(messageElement => {
                const statusElement = messageElement.querySelector('.message-status');
                if (statusElement) {
                    statusElement.className = 'message-status read';
                    statusElement.innerHTML = this.getStatusIcon('read');
                }
            });
        }
    }

    setupEventListeners() {
        this.chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            if (this.messageInput.value.trim()) {
                this.sendMessage();
            } else {
                this.sendLike();
            }
        });
    
        // Rest of your existing event listeners...
    }
    
    sendLike() {
        const messageId = Date.now().toString();
        const messageData = {
            type: 'message',
            message: '👍',
            room_id: this.roomName
        };
        const localMessageData = {
            message: '👍',
            sender: this.username,
            timestamp: new Date().toISOString(),
            message_id: messageId,
            status: 'pending'
        };
        
        // Add to message queue
        this.messageQueue.set(messageId, {
            content: '👍',
            status: 'pending',
            attempts: 0
        });

        this.displayMessage(localMessageData);
        this.processedMessages.add(messageId);

        try {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify(messageData));
            } else {
                throw new Error('WebSocket is not connected');
            }
        } catch (error) {
            console.error('Error sending message:', error);
            this.updateMessageStatus(messageId, 'failed');
            const errorDiv = document.createElement('div');
            errorDiv.className = 'message-error';
            errorDiv.textContent = 'Failed to send message. Click to retry.';
            const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
            if (messageElement) {
                messageElement.appendChild(errorDiv);
                errorDiv.onclick = () => this.resendMessage(messageId);
            }
        }
    }

    addUnreadMessagesSeparator(timestamp) {
        if (!this.unreadSeparatorAdded && this.lastReadTimestamp && 
            new Date(timestamp) > new Date(this.lastReadTimestamp)) {
            const separatorDiv = document.createElement('div');
            separatorDiv.className = 'unread-messages-separator';
            separatorDiv.innerHTML = '<span>Unread Messages</span>';
            this.messagesContainer.appendChild(separatorDiv);
            this.unreadSeparatorAdded = true;
        }
    }

    async initializeLastReadTimestamp() {
        try {
            const response = await fetch(`/api/chat/${this.roomName}/last-read/`);
            const data = await response.json();
            this.lastReadTimestamp = data.last_read_timestamp;
        } catch (error) {
            console.error('Error fetching last read timestamp:', error);
        }
    }

    markMessageAsRead(messageId) {
        const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
        if (messageElement) {
            messageElement.classList.remove('unread');
            const statusElement = messageElement.querySelector('.message-status');
            if (statusElement) {
                statusElement.className = 'message-status read';
                statusElement.innerHTML = this.getStatusIcon('read');
            }
        }
    }
}

// Initialize chat when the page loads
document.addEventListener('DOMContentLoaded', () => {
    const roomName = document.getElementById('messagesContainer').dataset.roomId;
    const username = localStorage.getItem('username');
    if (roomName && username) {
        console.log('Initializing chat with roomName:', roomName, 'and username:', username);
        new ChatManager(roomName, username);
    }
}); 