// Authentication Module

// User management functions (local storage for now, will be moved to backend)
const getUsers = () => JSON.parse(localStorage.getItem('agricare_users') || '[]');
const saveUsers = (users) => localStorage.setItem('agricare_users', JSON.stringify(users));

async function registerUser(email, password) {
    try {
        const response = await apiRequest(API_CONFIG.ENDPOINTS.AUTH.REGISTER, {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });
        
        return { success: true, message: 'Registration successful! Please log in.' };
    } catch (error) {
        // Fallback to local storage during transition
        let users = getUsers();
        if (users.find(u => u.email.toLowerCase() === email.toLowerCase())) {
            return { success: false, message: 'An account with this email already exists.' };
        }
        users.push({ email, password });
        saveUsers(users);
        return { success: true, message: 'Registration successful! Please log in.' };
    }
}

async function authenticateUser(email, password) {
    try {
        const response = await apiRequest(API_CONFIG.ENDPOINTS.AUTH.LOGIN, {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });
        
        // Store auth token
        localStorage.setItem('agricare_token', response.token);
        return response.user;
    } catch (error) {
        // Fallback to local storage during transition
        const users = getUsers();
        return users.find(u => u.email.toLowerCase() === email.toLowerCase() && u.password === password);
    }
}

async function signOut() {
    try {
        await apiRequest(API_CONFIG.ENDPOINTS.AUTH.LOGOUT, {
            method: 'POST'
        });
    } catch (error) {
        console.log('Logout API call failed, continuing with local logout');
    }
    
    localStorage.removeItem('agricare_session');
    localStorage.removeItem('agricare_token');
    location.reload();
}

function checkSession() {
    const session = localStorage.getItem('agricare_session');
    if (session) {
        currentUser = JSON.parse(session);
        if (currentUser.role === 'user') {
            showMainApp();
        } else {
            showDevApp();
        }
    }
}

function showMainApp() {
    dom.authContainer.classList.add('hidden');
    dom.choiceModal.classList.add('hidden');
    dom.mainApp.classList.remove('hidden');
    dom.devApp.classList.add('hidden');
    document.getElementById('user-name').textContent = currentUser.displayName;
    
    const savedLang = localStorage.getItem('agricare_language') || 'en-US';
    changeLanguage(savedLang);
    initializeUserSession();
}

function showDevApp() {
    dom.authContainer.classList.add('hidden');
    dom.choiceModal.classList.add('hidden');
    dom.mainApp.classList.add('hidden');
    dom.devApp.classList.remove('hidden');
    document.getElementById('dev-user-name').textContent = `${currentUser.displayName} (${currentUser.role})`;
    
    Object.values(dom.devSections).forEach(section => section.classList.add('hidden'));

    if (currentUser.role === 'ui') {
        dom.devSections.ui.classList.remove('hidden');
        initUiDeveloperPanel();
    } else if (currentUser.role === 'super') {
        dom.devSections.admin.classList.remove('hidden');
        checkAllApiStatus();
    } else if (currentUser.role === 'founder') {
        dom.devSections.founder.classList.remove('hidden');
        initFounderDeveloperPanel();
    }
}

async function initializeUserSession() {
    const userPrefs = JSON.parse(localStorage.getItem(`agricare_prefs_${currentUser.uid}`) || '{}');
    
    // Initialize weather data
    if (userPrefs.lat && userPrefs.lon) {
        try {
            await loadWeatherByCoordinates(userPrefs.lat, userPrefs.lon);
        } catch (err) {
            console.warn('Could not resolve stored location. Error:', err);
            getLocationAndFetchWeather();
        }
    } else {
        getLocationAndFetchWeather();
    }
    
    loadChatHistory();
}

// Event Listeners
function initializeAuthEventListeners() {
    // Login form
    dom.loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value.trim();
        const errorEl = document.getElementById('login-error');
        errorEl.classList.add('hidden');

        const devLogins = { 
            'admin@agricare.dev': { pass: 'admin', role: 'super', displayName: 'Admin' }, 
            'uideveloper@agricare.dev': { pass: 'ui@agricare', role: 'ui', displayName: 'UI Developer' }, 
            'founder@agricare.dev': { pass: 'founder@agricare', role: 'founder', displayName: 'Founder' } 
        };
        
        // Developer login
        if (devLogins[username] && password === devLogins[username].pass) {
            currentUser = { ...devLogins[username], uid: username };
            localStorage.setItem('agricare_session', JSON.stringify(currentUser));
            showDevApp();
            return;
        }

        // Regular user login
        try {
            const user = await authenticateUser(username, password);
            if (user) {
                currentUser = { uid: user.email, displayName: user.email, role: 'user' };
                localStorage.setItem('agricare_session', JSON.stringify(currentUser));
                showMainApp();
            } else {
                errorEl.textContent = 'Invalid username or password.';
                errorEl.classList.remove('hidden');
            }
        } catch (error) {
            errorEl.textContent = 'Login failed. Please try again.';
            errorEl.classList.remove('hidden');
        }
    });

    // Register form
    dom.registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('register-email').value.trim();
        const password = document.getElementById('register-password').value.trim();
        const errorEl = document.getElementById('register-error');
        
        try {
            const result = await registerUser(email, password);
            if (result.success) {
                showNotification(result.message, 'success');
                dom.registerForm.reset();
                dom.registerPage.classList.add('hidden');
                dom.loginPage.classList.remove('hidden');
            } else {
                errorEl.textContent = result.message;
                errorEl.classList.remove('hidden');
            }
        } catch (error) {
            errorEl.textContent = 'Registration failed. Please try again.';
            errorEl.classList.remove('hidden');
        }
    });

    // Toggle between login and register
    document.getElementById('toggle-register-btn').addEventListener('click', () => {
        dom.loginPage.classList.add('hidden');
        dom.registerPage.classList.remove('hidden');
    });

    document.getElementById('back-to-login-btn').addEventListener('click', () => {
        dom.registerPage.classList.add('hidden');
        dom.loginPage.classList.remove('hidden');
    });

    // Sign out buttons
    document.getElementById('signout-btn').addEventListener('click', signOut);
    document.getElementById('dev-signout-btn').addEventListener('click', signOut);

    // View switching
    document.getElementById('go-to-user-btn').addEventListener('click', showMainApp);
    document.getElementById('go-to-dev-btn').addEventListener('click', showDevApp);
}