/**
 * AgriCare Dynamic Translation System
 * Replaces i18next with API-based translation using the dynamic model
 */

class TranslationManager {
    constructor() {
        this.currentLanguage = 'en';
        this.supportedLanguages = [];
        this.translations = {};
        this.apiEndpoint = '/api/translate';
        this.languagesEndpoint = '/api/translate/languages';
        this.isModelAvailable = false;
    }

    async init() {
        try {
            console.log('🌐 Initializing AgriCare Translation System...');
            
            // Get supported languages from the API
            await this.loadSupportedLanguages();
            
            // Get saved language preference
            const savedLang = localStorage.getItem('agricare_language') || 'en';
            if (this.supportedLanguages.includes(savedLang)) {
                this.currentLanguage = savedLang;
            }
            
            // Apply translations to current page
            await this.applyTranslations();
            
            console.log('✅ Translation system initialized successfully');
            console.log(`📍 Current language: ${this.currentLanguage}`);
            console.log(`🔧 Model available: ${this.isModelAvailable}`);
            
        } catch (error) {
            console.error('❌ Translation system initialization failed:', error);
        }
    }

    async loadSupportedLanguages() {
        try {
            const response = await fetch(this.languagesEndpoint);
            const data = await response.json();
            
            if (data.success) {
                this.supportedLanguages = data.supported_languages;
                this.isModelAvailable = data.model_available;
                console.log('📋 Supported languages:', this.supportedLanguages);
            }
        } catch (error) {
            console.error('❌ Failed to load supported languages:', error);
            // Fallback to basic languages
            this.supportedLanguages = ['en', 'ta', 'hi', 'te', 'bn'];
        }
    }

    async translateText(text, targetLang = null) {
        if (!text || !text.trim()) return text;
        
        targetLang = targetLang || this.currentLanguage;
        
        // If target is English or same as current, no translation needed
        if (targetLang === 'en' || targetLang === this.currentLanguage) {
            return text;
        }

        // Check cache first
        const cacheKey = `${text}_${targetLang}`;
        if (this.translations[cacheKey]) {
            return this.translations[cacheKey];
        }

        try {
            const response = await fetch(this.apiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: text,
                    source_lang: 'en', // Assuming source is English
                    target_lang: targetLang
                })
            });

            const data = await response.json();
            
            if (data.success) {
                // Cache the translation
                this.translations[cacheKey] = data.translated_text;
                return data.translated_text;
            } else {
                console.warn('⚠️ Translation failed:', data.error);
                return text;
            }
        } catch (error) {
            console.error('❌ Translation API error:', error);
            return text;
        }
    }

    async applyTranslations() {
        if (this.currentLanguage === 'en') {
            console.log('📍 Current language is English, skipping translation');
            return;
        }

        console.log(`🔄 Applying translations for language: ${this.currentLanguage}`);
        
        // Find all elements with data-i18n attributes
        const elements = document.querySelectorAll('[data-i18n]');
        const translations = [];
        
        // Collect all texts to translate
        elements.forEach(element => {
            const key = element.getAttribute('data-i18n');
            const originalText = element.textContent.trim();
            if (originalText) {
                translations.push({
                    element: element,
                    key: key,
                    text: originalText
                });
            }
        });

        // Translate each text
        for (const item of translations) {
            try {
                const translatedText = await this.translateText(item.text, this.currentLanguage);
                if (translatedText !== item.text) {
                    item.element.textContent = translatedText;
                    console.log(`📝 Translated "${item.text}" → "${translatedText}"`);
                }
            } catch (error) {
                console.error(`❌ Failed to translate "${item.text}":`, error);
            }
        }

        console.log(`✅ Applied ${translations.length} translations`);
    }

    async setLanguage(languageCode) {
        if (!this.supportedLanguages.includes(languageCode)) {
            console.warn(`⚠️ Language ${languageCode} not supported`);
            return false;
        }

        console.log(`🔄 Changing language from ${this.currentLanguage} to ${languageCode}`);
        this.currentLanguage = languageCode;
        
        // Save preference
        localStorage.setItem('agricare_language', languageCode);
        
        // Apply translations
        await this.applyTranslations();
        
        // Update language selector if exists
        const languageSelect = document.getElementById('site-language-select');
        if (languageSelect) {
            languageSelect.value = languageCode;
        }

        console.log(`✅ Language changed to ${languageCode}`);
        return true;
    }

    getCurrentLanguage() {
        return this.currentLanguage;
    }

    getSupportedLanguages() {
        return this.supportedLanguages;
    }

    isModelLoaded() {
        return this.isModelAvailable;
    }

    // Helper method for translating dynamic content
    async translateDynamicContent(text, targetLang = null) {
        return await this.translateText(text, targetLang);
    }
}

// Initialize global translation manager
window.TranslationManager = TranslationManager;

// Auto-initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', async function() {
    if (!window.translationManager) {
        window.translationManager = new TranslationManager();
        await window.translationManager.init();
        
        // Setup language selector if exists
        const languageSelect = document.getElementById('site-language-select');
        if (languageSelect) {
            // Populate language options
            const supportedLangs = window.translationManager.getSupportedLanguages();
            const languageNames = {
                'en': 'English',
                'ta': 'தமிழ் (Tamil)',
                'hi': 'हिंदी (Hindi)', 
                'te': 'తెలుగు (Telugu)',
                'bn': 'বাংলা (Bengali)',
                'mr': 'मराठी (Marathi)',
                'gu': 'ગુજરાતી (Gujarati)',
                'kn': 'ಕನ್ನಡ (Kannada)',
                'ml': 'മലയാളം (Malayalam)',
                'pa': 'ਪੰਜਾਬੀ (Punjabi)',
                'ur': 'اردو (Urdu)'
            };

            languageSelect.innerHTML = '';
            supportedLangs.forEach(langCode => {
                const option = document.createElement('option');
                option.value = langCode;
                option.textContent = languageNames[langCode] || langCode.toUpperCase();
                languageSelect.appendChild(option);
            });

            // Set current selection
            languageSelect.value = window.translationManager.getCurrentLanguage();
            
            // Handle language change
            languageSelect.addEventListener('change', async function() {
                await window.translationManager.setLanguage(this.value);
            });
        }
    }
});

console.log('📦 AgriCare Translation System loaded');