// Chatbot Module - Frontend

let currentChatLanguage = 'en-US';
let chatHistory = [];

async function sendChatMessage(message, isFloating = false) {
    if (!message.trim()) return;

    const messagesContainer = isFloating ? 
        document.getElementById('floating-chatbot-messages') : 
        document.getElementById('chatbot-messages');
    
    // Add user message to chat
    addChatMessage(message, 'user', messagesContainer);

    try {
        const response = await apiRequest(API_CONFIG.ENDPOINTS.CHATBOT.CHAT, {
            method: 'POST',
            body: JSON.stringify({
                message: message.trim(),
                language: currentChatLanguage
            })
        });

        if (response.success) {
            // Add bot response to chat
            addChatMessage(response.data.botResponse, 'bot', messagesContainer);
            
            // Store in chat history
            chatHistory.push({
                user: message,
                bot: response.data.botResponse,
                timestamp: response.data.timestamp
            });

            // Auto-play TTS if enabled
            const autoTTS = localStorage.getItem('agricare_tts_auto');
            if (autoTTS === 'true') {
                playTTS(response.data.botResponse, currentChatLanguage);
            }
        } else {
            throw new Error('Chat response failed');
        }
    } catch (error) {
        console.error('Chat error:', error);
        addChatMessage('Sorry, I encountered an error. Please try again.', 'bot', messagesContainer);
    }

    // Clear input
    const inputId = isFloating ? 'floating-chatbot-input' : 'chatbot-input';
    document.getElementById(inputId).value = '';
}

