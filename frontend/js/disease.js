// Disease Detection Module - Frontend

// File handling functions
function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = () => resolve(reader.result.split(',')[1]);
        reader.onerror = error => reject(error);
    });
}

function handleFile(file) {
    if (file) {
        selectedDiseaseFile = file;
        const reader = new FileReader();
        reader.onload = e => {
            const imagePreview = document.getElementById('image-preview');
            const uploadPlaceholder = document.getElementById('upload-placeholder');
            const detectDiseaseBtn = document.getElementById('detect-disease-btn');
            
            imagePreview.src = e.target.result;
            imagePreview.classList.remove('hidden');
            uploadPlaceholder.classList.add('hidden');
            detectDiseaseBtn.disabled = false;
        };
        reader.readAsDataURL(file);
    }
}

async function detectDiseaseWithAPI(file, language = 'en-US') {
    const formData = new FormData();
    formData.append('image', file);
    formData.append('language', language);
    formData.append('useGemini', 'true');

    const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.DISEASE.DETECT}`, {
        method: 'POST',
        body: formData
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ message: 'Network error' }));
        throw new Error(error.message || `HTTP ${response.status}`);
    }

    return await response.json();
}

async function performDiseaseDetection() {
    const detectDiseaseBtn = document.getElementById('detect-disease-btn');
    const diseaseResultDiv = document.getElementById('disease-result');
    
    if (!selectedDiseaseFile) return;

    detectDiseaseBtn.textContent = 'Analyzing...';
    detectDiseaseBtn.disabled = true;
    diseaseResultDiv.classList.add('hidden');
    showLoader();

    try {
        const language = localStorage.getItem('agricare_language') || 'en-US';
        const result = await detectDiseaseWithAPI(selectedDiseaseFile, language);

        if (result.success) {
            displayDiseaseResult(result.data);
        } else {
            throw new Error('Disease detection failed');
        }
    } catch (error) {
        console.error('Disease detection error:', error);
        showNotification('Disease analysis failed. Please try again.', 'error');
    } finally {
        detectDiseaseBtn.textContent = 'Analyze Crop Health';
        detectDiseaseBtn.disabled = false;
        hideLoader();
    }
}

function displayDiseaseResult(data) {
    const diseaseResultDiv = document.getElementById('disease-result');
    const diseaseNameEl = document.getElementById('disease-name');
    const diseaseRecommendationEl = document.getElementById('disease-recommendation');
    const analysisTimeEl = document.getElementById('disease-analysis-time');

    diseaseNameEl.textContent = data.disease;
    diseaseRecommendationEl.textContent = data.recommendation;
    analysisTimeEl.textContent = new Date(data.analysisTime).toLocaleString();

    diseaseResultDiv.classList.remove('hidden');

    // Store result for TTS
    window.lastDiseaseResult = {
        disease: data.disease,
        recommendation: data.recommendation,
        language: data.language
    };
}

// Text-to-Speech for disease results
async function playDiseaseResultTTS() {
    if (!window.lastDiseaseResult) {
        showNotification('No disease result to read', 'error');
        return;
    }

    const language = document.getElementById('disease-tts-lang').value;
    const text = `Disease detected: ${window.lastDiseaseResult.disease}. Recommendation: ${window.lastDiseaseResult.recommendation}`;
    
    try {
        // Use Web Speech API
        if ('speechSynthesis' in window) {
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = language;
            speechSynthesis.speak(utterance);
        } else {
            showNotification('Text-to-speech not supported', 'error');
        }
    } catch (error) {
        console.error('TTS error:', error);
        showNotification('Could not play audio', 'error');
    }
}

// Webcam functionality
let webcamStream = null;

async function startWebcam() {
    const webcamModal = document.getElementById('webcam-modal');
    const webcamVideo = document.getElementById('webcam-video');
    
    try {
        webcamStream = await navigator.mediaDevices.getUserMedia({ 
            video: { width: 640, height: 480 } 
        });
        webcamVideo.srcObject = webcamStream;
        webcamModal.classList.remove('hidden');
        webcamModal.style.display = 'flex';
    } catch (error) {
        console.error('Webcam error:', error);
        showNotification('Could not access camera', 'error');
    }
}

function stopWebcam() {
    if (webcamStream) {
        webcamStream.getTracks().forEach(track => track.stop());
        webcamStream = null;
    }
    const webcamModal = document.getElementById('webcam-modal');
    webcamModal.classList.add('hidden');
    webcamModal.style.display = 'none';
}

function captureWebcamImage() {
    const webcamVideo = document.getElementById('webcam-video');
    const webcamCanvas = document.getElementById('webcam-canvas');
    const ctx = webcamCanvas.getContext('2d');
    
    webcamCanvas.width = webcamVideo.videoWidth;
    webcamCanvas.height = webcamVideo.videoHeight;
    
    ctx.drawImage(webcamVideo, 0, 0);
    
    webcamCanvas.toBlob(blob => {
        const file = new File([blob], 'webcam-capture.jpg', { type: 'image/jpeg' });
        handleFile(file);
        stopWebcam();
    }, 'image/jpeg', 0.8);
}

// Initialize disease detection event listeners
function initializeDiseaseEventListeners() {
    // Upload button
    document.getElementById('upload-btn').addEventListener('click', () => {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = 'image/*';
        input.onchange = e => handleFile(e.target.files[0]);
        input.click();
    });

    // Camera button
    document.getElementById('camera-btn').addEventListener('click', startWebcam);

    // Detect disease button
    document.getElementById('detect-disease-btn').addEventListener('click', performDiseaseDetection);

    // TTS button
    document.getElementById('play-disease-tts').addEventListener('click', playDiseaseResultTTS);

    // Webcam controls
    document.getElementById('capture-btn').addEventListener('click', captureWebcamImage);
    document.getElementById('cancel-webcam-btn').addEventListener('click', stopWebcam);
}