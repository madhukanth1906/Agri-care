// Configuration and API endpoints
// Note: API_CONFIG is defined in index.html to avoid duplicate declarations

// Default API keys - Load from backend/environment
// DO NOT hardcode API keys in frontend code
const DEFAULT_API_KEYS = {
    ACCUWEATHER: "",
    GEMINI: "",
    HUGGING_FACE: ""
};

// Global state
let currentUser = null;
let selectedDiseaseFile = null;
let uiCodeEditor = null;
let readOnlyUiEditor = null;

// DOM Element Cache - Use lazy loading
const dom = {
    get authContainer() { return document.getElementById('auth-container'); },
    get loginPage() { return document.getElementById('login-page'); },
    get registerPage() { return document.getElementById('register-page'); },
    get mainApp() { return document.getElementById('main-app'); },
    get devApp() { return document.getElementById('dev-app'); },
    get loginForm() { return document.getElementById('login-form'); },
    get registerForm() { return document.getElementById('register-form'); },
    get choiceModal() { return document.getElementById('choice-modal'); },
    get mainMenu() { return document.getElementById('main-menu'); },
    featureViews: {
        get weather() { return document.getElementById('weather-view'); },
        get disease() { return document.getElementById('disease-view'); },
        get yield() { return document.getElementById('yield-view'); },
        get chatbot() { return document.getElementById('chatbot-view'); }
    },
    get backToMenuBtn() { return document.getElementById('back-to-menu-btn'); },
    get siteLanguageSelect() { return document.getElementById('site-language-select'); },
    devSections: {
        get admin() { return document.getElementById('admin-dev-section'); },
        get ui() { return document.getElementById('ui-dev-section'); },
        get founder() { return document.getElementById('founder-dev-section'); }
    },
    get loadingOverlay() { return document.getElementById('loading-overlay'); }
};

// UI Helper Functions
const showLoader = () => {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) overlay.classList.remove('hidden');
};
const hideLoader = () => {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) overlay.classList.add('hidden');
};

// API Helper Functions
async function apiRequest(endpoint, options = {}) {
    const url = `${API_CONFIG.BASE_URL}${endpoint}`;
    const defaultHeaders = {
        'Content-Type': 'application/json',
    };

    // Add auth token if user is logged in
    const token = localStorage.getItem('agricare_token');
    if (token) {
        defaultHeaders['Authorization'] = `Bearer ${token}`;
    }

    const config = {
        headers: defaultHeaders,
        ...options,
        headers: {
            ...defaultHeaders,
            ...options.headers
        }
    };

    try {
        const response = await fetch(url, config);
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({ message: 'Network error' }));
            throw new Error(error.message || `HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error(`API Request failed: ${endpoint}`, error);
        throw error;
    }
}

// Utility Functions
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 ${
        type === 'success' ? 'bg-green-500' :
        type === 'error' ? 'bg-red-500' :
        'bg-blue-500'
    } text-white`;
    notification.innerHTML = `
        <div class="flex items-center">
            <i class="fas ${
                type === 'success' ? 'fa-check-circle' :
                type === 'error' ? 'fa-exclamation-circle' :
                'fa-info-circle'
            } mr-2"></i>
            <span>${message}</span>
        </div>
    `;

    document.body.appendChild(notification);

    // Remove notification after 3 seconds
    setTimeout(() => {
        notification.remove();
    }, 3000);
}