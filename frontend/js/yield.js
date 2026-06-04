// Yield Prediction Module - Frontend

async function predictYield() {
    const cropType = document.getElementById('crop-type').value;
    const area = parseFloat(document.getElementById('area').value);
    const language = localStorage.getItem('agricare_language') || 'en-US';
    const predictBtn = document.getElementById('predict-yield-btn');
    const resultDiv = document.getElementById('yield-result');

    if (!cropType || !area || area <= 0) {
        showNotification('Please select a crop type and enter valid area', 'error');
        return;
    }

    predictBtn.textContent = 'Predicting...';
    predictBtn.disabled = true;
    resultDiv.classList.add('hidden');
    showLoader();

    try {
        const response = await apiRequest(API_CONFIG.ENDPOINTS.YIELD.PREDICT, {
            method: 'POST',
            body: JSON.stringify({
                cropType,
                area,
                language
            })
        });

        if (response.success) {
            displayYieldResult(response.data);
        } else {
            throw new Error('Yield prediction failed');
        }
    } catch (error) {
        console.error('Yield prediction error:', error);
        showNotification('Yield prediction failed. Please try again.', 'error');
    } finally {
        predictBtn.textContent = 'Predict Yield';
        predictBtn.disabled = false;
        hideLoader();
    }
}

function displayYieldResult(data) {
    const resultDiv = document.getElementById('yield-result');
    const yieldValue = document.getElementById('yield-value');
    
    yieldValue.textContent = data.formatted.total;
    resultDiv.classList.remove('hidden');

    // Show additional information if available
    if (data.recommendations && data.recommendations.length > 0) {
        showNotification(`Confidence: ${data.formatted.confidence}`, 'success');
    }

    // Store result for potential sharing or further use
    window.lastYieldPrediction = data;
}

// Get supported crops information
async function loadCropsInfo() {
    try {
        const response = await apiRequest(`${API_CONFIG.ENDPOINTS.YIELD.PREDICT.replace('/predict', '/crops')}`);
        
        if (response.supportedCrops) {
            // Could be used to dynamically populate crop options
            console.log('Supported crops:', response.supportedCrops);
        }
    } catch (error) {
        console.warn('Could not load crops info:', error);
    }
}

// Initialize yield prediction event listeners
function initializeYieldEventListeners() {
    // Predict yield button
    document.getElementById('predict-yield-btn').addEventListener('click', predictYield);

    // Area input validation
    document.getElementById('area').addEventListener('input', (e) => {
        const value = parseFloat(e.target.value);
        if (value <= 0) {
            e.target.setCustomValidity('Area must be greater than 0');
        } else if (value > 10000) {
            e.target.setCustomValidity('Area cannot exceed 10,000 acres');
        } else {
            e.target.setCustomValidity('');
        }
    });

    // Load crops information on initialization
    loadCropsInfo();
}