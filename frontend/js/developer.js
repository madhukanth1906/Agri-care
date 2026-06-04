// Developer Panel Module - Frontend

// Developer panel functions
function initUiDeveloperPanel() {
    // Initialize CodeMirror for UI development
    if (typeof CodeMirror !== 'undefined') {
        // Read-only editor for current UI
        readOnlyUiEditor = CodeMirror.fromTextArea(document.getElementById('current-ui-code'), {
            mode: 'htmlmixed',
            theme: 'material-darker',
            lineNumbers: true,
            readOnly: true
        });

        // Editable editor for new UI
        uiCodeEditor = CodeMirror.fromTextArea(document.getElementById('new-ui-code'), {
            mode: 'htmlmixed',
            theme: 'material-darker',
            lineNumbers: true,
            autoCloseTags: true,
            autoCloseBrackets: true
        });

        // Load current UI code
        loadCurrentUiCode();
    }

    // Load commit history
    loadUiCommitHistory();
}

function initFounderDeveloperPanel() {
    // Load full source code
    loadFullSourceCode();
    
    // Load API keys
    loadApiKeys();
    
    // Load full commit history
    loadFounderCommitHistory();
    
    // Update developer status
    updateDeveloperStatus();
}

function loadCurrentUiCode() {
    // Load the current HTML structure (simplified)
    const currentCode = document.documentElement.outerHTML;
    if (readOnlyUiEditor) {
        readOnlyUiEditor.setValue(currentCode.substring(0, 2000) + '...\n// Full code available in source');
    }
}

function loadFullSourceCode() {
    const founderEditor = document.getElementById('founder-source-editor');
    // Load abbreviated version for demo
    founderEditor.value = `// AgriCare Full Source Code
// This is a simplified view for demonstration
// In production, this would load the actual source files

// Frontend Structure:
// - index.html (Main UI)
// - css/styles.css (Styling)
// - js/config.js (Configuration)
// - js/auth.js (Authentication)
// - js/weather.js (Weather Module)
// - js/disease.js (Disease Detection)
// - js/yield.js (Yield Prediction)
// - js/chatbot.js (Chatbot Interface)

// Backend Structure:
// - server.js (Main server)
// - routes/ (API endpoints)
// - services/ (Business logic)
// - middleware/ (Security, auth, etc.)

// Current API Status:
// - Weather Service: Active
// - Disease Detection: Active
// - Yield Prediction: Active
// - Chatbot Service: Active
`;
}

function loadApiKeys() {
    // Load API keys from localStorage (in production, these would be from secure backend)
    document.getElementById('founder-accuweather-key').value = localStorage.getItem('agricare_api_accuweather') || '';
    document.getElementById('founder-gemini-key').value = localStorage.getItem('agricare_api_gemini') || '';
    document.getElementById('founder-hf-key').value = localStorage.getItem('agricare_api_hf') || '';
}

function saveApiKeys() {
    const accuweatherKey = document.getElementById('founder-accuweather-key').value;
    const geminiKey = document.getElementById('founder-gemini-key').value;
    const hfKey = document.getElementById('founder-hf-key').value;

    localStorage.setItem('agricare_api_accuweather', accuweatherKey);
    localStorage.setItem('agricare_api_gemini', geminiKey);
    localStorage.setItem('agricare_api_hf', hfKey);

    showNotification('API keys saved successfully', 'success');
}

function loadUiCommitHistory() {
    const commits = getCommits().filter(c => c.author === 'UI Developer').slice(0, 10);
    const historyList = document.getElementById('ui-commit-history');
    
    historyList.innerHTML = commits.map(commit => `
        <li class="flex justify-between items-center">
            <span>${commit.timestamp}</span>
            <span class="text-green-400">${commit.author}</span>
        </li>
    `).join('');
}

function loadFounderCommitHistory() {
    const commits = getCommits().slice(0, 20);
    const historyList = document.getElementById('founder-commit-history');
    
    historyList.innerHTML = commits.map(commit => `
        <li class="flex justify-between items-center">
            <span>${commit.timestamp}</span>
            <span class="text-blue-400">${commit.author}</span>
        </li>
    `).join('');
}

function updateDeveloperStatus() {
    // Simulate developer status
    const now = Date.now();
    const lastActivity = now - Math.random() * 3600000; // Random activity in last hour
    
    document.getElementById('ui-dev-status').textContent = 
        Math.random() > 0.5 ? 'UI Developer: Active' : 'UI Developer: Inactive';
    document.getElementById('admin-dev-status').textContent = 
        Math.random() > 0.5 ? 'Admin: Active' : 'Admin: Inactive';
}

