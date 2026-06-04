// Weather Module - Frontend

// Weather functions for frontend
async function loadWeatherByCoordinates(lat, lon) {
    try {
        console.log(`🌤️ Loading weather for coordinates: ${lat}, ${lon}`);
        showLoader();
        const response = await apiRequest(`${API_CONFIG.ENDPOINTS.WEATHER.CURRENT}?lat=${lat}&lon=${lon}`);
        
        console.log('🌤️ Weather API response:', response);
        
        if (response.success) {
            displayWeatherData(response.data);
        } else {
            throw new Error(response.message || 'Failed to load weather data');
        }
    } catch (error) {
        console.error('❌ Weather error:', error);
        showNotification('Failed to load weather data', 'error');
        
        // Fallback to city-based weather
        console.log('🧪 Falling back to city-based weather');
        await loadWeatherByCity('New Delhi');
    } finally {
        hideLoader();
    }
}

async function loadWeatherByCity(city) {
    try {
        console.log(`🌤️ Loading weather for city: ${city}`);
        showLoader();
        const response = await apiRequest(`${API_CONFIG.ENDPOINTS.WEATHER.CURRENT}?location=${encodeURIComponent(city)}`);
        
        console.log('🌤️ Weather API response:', response);
        
        if (response.success) {
            displayWeatherData(response.data);
        } else {
            throw new Error(response.message || 'Failed to load weather data');
        }
    } catch (error) {
        console.error('❌ Weather error:', error);
        showNotification('City not found or weather service unavailable', 'error');
        
        // Show mock data for testing
        console.log('🧪 Showing mock weather data for testing');
        displayMockWeatherData(city);
    } finally {
        hideLoader();
    }
}

// Mock weather data for testing when API fails
function displayMockWeatherData(city) {
    const mockData = {
        location: {
            name: city || 'Test City',
            country: 'Test Country'
        },
        current: {
            temperature: 25,
            icon: 'fa-sun',
            description: 'Sunny',
            feelsLike: 27,
            humidity: 60,
            windSpeed: 10,
            pressure: 1013
        },
        sun: {
            sunrise: '06:30',
            sunset: '18:45'
        },
        hourly: [
            { time: '12:00', icon: 'fa-sun', temperature: 25 },
            { time: '13:00', icon: 'fa-cloud', temperature: 24 },
            { time: '14:00', icon: 'fa-cloud', temperature: 23 }
        ],
        daily: [
            { date: 'Today', icon: 'fa-sun', minTemp: 20, maxTemp: 28 },
            { date: 'Tomorrow', icon: 'fa-cloud', minTemp: 18, maxTemp: 26 },
            { date: 'Wed', icon: 'fa-cloud-rain', minTemp: 16, maxTemp: 22 }
        ]
    };
    
    displayWeatherData(mockData);
}

function displayWeatherData(data) {
    console.log('🌤️ Displaying weather data:', data);
    
    // Helper function to safely update element content
    const safeUpdate = (id, content) => {
        const element = document.getElementById(id);
        if (element) {
            if (typeof content === 'string') {
                element.textContent = content;
            } else {
                element.className = content;
            }
        } else {
            console.warn(`⚠️ Element not found: ${id}`);
        }
    };

    // Update current weather with safe element access
    safeUpdate('weather-location', `${data.location.name}, ${data.location.country}`);
    safeUpdate('weather-temp', `${data.current.temperature}°`);
    safeUpdate('weather-icon', `fas ${data.current.icon} text-5xl`);
    safeUpdate('weather-description', data.current.description);
    safeUpdate('weather-feels-like', `${data.current.feelsLike}°`);
    safeUpdate('weather-humidity', `${data.current.humidity}%`);
    safeUpdate('weather-wind', `${data.current.windSpeed} km/h`);
    safeUpdate('weather-pressure', data.current.pressure ? `${data.current.pressure} hPa` : '--');
    safeUpdate('weather-sunrise', data.sun.sunrise || '--:--');
    safeUpdate('weather-sunset', data.sun.sunset || '--:--');

    // Update hourly forecast
    const hourlyContainer = document.getElementById('hourly-forecast');
    if (hourlyContainer) {
        hourlyContainer.innerHTML = '';
        data.hourly.forEach(hour => {
            hourlyContainer.innerHTML += `
                <div class="weather-hourly-card flex-shrink-0 text-center p-3 rounded-lg bg-gray-50 space-y-1">
                    <p class="text-sm">${hour.time}</p>
                    <i class="fas ${hour.icon} text-2xl"></i>
                    <p class="font-bold">${hour.temperature}°C</p>
                </div>
            `;
        });
    }

    // Update daily forecast
    const dailyContainer = document.getElementById('daily-forecast');
    if (dailyContainer) {
        dailyContainer.innerHTML = '';
        data.daily.forEach(day => {
            dailyContainer.innerHTML += `
                <div class="flex justify-between items-center">
                    <span class="w-1/3 font-medium">${day.date}</span>
                    <i class="fas ${day.icon} text-xl"></i>
                    <span class="w-1/3 text-right">${day.minTemp}° / <strong>${day.maxTemp}°</strong></span>
                </div>
            `;
        });
    }

    // Store current weather summary for chatbot context
    window.currentWeatherSummary = `${data.location.name} - Current temperature: ${data.current.temperature}°C, ${data.current.description}. Sunrise: ${data.sun.sunrise}, Sunset: ${data.sun.sunset}.`;
    
    console.log('✅ Weather data displayed successfully');
}

