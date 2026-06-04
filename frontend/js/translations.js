// English-only translations for AgriCare

const TRANSLATIONS = {
    'en-US': {
        'app_title': 'AgriCare',
        'select_language': 'Select Language',
        'sign_out': 'Sign out',
        'back_to_menu': 'Back to Menu',

        // Authentication
        'welcome_title': 'Welcome to AgriCare',
        'welcome_subtitle': 'Your AI Farming Assistant',
        'create_account_title': 'Create Account',
        'create_account_subtitle': 'Get started with AgriCare',
        'username_label': 'Username or Email',
        'password_label': 'Password',
        'email_label': 'Email Address',
        'create_password_label': 'Create Password',
        'sign_in_btn': 'Sign In',
        'register_btn': 'Register',
        'no_account': 'Don\'t have an account?',
        'register_here': 'Register here',
        'have_account': 'Already have an account?',
        'login_here': 'Login here',

        // Main Menu
        'main_menu_title': 'What would you like to do today?',
        'menu_weather': 'Local Weather',
        'menu_disease': 'Crop Health Check',
        'menu_yield': 'Yield Prediction',
        'menu_chatbot': 'AgriBot Assistant',

        // Weather View
        'weather_title': 'Weather Forecast',
        'weather_search_placeholder': 'Enter city name...',
        'current_weather': 'Current Weather',
        'hourly_forecast': 'Hourly Forecast',
        'daily_forecast': '7-Day Forecast',
        'feels_like': 'Feels like',
        'humidity': 'Humidity',
        'wind': 'Wind',
        'pressure': 'Pressure',
        'sunrise': 'Sunrise',
        'sunset': 'Sunset',
        'use_location': 'Use my location',

        // Disease Detection
        'disease_title': 'Crop Health Check',
        'disease_description': 'Upload a photo of a crop leaf to get a diagnosis.',
        'upload_image': 'Upload Image',
        'take_photo': 'Take Photo',
        'analyze_crop': 'Analyze Crop Health',
        'diagnosis': 'Diagnosis',
        'recommendations': 'Recommendations',

        // Yield Prediction
        'yield_title': 'Crop Yield Prediction',
        'crop_type_label': 'Crop Type',
        'area_label': 'Area (in acres)',
        'predict_yield': 'Predict Yield',
        'predicted_yield': 'Predicted Yield',
        'crop_rice': 'Rice',
        'crop_wheat': 'Wheat',
        'crop_maize': 'Maize',

        // Chatbot
        'chatbot_title': 'AgriBot Assistant',
        'chatbot_placeholder': 'Ask AgriBot about farming...',
        'voice_input': 'Voice input',

        // Notifications
        'login_success': 'Login successful!',
        'registration_success': 'Registration successful! Please login.',
        'logout_success': 'Logged out successfully',
        'fill_all_fields': 'Please fill in all fields',
        'network_error': 'Network error. Please try again.',
        'language_changed': 'Language changed successfully!',

        // General
        'loading': 'Loading...',
        'error': 'Error',
        'success': 'Success',
        'cancel': 'Cancel',
        'close': 'Close',
        'save': 'Save',
        'submit': 'Submit'
    }
};

// Export for modules that import translations (if any)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TRANSLATIONS;
}