// Commit system functions
function getCommits() {
    return JSON.parse(localStorage.getItem('agricare_commits') || '[]');
}

function saveCommit(author, code) {
    const commits = getCommits();
    commits.unshift({
        id: Date.now().toString(),
        author: author,
        timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
        code: code.substring(0, 1000) // Store abbreviated version
    });
    
    // Keep only last 50 commits
    commits.splice(50);
    
    localStorage.setItem('agricare_commits', JSON.stringify(commits));
}

function commitUiCode() {
    if (uiCodeEditor) {
        const code = uiCodeEditor.getValue();
        if (code.trim()) {
            saveCommit('UI Developer', code);
            loadUiCommitHistory();
            showNotification('UI code committed successfully', 'success');
        } else {
            showNotification('No code to commit', 'error');
        }
    }
}

function rollbackUiCode() {
    const commits = getCommits().filter(c => c.author === 'UI Developer');
    if (commits.length > 1) {
        const previousCommit = commits[1];
        if (uiCodeEditor) {
            uiCodeEditor.setValue(previousCommit.code);
            showNotification('Rolled back to previous version', 'success');
        }
    } else {
        showNotification('No previous version available', 'error');
    }
}

function previewUiCode() {
    if (uiCodeEditor) {
        const code = uiCodeEditor.getValue();
        const previewWindow = window.open('', '_blank');
        previewWindow.document.write(code);
        previewWindow.document.close();
    }
}

// API Status checking
async function checkAllApiStatus() {
    const statusElements = {
        accuweather: document.getElementById('accuweather-status'),
        gemini: document.getElementById('gemini-status'),
        hf: document.getElementById('hf-status')
    };

    // Reset status
    Object.values(statusElements).forEach(el => {
        el.textContent = 'Checking...';
        el.className = 'font-bold text-yellow-500';
    });

    // Check Weather API
    try {
        const response = await fetch(`${API_CONFIG.BASE_URL}/weather/health`);
        if (response.ok) {
            statusElements.accuweather.textContent = 'Active';
            statusElements.accuweather.className = 'font-bold text-green-500';
        } else {
            throw new Error('API not responding');
        }
    } catch (error) {
        statusElements.accuweather.textContent = 'Error';
        statusElements.accuweather.className = 'font-bold text-red-500';
    }

    // Check Disease Detection API
    try {
        const response = await fetch(`${API_CONFIG.BASE_URL}/disease/health`);
        if (response.ok) {
            statusElements.gemini.textContent = 'Active';
            statusElements.gemini.className = 'font-bold text-green-500';
        } else {
            throw new Error('API not responding');
        }
    } catch (error) {
        statusElements.gemini.textContent = 'Error';
        statusElements.gemini.className = 'font-bold text-red-500';
    }

    // Check Yield Prediction API
    try {
        const response = await fetch(`${API_CONFIG.BASE_URL}/yield/health`);
        if (response.ok) {
            statusElements.hf.textContent = 'Active';
            statusElements.hf.className = 'font-bold text-green-500';
        } else {
            throw new Error('API not responding');
        }
    } catch (error) {
        statusElements.hf.textContent = 'Error';
        statusElements.hf.className = 'font-bold text-red-500';
    }
}

// Initialize developer event listeners
function initializeDeveloperEventListeners() {
    // UI Developer Panel
    const commitUiBtn = document.getElementById('commit-ui-code-btn');
    if (commitUiBtn) {
        commitUiBtn.addEventListener('click', commitUiCode);
    }

    const rollbackUiBtn = document.getElementById('rollback-ui-code-btn');
    if (rollbackUiBtn) {
        rollbackUiBtn.addEventListener('click', rollbackUiCode);
    }

    const previewUiBtn = document.getElementById('preview-ui-code-btn');
    if (previewUiBtn) {
        previewUiBtn.addEventListener('click', previewUiCode);
    }

    // Founder Panel
    const saveApiKeysBtn = document.getElementById('save-api-keys-btn');
    if (saveApiKeysBtn) {
        saveApiKeysBtn.addEventListener('click', saveApiKeys);
    }

    // Admin Panel
    const refreshApiStatusBtn = document.getElementById('refresh-api-status');
    if (refreshApiStatusBtn) {
        refreshApiStatusBtn.addEventListener('click', checkAllApiStatus);
    }
}