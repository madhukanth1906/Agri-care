// Main Application Module - Frontend
// Coordinates all modules and initializes the application

class AgriCareApp {
    constructor() {
        this.currentView = 'login-page';
        this.isAuthenticated = false;
        this.user = null;
        this.modules = {};
        
        console.log('AgriCare modules ready');
    }

    async init() {
        if (window.translationManager) {
            await window.translationManager.init();
            console.log('Translation manager ready');
        } else {
            console.warn('Translation manager not found yet; continuing with the app');
        }
        
        await this.checkAuthStatus();
        
        this.initializeEventListeners();
        
        this.setupNavigation();
        
        this.loadInitialView();
        
        console.log('AgriCare app initialized');
    }

    async checkAuthStatus() {
        // Local test build starts inside the app so UI flows can be exercised quickly.
        console.log('Authentication is bypassed in the local test build');
        this.isAuthenticated = true;
        this.user = { email: 'test@test.com', name: 'Test User' };
        this.showView('main-app');
        return;
        
        const token = localStorage.getItem('agricare_token');
        if (token) {
            try {
                const response = await fetch(`${API_CONFIG.BASE_URL}/auth/verify`, {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });
                
                if (response.ok) {
                    const data = await response.json();
                    this.isAuthenticated = true;
                    this.user = data.user;
                    this.showView('main-app');
                } else {
                    this.logout();
                }
            } catch (error) {
                console.error('Auth verification failed:', error);
                this.logout();
            }
        } else {
            this.showView('login-page');
        }
    }