function getLocationAndFetchWeather() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            async (pos) => {
                await loadWeatherByCoordinates(pos.coords.latitude, pos.coords.longitude);
            },
            async () => {
                // Fallback to default city
                await loadWeatherByCity('New Delhi');
            }
        );
    } else {
        loadWeatherByCity('New Delhi');
    }
}

async function fetchCitySuggestions(query) {
    const citySuggestions = document.getElementById('city-suggestions');
    
    if (!query) {
        citySuggestions.classList.add('hidden');
        citySuggestions.innerHTML = '';
        return;
    }

    try {
        const response = await apiRequest(`${API_CONFIG.ENDPOINTS.WEATHER.AUTOCOMPLETE}?q=${encodeURIComponent(query)}`);
        
        citySuggestions.innerHTML = '';
        
        if (response.success && response.suggestions.length > 0) {
            response.suggestions.forEach(item => {
                const li = document.createElement('li');
                li.className = 'px-4 py-2 hover:bg-green-100 cursor-pointer';
                li.textContent = `${item.name}, ${item.country}`;
                li.onclick = () => {
                    document.getElementById('city-input').value = item.name;
                    citySuggestions.classList.add('hidden');
                    loadWeatherByCity(item.name);
                };
                citySuggestions.appendChild(li);
            });
            citySuggestions.classList.remove('hidden');
        } else {
            citySuggestions.classList.add('hidden');
        }
    } catch (err) {
        console.error('Autocomplete error:', err);
        citySuggestions.classList.add('hidden');
    }
}

// Initialize weather event listeners
function initializeWeatherEventListeners() {
    console.log('🌤️ Initializing weather event listeners...');
    
    // Immediately show test content to verify the view is working
    console.log('🧪 Loading test weather content immediately...');
    displayMockWeatherData('Test City');
    
    // Check if required elements exist
    const weatherForm = document.getElementById('weather-search-form');
    const getLocationBtn = document.getElementById('get-location-btn');
    const cityInput = document.getElementById('city-input');
    
    if (!weatherForm || !getLocationBtn || !cityInput) {
        console.error('❌ Weather elements not found:', {
            weatherForm: !!weatherForm,
            getLocationBtn: !!getLocationBtn,
            cityInput: !!cityInput
        });
        return;
    }

    console.log('✅ All weather elements found');

    // Weather search form
    weatherForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const city = cityInput.value.trim();
        if (city) {
            await loadWeatherByCity(city);
        }
    });

    // Get location button
    getLocationBtn.addEventListener('click', getLocationAndFetchWeather);

    // City input autocomplete
    let suggestionTimer = null;
    
    cityInput.addEventListener('input', (e) => {
        const query = e.target.value.trim();
        if (suggestionTimer) clearTimeout(suggestionTimer);
        suggestionTimer = setTimeout(() => fetchCitySuggestions(query), 250);
    });

    // Hide suggestions when clicking outside
    document.addEventListener('click', (e) => {
        const citySuggestions = document.getElementById('city-suggestions');
        if (citySuggestions && !citySuggestions.contains(e.target) && e.target !== cityInput) {
            citySuggestions.classList.add('hidden');
        }
    });

    // Hide suggestions on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const citySuggestions = document.getElementById('city-suggestions');
            if (citySuggestions) {
                citySuggestions.classList.add('hidden');
            }
        }
    });

    // Try to load real weather data after a delay
    console.log('🌤️ Weather event listeners initialized. Attempting to load real weather data...');
    setTimeout(() => {
        getLocationAndFetchWeather();
    }, 2000); // Delay to show test data first
}