function addChatMessage(message, sender, container) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${sender}-message`;
    
    // Format message with basic HTML support
    const formattedMessage = message
        .replace(/\*\*(.*?)\*\*/g, '<b>$1</b>')
        .replace(/\*(.*?)\*/g, '<i>$1</i>');
    
    messageDiv.innerHTML = formattedMessage;
    
    container.appendChild(messageDiv);
    container.scrollTop = container.scrollHeight;

    // Remove empty state message if present
    const emptyState = container.querySelector('.text-center');
    if (emptyState) {
        emptyState.remove();
    }
}

function initializeChatbot() {
    const languageView = document.getElementById('language-selection-view');
    const chatInterface = document.getElementById('chat-interface');
    
    // Check if language is already selected
    const savedLang = localStorage.getItem('agricare_chat_language');
    if (savedLang) {
        currentChatLanguage = savedLang;
        languageView.classList.add('hidden');
        chatInterface.classList.remove('hidden');
        loadChatHistory();
    } else {
        languageView.classList.remove('hidden');
        chatInterface.classList.add('hidden');
    }
}

function selectChatLanguage(language) {
    currentChatLanguage = language;
    localStorage.setItem('agricare_chat_language', language);
    
    document.getElementById('language-selection-view').classList.add('hidden');
    document.getElementById('chat-interface').classList.remove('hidden');
    
    // Update TTS language dropdown
    document.getElementById('chatbot-tts-lang').value = language;
    
    loadChatHistory();
    
    // Send welcome message
    const welcomeMessages = {
        'en-US': "Hello! I'm AgriBot, your farming assistant. How can I help you today?"
    };

    const welcomeMessage = welcomeMessages[language] || welcomeMessages['en-US'];
    addChatMessage(welcomeMessage, 'bot', document.getElementById('chatbot-messages'));
}

function loadChatHistory() {
    const savedHistory = localStorage.getItem(`agricare_chat_history_${currentUser?.uid || 'anonymous'}`);
    if (savedHistory) {
        chatHistory = JSON.parse(savedHistory);
        const messagesContainer = document.getElementById('chatbot-messages');
        messagesContainer.innerHTML = '';
        
        chatHistory.forEach(chat => {
            addChatMessage(chat.user, 'user', messagesContainer);
            addChatMessage(chat.bot, 'bot', messagesContainer);
        });
    }
}

function saveChatHistory() {
    localStorage.setItem(`agricare_chat_history_${currentUser?.uid || 'anonymous'}`, JSON.stringify(chatHistory));
}

function clearChatHistory() {
    chatHistory = [];
    localStorage.removeItem(`agricare_chat_history_${currentUser?.uid || 'anonymous'}`);
    localStorage.removeItem('agricare_chat_language');
    
    // Reset chatbot interface
    const messagesContainer = document.getElementById('chatbot-messages');
    messagesContainer.innerHTML = '';
    
    // Show language selection again
    document.getElementById('language-selection-view').classList.remove('hidden');
    document.getElementById('chat-interface').classList.add('hidden');
    
    showNotification('Chat history cleared', 'success');
}

// Text-to-Speech functionality
function playTTS(text, language) {
    if ('speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = language;
        
        // Adjust voice settings based on language
        const voices = speechSynthesis.getVoices();
        const matchingVoice = voices.find(voice => voice.lang.startsWith(language.split('-')[0]));
        if (matchingVoice) {
            utterance.voice = matchingVoice;
        }
        
        speechSynthesis.speak(utterance);
    } else {
        showNotification('Text-to-speech not supported', 'error');
    }
}

// Voice recognition functionality
function startVoiceRecognition() {
    if ('webkitSpeechRecognition' in window) {
        const recognition = new webkitSpeechRecognition();
        recognition.lang = currentChatLanguage;
        recognition.continuous = false;
        recognition.interimResults = false;

        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            document.getElementById('chatbot-input').value = transcript;
        };

        recognition.onerror = function(event) {
            showNotification('Voice recognition error', 'error');
        };

        recognition.start();
        showNotification('Listening...', 'info');
    } else {
        showNotification('Voice recognition not supported', 'error');
    }
}

// Floating chatbot functionality
function initFloatingChatbot() {
    const floatingBtn = document.getElementById('floating-chatbot-btn');
    const floatingModal = document.getElementById('floating-chatbot-modal');
    const closeBtn = document.getElementById('close-floating-chatbot');
    const sendBtn = document.getElementById('floating-chatbot-send');
    const input = document.getElementById('floating-chatbot-input');

    floatingBtn.addEventListener('click', () => {
        floatingModal.classList.toggle('hidden');
    });

    closeBtn.addEventListener('click', () => {
        floatingModal.classList.add('hidden');
    });

    sendBtn.addEventListener('click', () => {
        const message = input.value.trim();
        if (message) {
            sendChatMessage(message, true);
        }
    });

    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const message = input.value.trim();
            if (message) {
                sendChatMessage(message, true);
            }
        }
    });
}

// Initialize chatbot event listeners
function initializeChatbotEventListeners() {
    // Language selection buttons
    document.querySelectorAll('.lang-select-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const language = btn.getAttribute('data-lang');
            selectChatLanguage(language);
        });
    });

    // Send message button
    document.getElementById('chatbot-send-btn').addEventListener('click', () => {
        const message = document.getElementById('chatbot-input').value.trim();
        if (message) {
            sendChatMessage(message);
        }
    });

    // Input field enter key
    document.getElementById('chatbot-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const message = e.target.value.trim();
            if (message) {
                sendChatMessage(message);
            }
        }
    });

    // Voice command button
    document.getElementById('voice-command-btn').addEventListener('click', startVoiceRecognition);

    // TTS play button
    document.getElementById('chatbot-play-tts').addEventListener('click', () => {
        if (chatHistory.length > 0) {
            const lastBotMessage = chatHistory[chatHistory.length - 1].bot;
            const ttsLang = document.getElementById('chatbot-tts-lang').value;
            playTTS(lastBotMessage, ttsLang);
        } else {
            showNotification('No messages to play', 'error');
        }
    });

    // Initialize floating chatbot
    initFloatingChatbot();

    // Save chat history before page unload
    window.addEventListener('beforeunload', saveChatHistory);
}