    initializeEventListeners() {
        console.log('Wiring event listeners');
        
        const loginForm = document.getElementById('login-form');
        if (loginForm) {
            console.log('Login form ready');
            loginForm.addEventListener('submit', (e) => {
                this.handleLogin(e);
            });
        } else {
            console.error('Login form not found');
        }

        const registerForm = document.getElementById('register-form');
        if (registerForm) {
            console.log('Register form ready');
            registerForm.addEventListener('submit', (e) => {
                this.handleRegister(e);
            });
        } else {
            console.error('Register form not found');
        }

        const showRegisterBtn = document.getElementById('toggle-register-btn');
        if (showRegisterBtn) {
            console.log('Register button ready');
            showRegisterBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.showView('register-page');
            });
            showRegisterBtn.onclick = (e) => {
                e.preventDefault();
                this.showView('register-page');
            };
        } else {
            console.error('Register button not found');
        }

        const showLoginBtn = document.getElementById('back-to-login-btn');
        if (showLoginBtn) {
            console.log('Back to login button ready');
            showLoginBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.showView('login-page');
            });
            showLoginBtn.onclick = (e) => {
                e.preventDefault();
                this.showView('login-page');
            };
        } else {
            console.error('Back to login button not found');
        }

        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => this.logout());
        }

        const tabs = document.querySelectorAll('[data-tab]');
        tabs.forEach(tab => {
            tab.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });

        const viewButtons = {
            'weather-view-btn': 'weather-view',
            'disease-view-btn': 'disease-view',
            'yield-view-btn': 'yield-view',
            'chatbot-view-btn': 'chatbot-view',
            'back-to-dashboard-btn': 'main-app'
        };

        Object.entries(viewButtons).forEach(([btnId, view]) => {
            const btn = document.getElementById(btnId);
            if (btn) {
                btn.addEventListener('click', () => this.showView(view));
            }
        });

        const devLoginBtn = document.getElementById('dev-login-btn');
        if (devLoginBtn) {
            devLoginBtn.addEventListener('click', () => this.showDeveloperLogin());
        }

        const languageSelector = document.getElementById('language-selector');
        if (languageSelector) {
            languageSelector.addEventListener('change', (e) => this.changeLanguage(e.target.value));
        }

        this.initializeMenuCards();
    }

    initializeMenuCards() {
        console.log('Initializing menu cards');
        
        const menuCards = {
            'menu-weather': 'weather-view',
            'menu-disease': 'disease-view',
            'menu-yield': 'yield-view',
            'menu-chatbot': 'chatbot-view'
        };

        Object.entries(menuCards).forEach(([menuId, viewId]) => {
            const menuCard = document.getElementById(menuId);
            if (menuCard) {
                console.log(`Menu card ready: ${menuId}`);

                menuCard.removeEventListener('click', menuCard._clickHandler);
                menuCard.removeEventListener('keydown', menuCard._keydownHandler);

                menuCard._clickHandler = (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    this.showView(viewId);
                    return false;
                };
                
                menuCard._keydownHandler = (e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        console.log(`Keyboard activation on ${menuId}`);
                        this.showView(viewId);
                    }
                };

                menuCard.addEventListener('click', menuCard._clickHandler);
                menuCard.addEventListener('keydown', menuCard._keydownHandler);

                const backBtn = document.getElementById('back-to-menu-btn');
                if (backBtn) {
                    backBtn.addEventListener('click', () => {
                        backBtn.classList.add('hidden');
                        this.showView('main-app');
                    });
                }
                
            } else {
                console.error(`Menu card not found: ${menuId}`);
            }
        });
        
        console.log('Menu cards ready');
    }

    setupNavigation() {
        // Back button navigation
        const backButtons = document.querySelectorAll('.back-btn');
        backButtons.forEach(btn => {
            btn.addEventListener('click', () => this.showView('main-app'));
        });

        // Handle browser back/forward
        window.addEventListener('popstate', (e) => {
            if (e.state && e.state.view) {
                this.showView(e.state.view, false);
            }
        });
    }

    loadInitialView() {
        if (this.isAuthenticated) {
            this.showView('main-app');
            this.updateUserInfo();
            this.loadDashboardData();
        } else {
            this.showView('login-page');
        }
    }

    async handleLogin(e) {
        e.preventDefault();
        
        const email = document.getElementById('username').value;
        const password = document.getElementById('password').value;

        if (!email || !password) {
            this.showNotification('Please fill in all fields', 'error');
            return;
        }

        try {
            const response = await fetch(`${API_CONFIG.BASE_URL}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();

            if (response.ok) {
                localStorage.setItem('agricare_token', data.token);
                this.isAuthenticated = true;
                this.user = data.user;
                this.showView('main-app');
                this.updateUserInfo();
                this.loadDashboardData();
                this.showNotification('Login successful!', 'success');
            } else {
                this.showNotification(data.message || 'Login failed', 'error');
            }
        } catch (error) {
            console.error('Login request failed:', error);
            this.showNotification('Network error. Please try again.', 'error');
        }
    }

    async handleRegister(e) {
        e.preventDefault();
        
        const email = document.getElementById('register-email').value;
        const password = document.getElementById('register-password').value;

        if (!email || !password) {
            this.showNotification('Please fill in all fields', 'error');
            return;
        }

        try {
            const response = await fetch(`${API_CONFIG.BASE_URL}/auth/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();

            if (response.ok) {
                this.showNotification('Registration successful! Please login.', 'success');
                this.showView('login-page');
                document.getElementById('register-form').reset();
            } else {
                this.showNotification(data.message || 'Registration failed', 'error');
            }
        } catch (error) {
            console.error('Registration request failed:', error);
            this.showNotification('Network error. Please try again.', 'error');
        }
    }

    logout() {
        localStorage.removeItem('agricare_token');
        this.isAuthenticated = false;
        this.user = null;
        this.showView('login-page');
        this.showNotification('Logged out successfully', 'success');
    }

    showView(viewId, pushState = true) {
        console.log(`Showing view: ${viewId}`);
        
        const authContainer = document.getElementById('auth-container');
        const mainApp = document.getElementById('main-app');
        const devApp = document.getElementById('dev-app');
        
        if (authContainer) authContainer.classList.add('hidden');
        if (mainApp) mainApp.classList.add('hidden');
        if (devApp) devApp.classList.add('hidden');
        
        const loginPage = document.getElementById('login-page');
        const registerPage = document.getElementById('register-page');
        
        if (loginPage) loginPage.classList.add('hidden');
        if (registerPage) registerPage.classList.add('hidden');

        // Hide all main app views
        const views = ['main-menu', 'weather-view', 'disease-view', 'yield-view', 'chatbot-view'];
        views.forEach(viewName => {
            const view = document.getElementById(viewName);
            if (view) view.classList.add('hidden');
        });

        // Show target view
        if (viewId === 'login-page') {
            if (authContainer) authContainer.classList.remove('hidden');
            if (loginPage) {
                loginPage.classList.remove('hidden');
                console.log('✅ Login page shown');
            }
        } else if (viewId === 'register-page') {
            if (authContainer) authContainer.classList.remove('hidden');
            if (registerPage) {
                registerPage.classList.remove('hidden');
                console.log('✅ Register page shown');
            }
        } else if (viewId === 'main-app') {
            if (mainApp) {
                mainApp.classList.remove('hidden');
                const mainMenu = document.getElementById('main-menu');
                if (mainMenu) {
                    mainMenu.classList.remove('hidden');
                    console.log('✅ Main app and menu shown');
                    // Re-initialize menu card listeners after showing main app
                    setTimeout(() => {
                        this.initializeMenuCards();
                    }, 100); // Small delay to ensure DOM is updated
                }
            }
        } else if (viewId === 'dev-app') {
            if (devApp) {
                devApp.classList.remove('hidden');
                console.log('✅ Developer app shown');
            }
        } else {
            // Handle specific views within main app
            if (mainApp) {
                mainApp.classList.remove('hidden');
                const targetView = document.getElementById(viewId);
                if (targetView) {
                    targetView.classList.remove('hidden');
                    console.log(`✅ ${viewId} shown`);
                    
                    // Show back button for sub-views
                    const backBtn = document.getElementById('back-to-menu-btn');
                    if (backBtn && viewId !== 'main-menu') {
                        backBtn.classList.remove('hidden');
                    }
                }
            }
        }

        this.currentView = viewId;

        // Apply translations for the current view (non-blocking)
        if (window.translationManager) {
            window.translationManager.applyTranslations().then(() => {
                console.log('✅ Translations applied for', viewId);
            }).catch(error => {
                console.error('❌ Translation error:', error);
            });
        }

        // Update browser history
        if (pushState) {
            history.pushState({ view: viewId }, '', `#${viewId}`);
        }

        // Initialize view-specific functionality
        this.initializeView(viewId);
    }

    initializeView(viewId) {
        switch (viewId) {
            case 'weather-view':
                initializeWeatherEventListeners();
                break;
            case 'disease-view':
                initializeDiseaseEventListeners();
                break;
            case 'yield-view':
                initializeYieldEventListeners();
                break;
            case 'chatbot-view':
                initializeChatbotEventListeners();
                break;
            case 'dev-app':
                // Developer views are handled by developer.js
                break;
        }
    }

    switchTab(tabId) {
        // Remove active class from all tabs
        const tabs = document.querySelectorAll('[data-tab]');
        tabs.forEach(tab => tab.classList.remove('bg-green-600'));

        // Add active class to clicked tab
        const activeTab = document.querySelector(`[data-tab="${tabId}"]`);
        if (activeTab) {
            activeTab.classList.add('bg-green-600');
        }

        // Show corresponding content
        const contents = document.querySelectorAll('.tab-content');
        contents.forEach(content => content.classList.add('hidden'));

        const activeContent = document.getElementById(tabId);
        if (activeContent) {
            activeContent.classList.remove('hidden');
        }
    }

    updateUserInfo() {
        if (this.user) {
            const userNameElements = document.querySelectorAll('.user-name');
            userNameElements.forEach(el => {
                el.textContent = this.user.name || 'User';
            });

            const userEmailElements = document.querySelectorAll('.user-email');
            userEmailElements.forEach(el => {
                el.textContent = this.user.email || '';
            });
        }
    }

    async loadDashboardData() {
        // Load quick stats for dashboard
        try {
            // Get current weather for dashboard (commented out for now)
            // const position = await this.getCurrentPosition();
            // await loadWeatherByCoordinates(position.coords.latitude, position.coords.longitude);
        } catch (error) {
            console.log('Could not load weather data for dashboard:', error);
        }

        // Update last activities
        this.updateLastActivities();
    }

    getCurrentPosition() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('Geolocation not supported'));
                return;
            }

            navigator.geolocation.getCurrentPosition(resolve, reject, {
                timeout: 10000,
                enableHighAccuracy: false
            });
        });
    }

    updateLastActivities() {
        const activities = JSON.parse(localStorage.getItem('agricare_activities') || '[]');
        const activitiesList = document.getElementById('recent-activities');
        
        if (activitiesList && activities.length > 0) {
            activitiesList.innerHTML = activities.slice(0, 5).map(activity => `
                <li class="text-sm text-gray-600">${activity.type} - ${activity.timestamp}</li>
            `).join('');
        }
    }

    addActivity(type, description) {
        const activities = JSON.parse(localStorage.getItem('agricare_activities') || '[]');
        activities.unshift({
            type: type,
            description: description,
            timestamp: new Date().toLocaleString()
        });
        
        // Keep only last 20 activities
        activities.splice(20);
        
        localStorage.setItem('agricare_activities', JSON.stringify(activities));
    }

    showDeveloperLogin() {
        const password = prompt('Enter developer password:');
        if (password === 'agricare2024' || password === 'founder2024') {
            this.showView('dev-app');
            // The developer.js will handle showing the appropriate sections
        } else if (password !== null) {
            this.showNotification('Invalid developer password', 'error');
        }
    }

    changeLanguage(language) {
        // Simple language switching implementation
        const translations = {
            'en': {
                'app-title': 'AgriCare',
                'welcome-msg': 'Welcome to AgriCare'
            },
            'hi': {
                'app-title': 'एग्रीकेयर',
                'welcome-msg': 'एग्रीकेयर में आपका स्वागत है'
            },
            'te': {
                'app-title': 'అగ్రికేర్',
                'welcome-msg': 'అగ్రికేర్‌కు స్వాగతం'
            }
        };

        const texts = translations[language];
        if (texts) {
            Object.entries(texts).forEach(([key, value]) => {
                const elements = document.querySelectorAll(`[data-translate="${key}"]`);
                elements.forEach(el => el.textContent = value);
            });
        }

        localStorage.setItem('agricare_language', language);
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 ${
            type === 'success' ? 'bg-green-500' :
            type === 'error' ? 'bg-red-500' :
            type === 'warning' ? 'bg-yellow-500' :
            'bg-blue-500'
        } text-white`;
        
        notification.textContent = message;
        document.body.appendChild(notification);

        // Auto remove after 3 seconds
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    // Utility method for API calls with authentication
    async apiCall(endpoint, options = {}) {
        const token = localStorage.getItem('agricare_token');
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                ...(token && { 'Authorization': `Bearer ${token}` })
            }
        };

        const mergedOptions = {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...options.headers
            }
        };

        try {
            const response = await fetch(`${API_CONFIG.BASE_URL}${endpoint}`, mergedOptions);
            
            if (response.status === 401) {
                this.logout();
                throw new Error('Authentication required');
            }

            return response;
        } catch (error) {
            console.error('API call failed:', error);
            throw error;
        }
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('Initializing AgriCare app');

    window.agriCareApp = new AgriCareApp();
    window.agriCareApp.init();
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AgriCareApp;
}