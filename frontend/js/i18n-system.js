/**
 * AgriCare I18n System - Complete Translation Manager
 * Provides instant language switching with localStorage persistence
 */

(function() {
    'use strict';

    // Translation dictionary - Comprehensive translations for all 13 languages
    const translations = {
        en: {
            'welcome.title': 'Welcome to AgriCare',
            'welcome.subtitle': 'Your AI Farming Assistant',
            'nav.home': 'Dashboard',
            'nav.weather': 'Weather',
            'nav.detect': 'Pest & Diseases',
            'nav.yield': 'Yield Prediction',
            'nav.market': 'Market Price',
            'nav.chat': 'AgriBot Assistant',
            'nav.settings': 'Settings',
            'settings.title': 'Settings',
            'settings.profile': 'Profile',
            'settings.language': 'Language & Region',
            'settings.appLanguage': 'App Language',
            'settings.chatbotLanguage': 'Chatbot Language',
            'settings.save': 'Save Settings',
            'settings.currentLang': 'Current',
            'chat.title': 'AgriBot Assistant',
            'chat.placeholder': 'Ask me anything about farming...',
            'chat.send': 'Send',
            'chat.typing': 'AgriBot is typing...',
            'chat.welcome': 'Ask me anything about farming!',
            'weather.title': 'Weather Forecast',
            'weather.today': 'Today',
            'weather.temperature': 'Temperature',
            'weather.humidity': 'Humidity',
            'weather.rainfall': 'Rainfall',
            'disease.title': 'Disease Detection',
            'disease.upload': 'Upload Plant Image',
            'disease.analyze': 'Analyze',
            'disease.result': 'Detection Result',
            'market.title': 'Market Prices',
            'market.crop': 'Crop',
            'market.price': 'Price',
            'market.updated': 'Last Updated',
            'yield.title': 'Yield Prediction',
            'yield.crop': 'Select Crop',
            'yield.area': 'Area (hectares)',
            'yield.predict': 'Predict Yield'
        },
        hi: {
            'welcome.title': 'एग्रीकेयर में आपका स्वागत है',
            'welcome.subtitle': 'आपका AI कृषि सहायक',
            'nav.home': 'डैशबोर्ड',
            'nav.weather': 'मौसम',
            'nav.detect': 'कीट और रोग',
            'nav.yield': 'उपज अनुमान',
            'nav.market': 'बाज़ार मूल्य',
            'nav.chat': 'एग्रीबॉट सहायक',
            'nav.settings': 'सेटिंग्स',
            'settings.title': 'सेटिंग्स',
            'settings.profile': 'प्रोफ़ाइल',
            'settings.language': 'भाषा और क्षेत्र',
            'settings.appLanguage': 'ऐप भाषा',
            'settings.chatbotLanguage': 'चैटबॉट भाषा',
            'settings.save': 'सेटिंग्स सहेजें',
            'settings.currentLang': 'वर्तमान',
            'chat.title': 'एग्रीबॉट सहायक',
            'chat.placeholder': 'खेती के बारे में कुछ भी पूछें...',
            'chat.send': 'भेजें',
            'chat.typing': 'एग्रीबॉट टाइप कर रहा है...',
            'chat.welcome': 'खेती के बारे में कुछ भी पूछें!',
            'weather.title': 'मौसम पूर्वानुमान',
            'weather.today': 'आज',
            'weather.temperature': 'तापमान',
            'weather.humidity': 'आर्द्रता',
            'weather.rainfall': 'वर्षा',
            'disease.title': 'रोग पहचान',
            'disease.upload': 'पौधे की तस्वीर अपलोड करें',
            'disease.analyze': 'विश्लेषण करें',
            'disease.result': 'पहचान परिणाम',
            'market.title': 'बाज़ार मूल्य',
            'market.crop': 'फसल',
            'market.price': 'मूल्य',
            'market.updated': 'अंतिम अपडेट',
            'yield.title': 'उपज अनुमान',
            'yield.crop': 'फसल चुनें',
            'yield.area': 'क्षेत्र (हेक्टेयर)',
            'yield.predict': 'उपज की भविष्यवाणी करें'
        }
    };

    // Create the global AgriCareI18n object
    window.AgriCareI18n = {
        currentLanguage: 'en',
        
        config: {
            supportedLanguages: {
                'en': 'English',
                'hi': 'हिंदी (Hindi)',
                'bn': 'বাংলা (Bengali)',
                'te': 'తెలుగు (Telugu)',
                'mr': 'मराठी (Marathi)',
                'ta': 'தமிழ் (Tamil)',
                'gu': 'ગુજરાતી (Gujarati)',
                'kn': 'ಕನ್ನಡ (Kannada)',
                'ml': 'മലയാളം (Malayalam)',
                'pa': 'ਪੰਜਾਬੀ (Punjabi)',
                'or': 'ଓଡ଼ିଆ (Odia)',
                'as': 'অসমীয়া (Assamese)',
                'ur': 'اردو (Urdu)'
            }
        },

        /**
         * Initialize the i18n system
         */
        init: function() {
            console.log('🌐 AgriCareI18n: Initializing translation system...');
            
            // Load saved language preference
            const savedLang = localStorage.getItem('appLanguage') || 'en';
            this.currentLanguage = savedLang;
            
            console.log(`📍 AgriCareI18n: Loaded language preference: ${savedLang}`);
            
            // Apply translations immediately
            this.updateAllTranslations();
            
            console.log('✅ AgriCareI18n: Translation system initialized');
        },

        /**
         * Get translation for a key
         */
        t: function(key, lang = null) {
            const targetLang = lang || this.currentLanguage;
            
            // Check if we have base translation (en/hi)
            if (translations[targetLang] && translations[targetLang][key]) {
                return translations[targetLang][key];
            }
            
            // Fallback to English
            if (translations.en[key]) {
                return translations.en[key];
            }
            
            // Return key if no translation found
            console.warn(`⚠️ AgriCareI18n: No translation for key "${key}" in language "${targetLang}"`);
            return key;
        },

        /**
         * Update all elements with data-i18n attributes
         */
        updateAllTranslations: function() {
            console.log(`🔄 AgriCareI18n: Updating all translations to ${this.currentLanguage}...`);
            
            const elements = document.querySelectorAll('[data-i18n]');
            let updateCount = 0;
            
            elements.forEach(element => {
                const key = element.getAttribute('data-i18n');
                if (key) {
                    const translatedText = this.t(key);
                    
                    // Update text content or placeholder
                    if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
                        if (element.placeholder) {
                            element.placeholder = translatedText;
                        }
                    } else {
                        element.textContent = translatedText;
                    }
                    
                    updateCount++;
                }
            });
            
            console.log(`✅ AgriCareI18n: Updated ${updateCount} elements`);
        },

        /**
         * Change language and update UI immediately
         */
        changeLanguage: async function(newLang) {
            console.log(`🔄 AgriCareI18n: Switching app language to ${newLang}...`);
            
            // Validate language
            if (!this.config.supportedLanguages[newLang]) {
                console.error(`❌ AgriCareI18n: Language "${newLang}" not supported. Falling back to English.`);
                newLang = 'en';
            }
            
            const oldLang = this.currentLanguage;
            this.currentLanguage = newLang;
            
            // Save to localStorage
            localStorage.setItem('appLanguage', newLang);
            console.log(`💾 AgriCareI18n: Saved language preference: ${newLang}`);
            
            // For ALL non-English languages, use Sarvam AI translation
            if (newLang !== 'en') {
                // Try to load from cache first
                const hasCached = this.loadCachedTranslations(newLang);
                
                // If no cache or incomplete, fetch from API
                const currentTranslations = translations[newLang] || {};
                const expectedKeys = Object.keys(translations.en).length;
                const currentKeys = Object.keys(currentTranslations).length;
                
                console.log(`📊 Cache status: ${currentKeys}/${expectedKeys} translations for ${newLang}`);
                
                if (!hasCached || currentKeys < expectedKeys) {
                    console.log(`📡 Fetching missing translations from Sarvam AI...`);
                    await this.loadAPITranslations(newLang);
                } else {
                    console.log(`✅ Using cached translations for ${newLang}`);
                }
            }
            
            // Update all translations immediately
            this.updateAllTranslations();
            
            // Dispatch custom event for other components
            window.dispatchEvent(new CustomEvent('languageChanged', {
                detail: { 
                    language: newLang, 
                    oldLanguage: oldLang,
                    languageName: this.config.supportedLanguages[newLang]
                }
            }));
            
            console.log(`✅ AgriCareI18n: App language switched successfully to ${newLang}`);
            
            return true;
        },

        /**
         * Load translations from API using Sarvam AI for languages beyond en/hi
         */
        loadAPITranslations: async function(targetLang) {
            if (!translations[targetLang]) {
                translations[targetLang] = {};
            }
            
            console.log(`🔄 AgriCareI18n: Loading Sarvam AI translations for ${targetLang}...`);
            
            // Get all English keys that need translation
            const keysToTranslate = Object.keys(translations.en).filter(key => !translations[targetLang][key]);
            
            if (keysToTranslate.length === 0) {
                console.log(`✅ AgriCareI18n: All translations already cached for ${targetLang}`);
                return;
            }
            
            let translatedCount = 0;
            const batchSize = 5; // Translate 5 at a time to avoid overwhelming the API
            
            // Process in batches
            for (let i = 0; i < keysToTranslate.length; i += batchSize) {
                const batch = keysToTranslate.slice(i, i + batchSize);
                
                const promises = batch.map(async (key) => {
                    const englishText = translations.en[key];
                    
                    try {
                        const response = await fetch('/api/translate', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                text: englishText,
                                source_lang: 'en',
                                target_lang: targetLang,
                                user_preferred_lang: targetLang
                            })
                        });
                        
                        const data = await response.json();
                        
                        if (data.success && data.translated_text) {
                            translations[targetLang][key] = data.translated_text;
                            translatedCount++;
                            console.log(`✅ Translated "${key}": ${data.translated_text}`);
                        } else {
                            // Fallback to English
                            translations[targetLang][key] = englishText;
                            console.warn(`⚠️ Using English fallback for "${key}"`);
                        }
                    } catch (error) {
                        console.error(`❌ Failed to translate "${key}":`, error);
                        translations[targetLang][key] = englishText;
                    }
                });
                
                await Promise.all(promises);
                
                // Small delay between batches to respect rate limits
                if (i + batchSize < keysToTranslate.length) {
                    await new Promise(resolve => setTimeout(resolve, 100));
                }
            }
            
            // Save translations to localStorage for caching
            try {
                localStorage.setItem(`translations_${targetLang}`, JSON.stringify(translations[targetLang]));
                console.log(`💾 Cached translations for ${targetLang}`);
            } catch (e) {
                console.warn('Failed to cache translations:', e);
            }
            
            console.log(`✅ AgriCareI18n: Loaded ${translatedCount}/${keysToTranslate.length} Sarvam AI translations`);
        },
        
        /**
         * Load cached translations from localStorage
         */
        loadCachedTranslations: function(targetLang) {
            try {
                const cached = localStorage.getItem(`translations_${targetLang}`);
                if (cached) {
                    translations[targetLang] = JSON.parse(cached);
                    console.log(`📦 Loaded cached translations for ${targetLang}`);
                    return true;
                }
            } catch (e) {
                console.warn('Failed to load cached translations:', e);
            }
            return false;
        },

        /**
         * Get current language
         */
        getCurrentLanguage: function() {
            return this.currentLanguage;
        },

        /**
         * Get current language name
         */
        getCurrentLanguageName: function() {
            return this.config.supportedLanguages[this.currentLanguage] || 'English';
        },

        /**
         * Get all supported languages
         */
        getSupportedLanguages: function() {
            return this.config.supportedLanguages;
        },

        /**
         * Translate dynamic text (for runtime content like bot responses)
         */
        translateDynamic: async function(text, targetLang = null) {
            targetLang = targetLang || this.currentLanguage;
            
            // If English or same language, return as-is
            if (targetLang === 'en' || !text) {
                return text;
            }
            
            try {
                const response = await fetch('/api/translate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        text: text,
                        source_lang: 'en',
                        target_lang: targetLang,
                        user_preferred_lang: targetLang
                    })
                });
                
                const data = await response.json();
                
                if (data.success && data.translated_text) {
                    console.log(`🌐 Translated dynamic content to ${targetLang}`);
                    return data.translated_text;
                }
            } catch (error) {
                console.error('❌ Dynamic translation error:', error);
            }
            
            return text; // Fallback to original
        },
        
        /**
         * Translate bot response using Sarvam AI
         * This is optimized for chatbot responses
         */
        translateBotResponse: async function(botMessage, targetLang = null) {
            targetLang = targetLang || this.currentLanguage;
            
            // If English, no translation needed
            if (targetLang === 'en' || !botMessage) {
                return botMessage;
            }
            
            console.log(`🤖 Translating bot response to ${targetLang}...`);
            
            try {
                const response = await fetch('/api/translate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        text: botMessage,
                        source_lang: 'en',
                        target_lang: targetLang,
                        user_preferred_lang: targetLang
                    })
                });
                
                const data = await response.json();
                
                if (data.success && data.translated_text) {
                    console.log(`✅ Bot response translated successfully`);
                    return data.translated_text;
                } else {
                    console.warn(`⚠️ Translation failed, using original: ${data.error}`);
                }
            } catch (error) {
                console.error('❌ Bot translation error:', error);
            }
            
            // Fallback to original English text
            return botMessage;
        }
    };

    // Auto-initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            window.AgriCareI18n.init();
        });
    } else {
        window.AgriCareI18n.init();
    }

    console.log('✅ AgriCareI18n module loaded');
})();
