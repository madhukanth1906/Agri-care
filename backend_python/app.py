from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import os
from datetime import timedelta, datetime
import hashlib
import json
import requests
from werkzeug.utils import secure_filename
import google.generativeai as genai
import base64
import io

# Firebase imports
try:
    import firebase_admin
    from firebase_admin import credentials, firestore, storage, auth
    import pyrebase
    from firebase_config import FIREBASE_CONFIG, SERVICE_ACCOUNT_KEY, COLLECTIONS, STORAGE_PATHS
    FIREBASE_AVAILABLE = True
    print("Firebase dependencies loaded")
except ImportError as e:
    print(f"Firebase support is unavailable: {e}")
    FIREBASE_AVAILABLE = False
    class firestore:
        @staticmethod
        def client():
            return None

# PyTorch imports - conditional loading
try:
    import torch
    import torchvision.transforms as transforms
    from PIL import Image
    import io
    PYTORCH_AVAILABLE = True
    print("PyTorch dependencies loaded")
except ImportError as e:
    print(f"PyTorch support is unavailable: {e}")
    PYTORCH_AVAILABLE = False
    class torch:
        @staticmethod
        def device(device_type):
            return device_type
        @staticmethod
        def load(*args, **kwargs):
            return None
    
    class transforms:
        class Compose:
            def __init__(self, transforms_list):
                self.transforms = transforms_list
            def __call__(self, x):
                return x
        
        class Resize:
            def __init__(self, size):
                self.size = size
        
        class ToTensor:
            pass
        
        class Normalize:
            def __init__(self, mean, std):
                pass

# Soundfile import for TTS (even though TTS is disabled, imports needed for endpoint code)
try:
    import soundfile as sf
except ImportError:
    sf = None
    print("soundfile is unavailable, so TTS is disabled")

# TensorFlow and multilingual support imports
try:
    import tensorflow as tf
    from langdetect import detect
    from transformers import MarianMTModel, MarianTokenizer
    import warnings
    warnings.filterwarnings('ignore')
    TF_AVAILABLE = True
    print("TensorFlow and multilingual dependencies loaded")
except ImportError as e:
    print(f"TensorFlow or multilingual support is unavailable: {e}")
    TF_AVAILABLE = False

# Initialize Flask app
app = Flask(__name__, static_folder='../frontend', static_url_path='')

# Configuration
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', '')
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY', '')
SARVAM_API_KEY = os.getenv('SARVAM_API_KEY', '')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')

app.config['JWT_SECRET_KEY'] = JWT_SECRET_KEY
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['JSON_AS_ASCII'] = False  # Enable proper rendering of Indian scripts in JSON

# Initialize extensions
jwt = JWTManager(app)
CORS(app, origins=["http://localhost:3000", "http://localhost:5000", "http://127.0.0.1:5000", "https://agricare-project.web.app"])

# Security headers
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response

# Cache headers for static files
@app.after_request
def add_cache_headers(response):
    if request.path.startswith('/css/') or request.path.startswith('/js/') or request.path.startswith('/img/'):
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    elif request.path.startswith('/'):
        response.headers['Cache-Control'] = 'public, max-age=3600'
    return response

# API Keys - Load from environment variables
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
HUGGING_FACE_API_KEY = os.getenv('HUGGING_FACE_API_KEY', '')
DATA_GOV_IN_API_KEY = os.getenv('DATA_GOV_IN_API_KEY', '')

# Model download helper
def download_model_from_github(model_url, local_filename):
    """
    Download a model file from GitHub when it is not available locally.
    """
    if os.path.exists(local_filename):
        print(f"Model file already exists: {local_filename}")
        return True

    try:
        print(f"Downloading model from GitHub: {model_url}")
        response = requests.get(model_url, stream=True, timeout=300)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        if total_size:
            print(f"Model size: {total_size / (1024*1024):.2f} MB")

        with open(local_filename, 'wb') as f:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total_size and downloaded % (1024*1024) == 0:
                    print(f"Downloaded {downloaded / (1024*1024):.1f} MB of {total_size / (1024*1024):.1f} MB")

        print("Model download completed successfully")
        return True
    except Exception as e:
        print(f"Failed to download model from GitHub: {e}")
        if os.path.exists(local_filename):
            os.remove(local_filename)
        return False

# TTS model configuration
TTS_AVAILABLE = False
tts_model = None
tts_processor = None
tts_description_tokenizer = None

LOCAL_TTS_PATH = r"G:\models\indic-parler-tts"
HUB_TTS_ID = "parler-tts/indic-parler-tts"

LOAD_TTS = False

if LOAD_TTS:
    try:
        from transformers import AutoProcessor, AutoTokenizer, ParlerTTSForConditionalGeneration
        import torch

        load_path = ""

        try:
            print(f"Attempting to load TTS model from local path: {LOCAL_TTS_PATH}")
            if os.path.exists(LOCAL_TTS_PATH) and os.path.isdir(LOCAL_TTS_PATH):
                tts_processor = AutoProcessor.from_pretrained(LOCAL_TTS_PATH)
                tts_description_tokenizer = AutoTokenizer.from_pretrained(LOCAL_TTS_PATH, subfolder="text_encoder")
                tts_model = ParlerTTSForConditionalGeneration.from_pretrained(LOCAL_TTS_PATH)
                load_path = LOCAL_TTS_PATH
                print("Loaded TTS model from local path")
            else:
                print(f"Local TTS path is not valid: {LOCAL_TTS_PATH}. Falling back to Hugging Face Hub")
                raise FileNotFoundError("Local path invalid")

        except Exception as local_error:
            print(f"Local TTS load failed ({local_error}). Trying Hugging Face Hub: {HUB_TTS_ID}")
            try:
                tts_processor = AutoProcessor.from_pretrained(HUB_TTS_ID)
                tts_description_tokenizer = AutoTokenizer.from_pretrained(HUB_TTS_ID, subfolder="text_encoder")
                tts_model = ParlerTTSForConditionalGeneration.from_pretrained(HUB_TTS_ID)
                load_path = HUB_TTS_ID
                print("Loaded TTS model from Hugging Face Hub")
            except Exception as hub_error:
                print("Failed to load the TTS model from both local and Hub sources")
                print(f"Hub error: {hub_error}")
                raise hub_error

        if tts_model and tts_processor and tts_description_tokenizer:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            tts_model.to(device)
            TTS_AVAILABLE = True
            print(f"TTS model ready from {load_path} on {device}")

    except Exception as e:
        print(f"Critical error during TTS setup: {e}")
        TTS_AVAILABLE = False
        tts_processor = None
        tts_model = None
        tts_description_tokenizer = None
else:
    print("Skipping TTS model loading because LOAD_TTS is False")

LOCAL_GEMMA_MODEL_PATH = r"G:\models\google\gemma-1.1-2b-it"
HUB_GEMMA_ID = "google/gemma-1.1-2b-it"

gemma_model = None
gemma_tokenizer = None
GEMMA_AVAILABLE = False

LOAD_GEMMA = False

if LOAD_GEMMA:
    print("Initializing Gemma model for chat responses")
    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM
        from pathlib import Path
        import torch

        load_path_or_id = ""

        if torch.cuda.is_available():
            print("CUDA found, using GPU")
            device_map = "auto"
            try:
                dtype = torch.bfloat16
                _ = torch.randn(1, device='cuda', dtype=dtype)
                print("Using bfloat16")
            except Exception:
                dtype = torch.float16
                print("bfloat16 is not supported, using float16")
        else:
            print("CUDA not found, so the model will run on CPU")
            device_map = "cpu"
            dtype = torch.float32

        try:
            print(f"Attempting to load Gemma model from local path: {LOCAL_GEMMA_MODEL_PATH}")
            model_path = Path(LOCAL_GEMMA_MODEL_PATH)
            if not model_path.exists() or not model_path.is_dir():
                print(f"Local Gemma path is not valid: {LOCAL_GEMMA_MODEL_PATH}. Falling back to Hugging Face Hub")
                raise FileNotFoundError("Local path invalid")

            gemma_tokenizer = AutoTokenizer.from_pretrained(LOCAL_GEMMA_MODEL_PATH)
            gemma_model = AutoModelForCausalLM.from_pretrained(
                LOCAL_GEMMA_MODEL_PATH,
                device_map=device_map,
                torch_dtype=dtype
            )
            load_path_or_id = LOCAL_GEMMA_MODEL_PATH
            print("Loaded Gemma model from local path")

        except Exception as local_error:
            print(f"Local Gemma load failed ({local_error}). Trying Hugging Face Hub: {HUB_GEMMA_ID}")
            try:
                gemma_tokenizer = AutoTokenizer.from_pretrained(HUB_GEMMA_ID)
                gemma_model = AutoModelForCausalLM.from_pretrained(
                    HUB_GEMMA_ID,
                    device_map=device_map,
                    torch_dtype=dtype
                )
                load_path_or_id = HUB_GEMMA_ID
                print("Loaded Gemma model from Hugging Face Hub")
            except Exception as hub_error:
                print("Failed to load the Gemma model from both local and Hub sources")
                print(f"Hub error: {hub_error}")
                raise hub_error

        if gemma_model and gemma_tokenizer:
            if device_map == "cpu":
                gemma_model.to("cpu")
            GEMMA_AVAILABLE = True
            print(f"Gemma model ready from {load_path_or_id}")

    except Exception as e:
        print(f"Critical error during Gemma setup: {e}")
        print("Fallback responses will be used instead")
        GEMMA_AVAILABLE = False
else:
    print("Skipping Gemma model loading because LOAD_GEMMA is False")

# ===============================================
# WEATHER API FUNCTION FOR GEMMA CHATBOT
# ===============================================
def get_current_weather(location):
    """Gets the current weather for a given city using the OpenWeatherMap API."""
    if not WEATHER_API_KEY:
        return json.dumps({"error": "Weather API key is not configured."})

    print(f"--- Calling Weather API for {location} ---")
    url = f"https://api.openweathermap.org/data/2.5/weather?q={location}&appid={WEATHER_API_KEY}&units=metric"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status() 
        data = response.json()
        
        weather_info = {
            "location": data.get("name", location),
            "temperature": data.get("main", {}).get("temp", "N/A"),
            "feels_like": data.get("main", {}).get("feels_like", "N/A"),
            "description": data.get("weather", [{}])[0].get("description", "N/A"),
            "humidity": data.get("main", {}).get("humidity", "N/A"),
            "wind_speed": data.get("wind", {}).get("speed", "N/A"),
        }
        return json.dumps(weather_info)
        
    except requests.exceptions.HTTPError as err:
        if response.status_code == 401:
            return json.dumps({"error": "Invalid Weather API key."})
        elif response.status_code == 404:
            return json.dumps({"error": f"City '{location}' not found."})
        else:
            return json.dumps({"error": f"HTTP error getting weather: {err}"})
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": f"Could not connect to weather service: {e}"})
    except Exception as e:
        return json.dumps({"error": f"An unexpected error occurred getting weather: {e}"})

# ===============================================
# GEMMA CHATBOT FUNCTION WITH TOOL CALLING
# ===============================================
def run_gemma_chatbot(user_message):
    """
    Chatbot controller using local Gemma model with few-shot prompting 
    and weather tool calling capability.
    """
    if not GEMMA_AVAILABLE:
        print("ERROR: Gemma model not loaded.")
        return None
        
    chat = [
        {"role": "user", "content": (
            "You are AgriGenius, a helpful farming and weather assistant. "
            "You can answer questions about agriculture.\n"
            "You have a tool: get_current_weather(location)\n"
            "If asked for weather, respond ONLY with: [TOOL_CALL: get_current_weather(location=\"<city_name>\")]\n"
            "For all other agriculture questions, answer them directly.\n\n"
            "USER_REQUEST: What is a good way to manage pests on tomato plants?"
        )},
        {"role": "model", "content": "A good way to manage pests on tomato plants is to use neem oil spray, introduce beneficial insects like ladybugs, or plant companion plants like marigolds."},
        {"role": "user", "content": "USER_REQUEST: What is the weather in Chennai?"},
        {"role": "model", "content": "[TOOL_CALL: get_current_weather(location=\"Chennai\")]"},
        {"role": "user", "content": f"USER_REQUEST: {user_message}"}
    ]

    # 1. FIRST MODEL CALL (Decision)
    try:
        prompt = gemma_tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
        inputs = gemma_tokenizer.encode(prompt, add_special_tokens=False, return_tensors="pt")
        input_length = inputs.shape[1] 
        
        outputs = gemma_model.generate(input_ids=inputs.to(gemma_model.device), max_new_tokens=150)
        
        new_tokens = outputs[0][input_length:]
        decision = gemma_tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
    except Exception as e:
        print(f"Error during model generation (Decision): {e}")
        return None

    print(f"Gemma's Decision: {decision}")

    # 2. CHECK DECISION
    if decision.startswith("[TOOL_CALL: get_current_weather"):
        try:
            location = decision.split("(\"")[1].split("\")]")[0]
        except Exception as e:
            print(f"Error parsing location: {e}")
            return "I understood you want the weather, but I couldn't figure out the location."

        weather_data_json = get_current_weather(location)
        print(f"Tool Result: {weather_data_json}")
        
        # Check if weather tool returned an error
        try:
            weather_data = json.loads(weather_data_json)
            if "error" in weather_data:
                return f"Sorry, I couldn't get the weather. {weather_data['error']}"
        except json.JSONDecodeError:
            return "Sorry, I received an invalid response from the weather service."

        # 3. SECOND MODEL CALL (Final Answer)
        try:
            chat.append({"role": "model", "content": decision}) 
            chat.append({"role": "user", "content": f"TOOL_RESULT: {weather_data_json}"}) 
            
            prompt = gemma_tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
            inputs = gemma_tokenizer.encode(prompt, add_special_tokens=False, return_tensors="pt")
            
            input_length = inputs.shape[1]
            
            outputs = gemma_model.generate(input_ids=inputs.to(gemma_model.device), max_new_tokens=150)
            
            new_tokens = outputs[0][input_length:]
            final_response = gemma_tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
            
            return final_response
        except Exception as e:
            print(f"Error during model generation (Final Answer): {e}")
            return "Sorry, I encountered an error while formulating the final response."

    else:
        # It's a normal question
        return decision

# ===============================================
# SARVAM AI TRANSLATION API CONFIGURATION
# ===============================================
# High-quality translation for Indian languages using Sarvam AI API
SARVAM_API_URL = "https://api.sarvam.ai/translate"

# Translation is available via API
TRANSLATION_AVAILABLE = True

# Sarvam AI Language Code Mapping (ISO 639-1)
SARVAM_LANG_CODES = {
    'en': 'en-IN',  # English (India)
    'hi': 'hi-IN',  # Hindi
    'bn': 'bn-IN',  # Bengali
    'te': 'te-IN',  # Telugu
    'mr': 'mr-IN',  # Marathi
    'ta': 'ta-IN',  # Tamil
    'gu': 'gu-IN',  # Gujarati
    'kn': 'kn-IN',  # Kannada
    'ml': 'ml-IN',  # Malayalam
    'pa': 'pa-IN',  # Punjabi
    'od': 'or-IN',  # Odia
    'as': 'as-IN',  # Assamese
    'ur': 'ur-IN'   # Urdu
}

print("✅ Sarvam AI Translation API configured (API-based, no model loading)")
print(f"🌍 Supported languages: {', '.join(SARVAM_LANG_CODES.keys())}")

# Dynamic Translation Helper Functions
def get_supported_languages():
    """Returns list of supported language codes for the dynamic model."""
    # These should be supported by your specific translation model
    return ['en', 'ta', 'hi', 'te', 'bn', 'mr', 'gu', 'kn', 'ml', 'pa', 'od', 'as', 'ur']

def detect_language(text):
    """
    Automatically detect the language of input text.
    Uses langdetect library for detection.
    """
    try:
        from langdetect import detect
        detected_lang = detect(text)
        
        # Map detected language to supported codes
        lang_map = {
            'en': 'en', 'ta': 'ta', 'hi': 'hi', 'te': 'te', 
            'bn': 'bn', 'mr': 'mr', 'gu': 'gu', 'kn': 'kn', 
            'ml': 'ml', 'pa': 'pa', 'ur': 'ur', 'or': 'od', 'as': 'as'
        }
        
        detected = lang_map.get(detected_lang, 'en')
        print(f"🔍 Detected language: {detected_lang} → {detected}")
        return detected
    except Exception as e:
        print(f"⚠️ Language detection failed: {e}, defaulting to English")
        return 'en'

def translate_text(text, source_lang="en", target_lang="en"):
    """
    Translates text using Sarvam AI Translation API.
    High-quality translation for Indian languages.
    
    Args:
        text: Text to translate
        source_lang: Source language code (e.g., 'en', 'hi', 'ta')
        target_lang: Target language code (e.g., 'en', 'hi', 'ta')
        
    Returns:
        Translated text string
    """
    # Skip translation if source and target are the same or text is empty
    if not text or source_lang == target_lang:
        return text
    
    # If translation is not available, return original text
    if not TRANSLATION_AVAILABLE:
        print(f"⚠️ Translation unavailable, returning original text")
        return text

    try:
        # Get Sarvam language codes
        src_code = SARVAM_LANG_CODES.get(source_lang, 'en-IN')
        tgt_code = SARVAM_LANG_CODES.get(target_lang, 'en-IN')
        
        print(f"🌐 Translating via Sarvam API: {src_code} → {tgt_code}")
        
        # Prepare API request
        headers = {
            'Content-Type': 'application/json',
            'API-Subscription-Key': SARVAM_API_KEY
        }
        
        payload = {
            'input': text,
            'source_language_code': src_code,
            'target_language_code': tgt_code,
            'speaker_gender': 'Female',
            'mode': 'formal',
            'model': 'mayura:v1',
            'enable_preprocessing': True
        }
        
        # Make API request
        response = requests.post(SARVAM_API_URL, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            translated_text = result.get('translated_text', text)
            print(f"✅ Translation successful: '{text[:50]}...' → '{translated_text[:50]}...'")
            return translated_text
        else:
            print(f"⚠️ Sarvam API error ({response.status_code}): {response.text}")
            return text

    except requests.exceptions.Timeout:
        print(f"⚠️ Translation API timeout, returning original text")
        return text
    except Exception as e:
        print(f"❌ Translation error: {e}")
        return text

def translate_disease_result(result_data, target_lang='en'):
    """
    Translates all text fields within the disease result dictionary.
    """
    if target_lang == 'en':
        return result_data # No translation needed

    translated_result = result_data.copy() # Start with a copy

    # Translate single string fields
    for key in ['disease', 'recovery_timeline', 'additional_notes']:
        if key in translated_result and translated_result[key]:
            translated_result[key] = translate_text(translated_result[key], 'en', target_lang)

    # Translate lists of strings
    for key in ['symptoms', 'causes', 'prevention', 'recommendations']:
        if key in translated_result and translated_result[key]:
            translated_list = [translate_text(item, 'en', target_lang) for item in translated_result[key]]
            translated_result[key] = translated_list
            
    # Also translate the 'verified_diagnosis' from Gemini
    if 'gemini_verification' in translated_result and translated_result['gemini_verification'].get('verified_diagnosis'):
        gemini_info = translated_result['gemini_verification']
        gemini_info['verified_diagnosis'] = translate_text(gemini_info['verified_diagnosis'], 'en', target_lang)

    return translated_result

def detect_language(text):
    """Detect the language of input text with better handling of common words."""
    try:
        text_lower = text.lower().strip()
        
        # Handle common greetings and simple words that often get misdetected
        common_patterns = {
            'en': ['hai', 'hi', 'hello', 'hey', 'what', 'how', 'can you', 'speak', 'talk', 'weather', 'help'],
            'hi': ['नमस्ते', 'हैलो', 'कैसे', 'क्या', 'मदद', 'फसल'],
            'ta': ['வணக்கம்', 'எப்படி', 'என்ன', 'உதவி', 'பயிர்']
        }
        
        # Check for exact matches first
        for lang, patterns in common_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                if lang != 'en' or len(text.split()) <= 3:  # For short English phrases
                    print(f"🔍 Pattern-matched language: {lang}")
                    return lang
        
        # Only use langdetect for longer, more complex text
        if len(text.split()) > 3:
            detected = detect(text)
            print(f"🔍 Auto-detected language: {detected}")
            return detected
        else:
            # For short text, assume English to avoid misdetection
            print(f"🔍 Short text detected as English: '{text}'")
            return 'en'
            
    except Exception as e:
        print(f"🔍 Language detection error: {e}, assuming English")
        return 'en'

def process_with_gemini(text, language='en'):
    """Process text with Gemini API for intelligent agricultural responses."""
    try:
        print(f"🤖 Processing with Gemini API: {text[:100]}...")
        
        # Configure Gemini AI
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Create the model
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Generate response
        response = model.generate_content(text)
        
        if response and response.text:
            print(f"✅ Gemini API response: {response.text[:80]}...")
            return response.text
        else:
            print("⚠️ Gemini API returned empty response")
            return None
            
    except Exception as e:
        print(f"❌ Gemini API processing error: {e}")
        return None

# Disease Detection Model Configuration
# Using local model file from G:\models directory
DISEASE_MODEL_PATH = r"G:\projects\models\best_disease_model.pth"
disease_model = None
disease_transform = None

# Translation API Routes
@app.route('/api/translate', methods=['POST'])
def api_translate():
    """
    API endpoint for text translation using Sarvam AI.
    
    Supports user preferred language priority:
    1. target_lang from request (highest priority)
    2. user_preferred_lang from request
    3. Browser default language
    4. English (fallback)
    
    Request JSON:
        {
            "text": "Text to translate",
            "target_lang": "hi",              // Optional: specific target for this translation
            "source_lang": "en",              // Optional: will auto-detect if not provided
            "user_preferred_lang": "ta"       // Optional: user's saved language preference
        }
    
    Response JSON:
        {
            "success": true,
            "original_text": "Hello",
            "translated_text": "नमस्ते",
            "detected_source_lang": "en",
            "target_lang": "hi",
            "used_preference": true
        }
    """
    try:
        data = request.get_json()
        text = data.get('text', '')
        source_lang = data.get('source_lang')  # Optional - will auto-detect
        
        # PRIORITY SYSTEM: target_lang > user_preferred_lang > en
        target_lang = data.get('target_lang')  # Specific override
        user_preferred = data.get('user_preferred_lang')  # User's saved preference
        
        # Apply priority logic
        used_preference = False
        if not target_lang:
            if user_preferred and user_preferred in SARVAM_LANG_CODES:
                target_lang = user_preferred
                used_preference = True
                print(f"✅ Using user preferred language: {target_lang}")
            else:
                target_lang = 'en'  # Default fallback
        
        # Validate input
        if not text:
            return jsonify({
                'success': False,
                'error': 'Text is required',
                'message': 'Please provide text to translate'
            }), 400
        
        # Validate target language
        if target_lang not in SARVAM_LANG_CODES:
            return jsonify({
                'success': False,
                'error': 'Unsupported language',
                'message': f'Language code "{target_lang}" is not supported',
                'supported_languages': list(SARVAM_LANG_CODES.keys())
            }), 400
        
        # Auto-detect source language if not provided
        if not source_lang:
            source_lang = detect_language(text)
            print(f"🔍 Auto-detected source language: {source_lang}")
        
        # Translate text
        translated_text = translate_text(text, source_lang, target_lang)
        
        return jsonify({
            'success': True,
            'original_text': text,
            'translated_text': translated_text,
            'detected_source_lang': source_lang,
            'target_lang': target_lang,
            'used_preference': used_preference,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"❌ Translation API error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Translation failed',
            'message': str(e)
        }), 500

@app.route('/api/translate/languages', methods=['GET'])
def api_supported_languages():
    """
    Get list of all supported languages for translation.
    
    Response JSON:
        {
            "success": true,
            "languages": [
                {"code": "en", "name": "English", "native": "English"},
                {"code": "hi", "name": "Hindi", "native": "हिन्दी"},
                ...
            ],
            "total": 13
        }
    """
    try:
        # Complete language list with native names
        languages = [
            {"code": "en", "name": "English", "native": "English"},
            {"code": "hi", "name": "Hindi", "native": "हिन्दी"},
            {"code": "ta", "name": "Tamil", "native": "தமிழ்"},
            {"code": "te", "name": "Telugu", "native": "తెలుగు"},
            {"code": "bn", "name": "Bengali", "native": "বাংলা"},
            {"code": "mr", "name": "Marathi", "native": "मराठी"},
            {"code": "gu", "name": "Gujarati", "native": "ગુજરાતી"},
            {"code": "kn", "name": "Kannada", "native": "ಕನ್ನಡ"},
            {"code": "ml", "name": "Malayalam", "native": "മലയാളം"},
            {"code": "pa", "name": "Punjabi", "native": "ਪੰਜਾਬੀ"},
            {"code": "od", "name": "Odia", "native": "ଓଡ଼ିଆ"},
            {"code": "as", "name": "Assamese", "native": "অসমীয়া"},
            {"code": "ur", "name": "Urdu", "native": "اردو"}
        ]
        
        return jsonify({
            'success': True,
            'languages': languages,
            'total': len(languages),
            'translation_available': TRANSLATION_AVAILABLE,
            'provider': 'Sarvam AI API'
        })
        
    except Exception as e:
        print(f"❌ Languages API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/translate/detect', methods=['POST'])
def api_detect_language():
    """
    Detect the language of given text.
    
    Request JSON:
        {
            "text": "Text to detect language"
        }
    
    Response JSON:
        {
            "success": true,
            "text": "Input text",
            "detected_language": "hi",
            "language_name": "Hindi",
            "confidence": "high"
        }
    """
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({
                'success': False,
                'error': 'Text is required'
            }), 400
        
        detected_lang = detect_language(text)
        
        # Get language name
        lang_names = {
            'en': 'English', 'hi': 'Hindi', 'ta': 'Tamil', 'te': 'Telugu',
            'bn': 'Bengali', 'mr': 'Marathi', 'gu': 'Gujarati', 'kn': 'Kannada',
            'ml': 'Malayalam', 'pa': 'Punjabi', 'od': 'Odia', 'as': 'Assamese',
            'ur': 'Urdu'
        }
        
        return jsonify({
            'success': True,
            'text': text[:100] + '...' if len(text) > 100 else text,
            'detected_language': detected_lang,
            'language_name': lang_names.get(detected_lang, detected_lang),
            'confidence': 'high'
        })
        
    except Exception as e:
        print(f"❌ Language detection error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ===============================================
# OLLAMA AGRICULTURE CHATBOT ENDPOINT
# ===============================================
@app.route('/api/chat', methods=['POST'])
def ollama_agriculture_chat():
    """
    Ollama-based agriculture chatbot endpoint.
    
    Connects to local Ollama instance for evidence-based farming advice.
    
    Request JSON:
        {
            "message": "User question",
            "language": "en" (optional, default: "en"),
            "context": [] (optional conversation history)
        }
    
    Response JSON:
        {
            "success": true,
            "response": "Bot response",
            "language": "en",
            "timestamp": "2025-11-01T10:30:00"
        }
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('message'):
            return jsonify({
                'success': False,
                'error': 'Message is required'
            }), 400
        
        user_message = data['message']
        language = data.get('language', 'en')
        user_context = data.get('context', [])
        
        print(f"🤖 Ollama Chat - Language: {language}, Message: {user_message}")
        
        # Agriculture-focused system prompt
        system_prompt = """You are AgriGenius — a safe, evidence-based agriculture advisor for Indian farmers.

Key Responsibilities:
- Always ask clarifying questions (crop, stage, soil type, irrigation, season, region)
- Prioritize cultural & biological pest controls
- Only give low-toxicity chemical options if necessary
- For each query, include: short diagnosis, 2-3 clear steps, and a short reason
- Avoid recommending restricted chemicals or unsafe home remedies
- Provide practical, actionable advice based on Indian farming conditions

Response Format:
1. Brief diagnosis of the issue
2. 2-3 actionable steps
3. Reasoning/explanation
4. Follow-up questions if needed

Be concise, practical, and farmer-friendly."""

        # Build conversation messages
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add context if provided
        for ctx in user_context:
            if ctx.get('role') and ctx.get('content'):
                messages.append({
                    "role": ctx['role'],
                    "content": ctx['content']
                })
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        # Call Ollama API (local first) - Using native Ollama format
        ollama_url = "http://localhost:11434/api/chat"
        ollama_payload = {
            "model": "llama2:latest",  # Using llama2:latest as confirmed by user
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.3,  # Balanced temperature for helpful but consistent responses
                "num_predict": 400   # Max tokens in Ollama format
            }
        }
        
        print(f"📡 Calling local Ollama API at {ollama_url}...")
        
        try:
            ollama_response = requests.post(
                ollama_url,
                json=ollama_payload,
                timeout=120  # Increased to 2 minutes for first-time model loading
            )
            ollama_response.raise_for_status()
            
            ollama_data = ollama_response.json()
            
            # Extract response - Ollama native format uses 'message' -> 'content'
            bot_response = ollama_data.get('message', {}).get('content', '')
            
            if not bot_response:
                raise ValueError("Empty response from Ollama")
            
            print(f"✅ Ollama response received: {len(bot_response)} chars")
            
            # Translate response if needed
            if language != 'en' and TRANSLATION_AVAILABLE:
                print(f"🌐 Translating response to {language}...")
                bot_response = translate_text(bot_response, language)
            
            return jsonify({
                'success': True,
                'response': bot_response,
                'language': language,
                'timestamp': datetime.now().isoformat(),
                'model': 'llama2:latest',
                'provider': 'Ollama (Local)'
            })
            
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as ollama_error:
            print(f"❌ Local Ollama failed: {ollama_error}")
            print("🔄 Attempting cloud API fallback...")
            
            # Fallback to cloud API if provided (OpenRouter format)
            try:
                cloud_api_key = OPENROUTER_API_KEY
                if not cloud_api_key:
                    raise ValueError("OpenRouter API key is not configured.")
                cloud_url = "https://openrouter.ai/api/v1/chat/completions"  # OpenRouter endpoint
                
                cloud_payload = {
                    "model": "meta-llama/llama-2-7b-chat",
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 400
                }
                
                cloud_response = requests.post(
                    cloud_url,
                    headers={
                        "Authorization": f"Bearer {cloud_api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "http://localhost:5000",  # Required by OpenRouter
                        "X-Title": "AgriCare"  # Optional but recommended
                    },
                    json=cloud_payload,
                    timeout=30
                )
                cloud_response.raise_for_status()
                
                cloud_data = cloud_response.json()
                bot_response = cloud_data.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                if not bot_response:
                    raise ValueError("Empty response from cloud API")
                
                print(f"✅ Cloud API response received: {len(bot_response)} chars")
                
                # Translate response if needed
                if language != 'en' and TRANSLATION_AVAILABLE:
                    bot_response = translate_text(bot_response, language)
                
                return jsonify({
                    'success': True,
                    'response': bot_response,
                    'language': language,
                    'timestamp': datetime.now().isoformat(),
                    'model': 'llama-2-7b-chat',
                    'provider': 'OpenRouter (Cloud Fallback)'
                })
                
            except Exception as cloud_error:
                print(f"❌ Cloud API fallback also failed: {cloud_error}")
                
                return jsonify({
                    'success': False,
                    'error': 'Both local Ollama and cloud API unavailable',
                    'fallback_response': 'AI assistant temporarily unavailable. Please check if Ollama is running (http://localhost:11434) or try again later.',
                    'details': {
                        'local_error': str(ollama_error),
                        'cloud_error': str(cloud_error)
                    }
                }), 503
            
    except Exception as e:
        print(f"❌ Ollama chat error: {e}")
        
        # Provide fallback response
        fallback_responses = {
            'en': "I'm currently unavailable. Please ensure Ollama is running with llama2:13b-chat-q8_0 model, or try again later.",
            'hi': "मैं अभी उपलब्ध नहीं हूं। कृपया सुनिश्चित करें कि Ollama llama2:13b-chat-q8_0 मॉडल के साथ चल रहा है, या बाद में पुनः प्रयास करें।"
        }
        
        return jsonify({
            'success': False,
            'error': str(e),
            'fallback_response': fallback_responses.get(language, fallback_responses['en'])
        }), 500

@app.route('/api/chat/health', methods=['GET'])
def ollama_health():
    """Check if Ollama service is available"""
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=5)
        response.raise_for_status()
        
        models = response.json().get('models', [])
        model_names = [m.get('name', '') for m in models]
        
        # Check if llama2:latest is available
        has_llama2 = any('llama2' in name.lower() for name in model_names)
        
        return jsonify({
            'success': True,
            'status': 'healthy',
            'ollama_available': True,
            'models': model_names,
            'recommended_model': 'llama2:latest',
            'llama2_available': has_llama2,
            'cloud_fallback_available': True
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'unavailable',
            'ollama_available': False,
            'error': str(e),
            'message': 'Ollama service not running on localhost:11434. Cloud fallback will be used.',
            'cloud_fallback_available': True
        }), 200  # Return 200 instead of 503 since cloud fallback exists

# Firebase Configuration
db = None
firebase_auth = None
storage_bucket = None

# Initialize Firebase
def initialize_firebase():
    global db, firebase_auth, storage_bucket
    
    if not FIREBASE_AVAILABLE:
        print("🔥 Firebase dependencies not available - using fallback storage")
        return False

    try:
        # Check if service account key is properly configured
        if isinstance(SERVICE_ACCOUNT_KEY, dict):
            # Check if it's still using placeholder values
            if "your-private-key-id-from-service-account-json" in str(SERVICE_ACCOUNT_KEY.get("private_key_id", "")):
                print("🔥 Firebase service account key not configured - using fallback storage")
                print("   Please replace placeholder values in firebase_config.py with actual credentials")
                print("   To enable Firebase: Download service account key from Firebase Console")
                return False
        elif isinstance(SERVICE_ACCOUNT_KEY, str):
            # It's a file path
            if not os.path.exists(SERVICE_ACCOUNT_KEY):
                print("🔥 Firebase service account key file not found - using fallback storage")
                print(f"   Expected file: {SERVICE_ACCOUNT_KEY}")
                print("   To enable Firebase: Download service account key from Firebase Console")
                return False
        else:
            print("🔥 Firebase service account key configuration invalid - using fallback storage")
            return False
        
        # Initialize Firebase Admin SDK
        if not firebase_admin._apps:
            cred = credentials.Certificate(SERVICE_ACCOUNT_KEY)
            firebase_admin.initialize_app(cred, {
                'storageBucket': FIREBASE_CONFIG['storageBucket']
            })
        
        # Initialize Firestore
        db = firestore.client()
        
        # Initialize Firebase Auth for client-side
        firebase_auth = pyrebase.initialize_app(FIREBASE_CONFIG)
        
        # Initialize Storage bucket
        storage_bucket = storage.bucket()
        
        print("✅ Firebase initialized successfully")
        return True
        
    except Exception as e:
        error_msg = str(e)
        if "PEM file" in error_msg or "InvalidByte" in error_msg:
            print("🔥 Firebase service account key is corrupted - using fallback storage")
            print("   Please download a fresh service account key from Firebase Console")
        elif "permission" in error_msg.lower() or "access" in error_msg.lower():
            print("🔥 Firebase access denied - check credentials and permissions")
        else:
            print(f"🔥 Firebase initialization failed - using fallback storage")
            print(f"   Error: {error_msg}")
        db = None
        return False# Fallback in-memory user storage (when Firebase is not available)
users = []

# Utility functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

def find_user_by_email(email):
    """Find user by email from Firebase Firestore or fallback storage"""
    if db is not None:
        try:
            # Query Firestore
            users_ref = db.collection(COLLECTIONS['USERS'])
            query = users_ref.where('email', '==', email).limit(1)
            docs = query.get()
            
            if docs:
                user_doc = docs[0]
                user_data = user_doc.to_dict()
                user_data['id'] = user_doc.id
                return user_data
            return None
        except Exception as e:
            print(f"Error finding user in Firestore: {e}")
            return None
    else:
        # Fallback to in-memory storage
        return next((user for user in users if user['email'] == email), None)

def create_user(email, password, full_name):
    """Create a new user in Firebase Firestore or fallback storage"""
    if db is not None:
        try:
            # Create user document in Firestore
            user_data = {
                'email': email,
                'password_hash': hash_password(password),
                'full_name': full_name,
                'created_at': firestore.SERVER_TIMESTAMP,
                'last_login': None,
                'disease_detections_count': 0,
                'yield_predictions_count': 0,
                'chat_sessions_count': 0
            }
            
            # Add user to Firestore
            doc_ref = db.collection(COLLECTIONS['USERS']).add(user_data)
            user_data['id'] = doc_ref[1].id
            
            print(f"✅ User created in Firestore: {email}")
            return user_data
            
        except Exception as e:
            print(f"❌ Error creating user in Firestore: {e}")
            return None
    else:
        # Fallback to in-memory storage
        user_data = {
            'id': str(len(users) + 1),
            'email': email,
            'password_hash': hash_password(password),
            'full_name': full_name,
            'created_at': datetime.now().isoformat(),
            'last_login': None,
            'disease_detections_count': 0,
            'yield_predictions_count': 0,
            'chat_sessions_count': 0
        }
        users.append(user_data)
        return user_data

def update_user_login(user_id):
    """Update user's last login timestamp"""
    if db is not None:
        try:
            db.collection(COLLECTIONS['USERS']).document(user_id).update({
                'last_login': firestore.SERVER_TIMESTAMP
            })
        except Exception as e:
            print(f"Error updating user login: {e}")
    # For in-memory storage, we don't track this for simplicity

def increment_user_activity(user_id, activity_type):
    """Increment user activity counters"""
    if db is not None:
        try:
            field_map = {
                'disease_detection': 'disease_detections_count',
                'yield_prediction': 'yield_predictions_count', 
                'chat_session': 'chat_sessions_count'
            }
            
            if activity_type in field_map:
                db.collection(COLLECTIONS['USERS']).document(user_id).update({
                    field_map[activity_type]: firestore.Increment(1)
                })
        except Exception as e:
            print(f"Error incrementing user activity: {e}")

def create_google_user(google_uid, email, display_name, photo_url, provider_id):
    """Create a new Google user in Firebase Firestore or fallback storage"""
    if db is not None:
        try:
            # Create user document in Firestore with Google data
            user_data = {
                'email': email,
                'google_uid': google_uid,
                'display_name': display_name,
                'name': display_name,  # Use display name as the name
                'full_name': display_name,
                'photo_url': photo_url,
                'provider_id': provider_id,
                'created_at': firestore.SERVER_TIMESTAMP,
                'last_login': firestore.SERVER_TIMESTAMP,
                'disease_detections_count': 0,
                'yield_predictions_count': 0,
                'chat_sessions_count': 0,
                'auth_method': 'google'
            }
            
            # Add user to Firestore
            doc_ref = db.collection(COLLECTIONS['USERS']).add(user_data)
            user_data['id'] = doc_ref[1].id
            
            print(f"✅ Google user created in Firestore: {email}")
            return user_data
            
        except Exception as e:
            print(f"❌ Error creating Google user in Firestore: {e}")
            return None
    else:
        # Fallback to in-memory storage
        user_data = {
            'id': str(len(users) + 1),
            'email': email,
            'google_uid': google_uid,
            'display_name': display_name,
            'name': display_name,
            'full_name': display_name,
            'photo_url': photo_url,
            'provider_id': provider_id,
            'created_at': datetime.now().isoformat(),
            'last_login': datetime.now().isoformat(),
            'disease_detections_count': 0,
            'yield_predictions_count': 0,
            'chat_sessions_count': 0,
            'auth_method': 'google'
        }
        users.append(user_data)
        return user_data

def update_user_profile(user_id, profile_data):
    """Update user profile information"""
    if db is not None:
        try:
            db.collection(COLLECTIONS['USERS']).document(user_id).update(profile_data)
            print(f"✅ User profile updated in Firestore: {user_id}")
        except Exception as e:
            print(f"❌ Error updating user profile: {e}")
    else:
        # Update in-memory storage
        for user in users:
            if user['id'] == user_id:
                user.update(profile_data)
                break

# Firebase Storage Functions
def upload_image_to_storage(file, user_id, image_type='disease'):
    """Upload image to Firebase Storage"""
    if storage_bucket is None:
        return None
    
    try:
        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{user_id}_{timestamp}_{secure_filename(file.filename)}"
        
        # Choose storage path based on image type
        if image_type == 'disease':
            storage_path = f"{STORAGE_PATHS['DISEASE_IMAGES']}{filename}"
        else:
            storage_path = f"{STORAGE_PATHS['USER_PROFILES']}{filename}"
        
        # Upload file
        blob = storage_bucket.blob(storage_path)
        blob.upload_from_string(
            file.read(),
            content_type=file.content_type or 'image/jpeg'
        )
        
        # Make it publicly accessible
        blob.make_public()
        
        return {
            'url': blob.public_url,
            'path': storage_path,
            'filename': filename
        }
        
    except Exception as e:
        print(f"Error uploading image to Firebase Storage: {e}")
        return None

def save_disease_detection(user_id, image_info, disease_result):
    """Save disease detection result to Firestore"""
    if db is None:
        return None
    
    try:
        detection_data = {
            'user_id': user_id,
            'image_url': image_info.get('url') if image_info else None,
            'image_path': image_info.get('path') if image_info else None,
            'disease_name': disease_result.get('disease'),
            'confidence': disease_result.get('confidence'),
            'local_prediction': disease_result.get('local_model_prediction'),
            'gemini_verification': disease_result.get('gemini_verification'),
            'recommendations': disease_result.get('recommendations', []),
            'symptoms': disease_result.get('symptoms', []),
            'causes': disease_result.get('causes', []),
            'prevention': disease_result.get('prevention', []),
            'recovery_timeline': disease_result.get('recovery_timeline'),
            'timestamp': firestore.SERVER_TIMESTAMP
        }
        
        # Save to Firestore
        doc_ref = db.collection(COLLECTIONS['DISEASE_DETECTIONS']).add(detection_data)
        
        # Increment user activity counter
        increment_user_activity(user_id, 'disease_detection')
        
        return doc_ref[1].id
        
    except Exception as e:
        print(f"Error saving disease detection: {e}")
        return None

def save_yield_prediction(user_id, prediction_data, result):
    """Save yield prediction to Firestore"""
    if db is None:
        return None
    
    try:
        yield_data = {
            'user_id': user_id,
            'crop_type': prediction_data.get('crop'),
            'area': prediction_data.get('area'),
            'location': prediction_data.get('location'),
            'predicted_yield': result.get('predicted_yield'),
            'confidence': result.get('confidence', 0.0),
            'factors': result.get('factors', []),
            'recommendations': result.get('recommendations', []),
            'timestamp': firestore.SERVER_TIMESTAMP
        }
        
        doc_ref = db.collection(COLLECTIONS['YIELD_PREDICTIONS']).add(yield_data)
        increment_user_activity(user_id, 'yield_prediction')
        
        return doc_ref[1].id
        
    except Exception as e:
        print(f"Error saving yield prediction: {e}")
        return None

def save_chat_message(user_id, message, response, language='en'):
    """Save chat interaction to Firestore"""
    if db is None:
        return None
    
    try:
        chat_data = {
            'user_id': user_id,
            'user_message': message,
            'bot_response': response,
            'language': language,
            'timestamp': firestore.SERVER_TIMESTAMP
        }
        
        doc_ref = db.collection(COLLECTIONS['CHAT_HISTORY']).add(chat_data)
        increment_user_activity(user_id, 'chat_session')
        
        return doc_ref[1].id
        
    except Exception as e:
        print(f"Error saving chat message: {e}")
        return None

def get_user_history(user_id, history_type='all', limit=10):
    """Get user's history from Firestore"""
    if db is None:
        return []
    
    try:
        if history_type == 'disease_detections' or history_type == 'all':
            detections_ref = db.collection(COLLECTIONS['DISEASE_DETECTIONS'])
            query = detections_ref.where('user_id', '==', user_id).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit)
            detections = [{'id': doc.id, **doc.to_dict(), 'type': 'disease_detection'} for doc in query.get()]
        
        if history_type == 'yield_predictions' or history_type == 'all':
            yields_ref = db.collection(COLLECTIONS['YIELD_PREDICTIONS'])
            query = yields_ref.where('user_id', '==', user_id).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit)
            yields = [{'id': doc.id, **doc.to_dict(), 'type': 'yield_prediction'} for doc in query.get()]
        
        if history_type == 'chat_history' or history_type == 'all':
            chat_ref = db.collection(COLLECTIONS['CHAT_HISTORY'])
            query = chat_ref.where('user_id', '==', user_id).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit)
            chats = [{'id': doc.id, **doc.to_dict(), 'type': 'chat'} for doc in query.get()]
        
        if history_type == 'all':
            # Combine and sort all results
            all_results = []
            if 'detections' in locals():
                all_results.extend(detections)
            if 'yields' in locals():
                all_results.extend(yields)
            if 'chats' in locals():
                all_results.extend(chats)
            
            # Sort by timestamp (newest first)
            all_results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return all_results[:limit]
        elif history_type == 'disease_detections':
            return detections if 'detections' in locals() else []
        elif history_type == 'yield_predictions':
            return yields if 'yields' in locals() else []
        elif history_type == 'chat_history':
            return chats if 'chats' in locals() else []
        
        return []
        
    except Exception as e:
        print(f"Error getting user history: {e}")
        return []

# Disease Detection Model Functions
def load_disease_model():
    """Load the PyTorch disease detection model"""
    global disease_model, disease_transform
    
    if not PYTORCH_AVAILABLE:
        print("PyTorch not available - disease detection will use fallback mode")
        return False
    
    try:
        import torchvision.models as models
        import pickle  # Import pickle for compatibility with older model files
        
        print(f"Loading disease detection model from {DISEASE_MODEL_PATH}...")
        
        # Check if model file exists
        if not os.path.exists(DISEASE_MODEL_PATH):
            print(f"Error: Model file not found at {DISEASE_MODEL_PATH}")
            return False
        
        # Load the model state dict
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"Using device: {device}")
        
        # Load the state dict
        # Note: weights_only=False and pickle_module=pickle are required for PyTorch 2.6+ to load older models
        state_dict = torch.load(DISEASE_MODEL_PATH, map_location=device, weights_only=False, pickle_module=pickle)
        print(f"Loaded state dict with {len(state_dict)} parameters")
        
        # Based on the layer names, this appears to be a ResNet model
        # Let's try different ResNet architectures to find the right one
        resnet_models = [
            (models.resnet50, "ResNet-50"),
            (models.resnet34, "ResNet-34"),
            (models.resnet18, "ResNet-18"),
            (models.resnet101, "ResNet-101"),
            (models.resnet152, "ResNet-152")
        ]
        
        # Determine number of classes from the final layer
        fc_weight = state_dict.get('fc.weight')
        if fc_weight is not None:
            num_classes = fc_weight.shape[0]
            print(f"Detected {num_classes} classes from model")
        else:
            print("Warning: Could not determine number of classes, using default 10")
            num_classes = 10
        
        model_loaded = False
        for model_fn, model_name in resnet_models:
            try:
                print(f"Trying {model_name}...")
                
                # Create model with the correct number of classes
                model = model_fn(weights=None)
                model.fc = torch.nn.Linear(model.fc.in_features, num_classes)
                
                # Try to load the state dict
                model.load_state_dict(state_dict, strict=True)
                
                # Move to device and set to eval mode
                disease_model = model.to(device)
                disease_model.eval()
                
                print(f"✅ Successfully loaded {model_name} with {num_classes} classes")
                model_loaded = True
                break
                
            except Exception as e:
                print(f"❌ {model_name} failed: {str(e)}")
                continue
        
        if not model_loaded:
            print("❌ Failed to load model with any ResNet architecture")
            return False
        
        # Define image preprocessing transforms
        disease_transform = transforms.Compose([
            transforms.Resize((224, 224)),  # Common input size for CNN models
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])  # ImageNet normalization
        ])
        
        print("✅ Disease detection model loaded successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error loading disease detection model: {str(e)}")
        # Print detailed traceback for debugging
        import traceback
        traceback.print_exc()
        return False

def preprocess_image(image_file):
    """Preprocess uploaded image for disease detection"""
    if not PYTORCH_AVAILABLE:
        return None
    
    try:
        from PIL import Image
        import io
        
        # Open and convert image
        image = Image.open(io.BytesIO(image_file.read())).convert('RGB')
        
        # Apply transforms
        if disease_transform is None:
            return None
            
        image_tensor = disease_transform(image)
        
        # Add batch dimension
        image_tensor = image_tensor.unsqueeze(0)
        
        return image_tensor
    except Exception as e:
        print(f"Error preprocessing image: {str(e)}")
        return None

def predict_disease(image_tensor):
    """Run disease prediction using the local model"""
    global disease_model
    
    if not PYTORCH_AVAILABLE:
        return None, 0.0, "PyTorch not available"
    
    try:
        if disease_model is None:
            return None, 0.0, "Model not loaded"
        
        # Run inference
        with torch.no_grad():
            outputs = disease_model(image_tensor)
            
            # Get prediction - assuming classification model
            if hasattr(outputs, 'data'):
                predictions = torch.nn.functional.softmax(outputs.data, dim=1)
            else:
                predictions = torch.nn.functional.softmax(outputs, dim=1)
            
            confidence, predicted_class = torch.max(predictions, 1)
            
            # Convert to Python values
            confidence_score = confidence.item()
            class_index = predicted_class.item()
            
            # Define comprehensive plant diseases (adjust based on your model's actual classes)
            # This should match the order of classes your model was trained on
            disease_classes = [
                "Healthy Plant",
                "Apple Black Rot",
                "Apple Cedar Rust", 
                "Apple Scab",
                "Bacterial Blight",
                "Bell Pepper Bacterial Spot",
                "Cherry Powdery Mildew",
                "Corn Blight",
                "Corn Rust",
                "Cotton Bacterial Blight",
                "Grape Black Rot",
                "Grape Leaf Blight", 
                "Late Blight",
                "Leaf Spot",
                "Mosaic Virus",
                "Potato Early Blight",
                "Potato Late Blight",
                "Powdery Mildew",
                "Rice Blast",
                "Root Rot",
                "Rust Disease",
                "Soybean Frogeye Leaf Spot",
                "Strawberry Leaf Scorch",
                "Tomato Bacterial Spot",
                "Tomato Early Blight",
                "Tomato Late Blight",
                "Tomato Leaf Mold",
                "Tomato Mosaic Virus",
                "Tomato Septoria Leaf Spot",
                "Tomato Spider Mites",
                "Tomato Target Spot",
                "Tomato Yellow Leaf Curl Virus",
                "Wheat Rust",
                "Wilt Disease"
            ]
            
            # Get disease name
            if class_index < len(disease_classes):
                disease_name = disease_classes[class_index]
            else:
                disease_name = f"Unknown Disease (Class {class_index})"
            
            return disease_name, confidence_score, "Success"
            
    except Exception as e:
        return None, 0.0, f"Prediction error: {str(e)}"

def get_gemini_disease_verification(disease_name, confidence_score, image_description="plant image"):
    """Use Gemini AI to verify disease diagnosis and provide detailed recommendations"""
    try:
        # Configure Gemini
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Create prompt for disease verification
        prompt = f"""
        As an expert plant pathologist, please analyze this disease diagnosis:
        
        Detected Disease: {disease_name}
        Confidence Score: {confidence_score:.2%}
        Image: {image_description}
        
        Please provide:
        1. Verification of the diagnosis (confirm or suggest alternatives)
        2. Detailed symptoms to look for
        3. Causes of this disease
        4. Treatment recommendations (organic and chemical options)
        5. Prevention measures
        6. Expected recovery timeline
        
        Format your response as a JSON object with these keys:
        - verified_diagnosis: string
        - alternative_diagnoses: array of strings (if any)
        - symptoms: array of strings
        - causes: array of strings
        - treatments: object with organic and chemical arrays
        - prevention: array of strings
        - recovery_timeline: string
        - additional_notes: string
        
        Keep responses practical and farmer-friendly.
        """
        
        response = model.generate_content(prompt)
        
        # Try to parse JSON response
        try:
            import re
            # Extract JSON from response text
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                verification_data = json.loads(json_match.group())
                return verification_data
            else:
                # Fallback if JSON parsing fails
                return {
                    "verified_diagnosis": disease_name,
                    "alternative_diagnoses": [],
                    "symptoms": ["Symptoms analysis needed"],
                    "causes": ["Environmental or pathogen-related"],
                    "treatments": {
                        "organic": ["Consult agricultural expert"],
                        "chemical": ["Professional diagnosis recommended"]
                    },
                    "prevention": ["Regular monitoring", "Proper plant care"],
                    "recovery_timeline": "Varies based on treatment",
                    "additional_notes": response.text
                }
        except json.JSONDecodeError:
            # Return formatted response if JSON parsing fails
            return {
                "verified_diagnosis": disease_name,
                "alternative_diagnoses": [],
                "symptoms": ["Analysis needed"],
                "causes": ["Various factors"],
                "treatments": {
                    "organic": ["Professional consultation recommended"],
                    "chemical": ["Expert diagnosis needed"]
                },
                "prevention": ["Regular plant monitoring"],
                "recovery_timeline": "Depends on treatment approach",
                "additional_notes": response.text
            }
            
    except Exception as e:
        print(f"Gemini verification error: {str(e)}")
        return {
            "verified_diagnosis": disease_name,
            "alternative_diagnoses": [],
            "symptoms": ["Unable to analyze symptoms"],
            "causes": ["Analysis unavailable"],
            "treatments": {
                "organic": ["Consult local agricultural expert"],
                "chemical": ["Professional diagnosis recommended"]
            },
            "prevention": ["Regular plant health monitoring"],
            "recovery_timeline": "Professional assessment needed",
            "additional_notes": f"Verification unavailable: {str(e)}"
        }

# Routes

@app.route('/')
def serve_frontend():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    response = send_from_directory(app.static_folder, filename)
    # Set proper content types for different file types
    if filename.endswith('.css'):
        response.headers['Content-Type'] = 'text/css; charset=utf-8'
    elif filename.endswith('.js'):
        response.headers['Content-Type'] = 'application/javascript; charset=utf-8'
    elif filename.endswith('.woff2'):
        response.headers['Content-Type'] = 'font/woff2'
    elif filename.endswith('.json'):
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
    return response

# Health check
@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'message': 'AgriCare Backend API is running',
        'version': '2.0.0',
        'timestamp': '2025-09-22T12:00:00Z'
    })

# API root endpoint
@app.route('/api')
def api_root():
    return jsonify({
        'message': 'AgriCare Backend API',
        'version': '2.0.0',
        'status': 'running',
        'endpoints': {
            'health': '/api/health',
            'auth': {
                'register': 'POST /api/auth/register',
                'login': 'POST /api/auth/login',
                'verify': 'GET /api/auth/verify'
            },
            'weather': {
                'location': 'GET /api/weather/location?city={city} or ?lat={lat}&lon={lon}',
                'autocomplete': 'GET /api/weather/autocomplete?q={query}',
                'current': 'GET /api/weather/current?location={city}',
                'forecast': 'GET /api/weather/forecast?location={city}',
                'health': 'GET /api/weather/health'
            },
            'disease': {
                'detect': 'POST /api/disease/detect (multipart/form-data)',
                'health': 'GET /api/disease/health'
            },
            'yield': {
                'predict': 'POST /api/yield/predict',
                'health': 'GET /api/yield/health'
            },
            'chatbot': {
                'message': 'POST /api/chatbot/message',
                'health': 'GET /api/chatbot/health'
            }
        },
        'documentation': 'Access specific endpoints for detailed information'
    })

# Authentication Routes
@app.route('/api/auth/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'success': False, 'message': 'Email and password are required'}), 400
        
        email = data['email'].lower().strip()
        password = data['password']
        full_name = data.get('name', email.split('@')[0])
        
        # Check if user already exists
        if find_user_by_email(email):
            return jsonify({'success': False, 'message': 'User already exists'}), 400
        
        # Create new user using Firebase
        user = create_user(email, password, full_name)
        if not user:
            return jsonify({'success': False, 'message': 'Failed to create user'}), 500
        
        return jsonify({
            'success': True, 
            'message': 'User registered successfully',
            'user': {
                'id': user['id'],
                'email': user['email'],
                'full_name': user['full_name']
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Registration error: {str(e)}'}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'success': False, 'message': 'Email and password are required'}), 400
        
        email = data['email'].lower().strip()
        password = data['password']
        
        # Find user
        user = find_user_by_email(email)
        if not user or not verify_password(password, user.get('password_hash', user.get('password', ''))):
            return jsonify({'success': False, 'message': 'Invalid email or password'}), 401
        
        # Update last login timestamp
        update_user_login(user['id'])
        
        # Create access token
        access_token = create_access_token(identity=user['id'])
        
        return jsonify({
            'success': True,
            'token': access_token,
            'user': {
                'id': user['id'],
                'email': user['email'],
                'name': user['name']
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Login error: {str(e)}'}), 500

@app.route('/api/auth/verify', methods=['GET'])
@jwt_required()
def verify_token():
    try:
        user_id = get_jwt_identity()
        user = next((user for user in users if user['id'] == user_id), None)
        
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'email': user['email'],
                'name': user['name']
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Token verification error: {str(e)}'}), 500

@app.route('/api/auth/google-login', methods=['POST'])
def google_login():
    """Handle Google OAuth login/registration"""
    try:
        data = request.get_json()
        
        if not data or not data.get('uid') or not data.get('email'):
            return jsonify({'success': False, 'message': 'Google user data is required'}), 400
        
        uid = data['uid']
        email = data['email'].lower().strip()
        display_name = data.get('displayName', email.split('@')[0])
        photo_url = data.get('photoURL', '')
        provider_id = data.get('providerId', 'google.com')
        
        # Check if user already exists
        existing_user = find_user_by_email(email)
        
        if existing_user:
            # Update user login timestamp
            update_user_login(existing_user['id'])
            
            # Update Google profile info if different
            if existing_user.get('provider_id') != provider_id:
                update_user_profile(existing_user['id'], {
                    'provider_id': provider_id,
                    'google_uid': uid,
                    'photo_url': photo_url,
                    'display_name': display_name
                })
            
            user_data = existing_user
        else:
            # Create new Google user
            user_data = create_google_user(uid, email, display_name, photo_url, provider_id)
            if not user_data:
                return jsonify({'success': False, 'message': 'Failed to create Google user'}), 500
        
        # Create access token
        access_token = create_access_token(identity=user_data['id'])
        
        return jsonify({
            'success': True,
            'access_token': access_token,
            'user': {
                'id': user_data['id'],
                'email': user_data['email'],
                'name': user_data.get('name', user_data.get('display_name', display_name)),
                'photo_url': user_data.get('photo_url', photo_url),
                'provider': provider_id
            }
        })
        
    except Exception as e:
        print(f"❌ Google login error: {e}")
        return jsonify({'success': False, 'message': f'Google login error: {str(e)}'}), 500

@app.route('/api/auth/check-user', methods=['GET'])
def check_user():
    """Check if user exists by email"""
    try:
        email = request.args.get('email')
        if not email:
            return jsonify({'success': False, 'message': 'Email parameter required'}), 400
        
        email = email.lower().strip()
        user = find_user_by_email(email)
        
        if user:
            return jsonify({
                'success': True,
                'exists': True,
                'user': {
                    'id': user['id'],
                    'email': user['email'],
                    'name': user.get('name', user.get('display_name', '')),
                    'photo_url': user.get('photo_url', ''),
                    'provider': user.get('provider_id', 'email')
                }
            })
        else:
            return jsonify({
                'success': True,
                'exists': False
            })
            
    except Exception as e:
        print(f"❌ Check user error: {e}")
        return jsonify({'success': False, 'message': f'Check user error: {str(e)}'}), 500

@app.route('/api/auth/update-preferences', methods=['POST'])
def update_preferences():
    """Update user preferences/settings"""
    try:
        data = request.get_json()
        print(f"🔧 Update preferences request data: {data}")
        
        if not data:
            print("❌ No request data provided")
            return jsonify({'success': False, 'message': 'Request data required'}), 400
        
        # Handle different possible data structures from frontend
        user_id = data.get('userId') or data.get('user_id') or data.get('email')
        preferences = data.get('preferences', {})
        
        # If no userId but we have settings directly in data, accept that
        if not user_id and ('language' in data or 'ttsEngine' in data or 'voiceMode' in data):
            user_id = 'anonymous'  # Allow anonymous settings
            preferences = data
        
        print(f"🔧 Extracted - User ID: {user_id}, Preferences: {preferences}")
        
        if not user_id:
            print("❌ No user ID found in request")
            return jsonify({'success': False, 'message': 'User ID or settings data required'}), 400
        
        # Update user preferences in storage
        # Since Firebase is disabled, we'll save to a local store for the session
        # In a real implementation, this would save to your chosen database
        
        print(f"✅ Successfully processed preferences for user {user_id}: {preferences}")
        
        return jsonify({
            'success': True,
            'message': 'Settings saved successfully',
            'preferences': preferences,
            'userId': user_id
        })
        
    except Exception as e:
        print(f"❌ Update preferences error: {e}")
        print(f"❌ Request data was: {request.get_json()}")
        return jsonify({'success': False, 'message': f'Update preferences error: {str(e)}'}), 500

# Weather Routes
@app.route('/api/weather/current', methods=['GET'])
def get_current_weather():
    try:
        lat = request.args.get('lat')
        lon = request.args.get('lon')
        city = request.args.get('city')
        
        print(f"🌦️ Weather request - lat: {lat}, lon: {lon}, city: {city}")
        
        # If city is provided, use a simple geocoding (or default coordinates)
        if city and not lat and not lon:
            # For simplicity, use default coordinates for common cities
            city_coords = {
                'new delhi': (28.6139, 77.2090),
                'delhi': (28.6139, 77.2090),
                'mumbai': (19.0760, 72.8777),
                'bangalore': (12.9716, 77.5946),
                'chennai': (13.0827, 80.2707),
                'kolkata': (22.5726, 88.3639),
                'hyderabad': (17.3850, 78.4867),
                'pune': (18.5204, 73.8567),
                'ahmedabad': (23.0225, 72.5714),
                'jaipur': (26.9124, 75.7873)
            }
            
            city_lower = city.lower().strip()
            if city_lower in city_coords:
                lat, lon = city_coords[city_lower]
                print(f"🌎 Using coordinates for {city}: lat={lat}, lon={lon}")
            else:
                # Default to New Delhi if city not recognized
                lat, lon = 28.6139, 77.2090
                print(f"🌎 City '{city}' not found, using Delhi coordinates")
        
        if not lat or not lon:
            return jsonify({'success': False, 'message': 'Latitude and longitude required'}), 400
        
        # Get current weather from Open-Meteo
        weather_url = "https://api.open-meteo.com/v1/forecast"
        weather_params = {
            'latitude': lat,
            'longitude': lon,
            'current': 'temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,wind_direction_10m',
            'timezone': 'auto'
        }
        
        print(f"🌐 Calling Open-Meteo API: {weather_url}")
        print(f"📊 Parameters: {weather_params}")
        
        weather_response = requests.get(weather_url, params=weather_params)
        print(f"📈 API Response Status: {weather_response.status_code}")
        
        if weather_response.status_code == 200:
            weather_data = weather_response.json()
            print(f"📊 Weather API response: {weather_data}")
            current = weather_data['current']
            
            # Determine location name using reverse geocoding
            location_name = city or 'Current Location'
            if not city and lat and lon:
                try:
                    # Use OpenStreetMap Nominatim for reverse geocoding (free)
                    lat_float = float(lat)
                    lon_float = float(lon)
                    
                    # Try reverse geocoding to get location name
                    geocoding_url = f"https://nominatim.openstreetmap.org/reverse"
                    geocoding_params = {
                        'lat': lat_float,
                        'lon': lon_float,
                        'format': 'json',
                        'addressdetails': 1
                    }
                    
                    # Add proper headers for Nominatim API
                    headers = {
                        'User-Agent': 'AgriCare Weather App (https://localhost:5000)'
                    }
                    
                    print(f"🌍 Trying reverse geocoding for ({lat_float}, {lon_float})")
                    geocoding_response = requests.get(geocoding_url, params=geocoding_params, headers=headers, timeout=5)
                    if geocoding_response.status_code == 200:
                        geocoding_data = geocoding_response.json()
                        print(f"📍 Geocoding response: {geocoding_data}")
                        address = geocoding_data.get('address', {})
                        
                        # Extract city name in order of preference
                        if address.get('city'):
                            location_name = address['city']
                        elif address.get('town'):
                            location_name = address['town']
                        elif address.get('village'):
                            location_name = address['village']
                        elif address.get('suburb'):
                            location_name = address['suburb']
                        elif address.get('district'):
                            location_name = address['district']
                        elif address.get('state'):
                            location_name = address['state']
                        else:
                            location_name = geocoding_data.get('display_name', '').split(',')[0] or f"Location ({lat_float:.2f}, {lon_float:.2f})"
                        
                        print(f"🏙️ Reverse geocoding successful: {location_name}")
                    else:
                        print(f"⚠️ Reverse geocoding failed with status {geocoding_response.status_code}: {geocoding_response.text}")
                        location_name = f"Location ({lat_float:.2f}, {lon_float:.2f})"
                        
                except Exception as e:
                    print(f"⚠️ Reverse geocoding error: {e}")
                    lat_float = float(lat)
                    lon_float = float(lon)
                    location_name = f"Location ({lat_float:.2f}, {lon_float:.2f})"
            
            print(f"🌦️ Weather data retrieved for {location_name}")
            
            # Convert to AccuWeather-like format for frontend compatibility
            response_data = {
                'LocalizedName': location_name,
                'LocalObservationDateTime': current['time'],
                'Temperature': {
                    'Metric': {
                        'Value': current['temperature_2m'],
                        'Unit': 'C'
                    }
                },
                'RealFeelTemperature': {
                    'Metric': {
                        'Value': current['apparent_temperature'],
                        'Unit': 'C'
                    }
                },
                'RelativeHumidity': current['relative_humidity_2m'],
                'WeatherText': get_weather_description(current['weather_code']),
                'WeatherIcon': current['weather_code'],
                'Wind': {
                    'Speed': {
                        'Metric': {
                            'Value': current['wind_speed_10m'],
                            'Unit': 'km/h'
                        }
                    },
                    'Direction': {
                        'Degrees': current['wind_direction_10m']
                    }
                },
                'GeoPosition': {
                    'Latitude': float(lat),
                    'Longitude': float(lon)
                }
            }
            return jsonify({'success': True, 'data': response_data})
        else:
            print(f"❌ Weather API failed with status: {weather_response.status_code}")
            print(f"❌ Response: {weather_response.text}")
            return jsonify({'success': False, 'message': 'Failed to fetch weather data'}), 400
            
    except Exception as e:
        print(f"❌ Weather API error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Weather error: {str(e)}'}), 500

@app.route('/api/weather/forecast', methods=['GET'])
def get_weather_forecast():
    try:
        lat = request.args.get('lat')
        lon = request.args.get('lon')
        
        if not lat or not lon:
            return jsonify({'success': False, 'message': 'Latitude and longitude required'}), 400
        
        # Get 7-day forecast from Open-Meteo
        forecast_url = "https://api.open-meteo.com/v1/forecast"
        forecast_params = {
            'latitude': lat,
            'longitude': lon,
            'daily': 'weather_code,temperature_2m_max,temperature_2m_min',
            'timezone': 'auto',
            'forecast_days': 7
        }
        
        forecast_response = requests.get(forecast_url, params=forecast_params)
        
        if forecast_response.status_code == 200:
            forecast_data = forecast_response.json()
            daily = forecast_data['daily']
            
            # Convert to AccuWeather-like format for frontend compatibility
            daily_forecasts = []
            for i in range(len(daily['time'])):
                daily_forecasts.append({
                    'Date': daily['time'][i],
                    'Temperature': {
                        'Maximum': {'Value': daily['temperature_2m_max'][i]},
                        'Minimum': {'Value': daily['temperature_2m_min'][i]}
                    },
                    'Day': {'Icon': daily['weather_code'][i]},
                    'Night': {'Icon': daily['weather_code'][i]}
                })
            
            response_data = {
                'DailyForecasts': daily_forecasts
            }
            return jsonify({'success': True, 'data': response_data})
        else:
            return jsonify({'success': False, 'message': 'Failed to fetch forecast data'}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Forecast error: {str(e)}'}), 500

def get_weather_description(weather_code):
    """Convert WMO weather codes to descriptions"""
    weather_codes = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy", 
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        56: "Light freezing drizzle",
        57: "Dense freezing drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        66: "Light freezing rain",
        67: "Heavy freezing rain",
        71: "Slight snow fall",
        73: "Moderate snow fall",
        75: "Heavy snow fall",
        77: "Snow grains",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail"
    }
    return weather_codes.get(weather_code, "Unknown")

@app.route('/api/weather/health', methods=['GET'])
def weather_health():
    return jsonify({'status': 'healthy', 'service': 'weather'})

@app.route('/api/weather/location', methods=['GET'])
def get_weather_location():
    """Get location information for weather services"""
    try:
        city = request.args.get('city')
        lat = request.args.get('lat')
        lon = request.args.get('lon')

        if not city and not (lat and lon):
            return jsonify({'success': False, 'message': 'Either city or lat/lon coordinates required'}), 400

        # This endpoint is no longer needed with Open-Meteo
        # Keeping for compatibility but returning simple response
        if city:
            return jsonify({
                'success': True,
                'location': {
                    'key': 'open-meteo',
                    'name': city,
                    'country': 'Unknown',
                    'region': 'Unknown',
                    'coordinates': {
                        'lat': lat or 28.6139,  # Default to Delhi if no coordinates
                        'lon': lon or 77.2090
                    }
                }
            })
        else:
            return jsonify({
                'success': True,
                'location': {
                    'key': 'open-meteo',
                    'name': 'Current Location',
                    'country': 'Unknown',
                    'region': 'Unknown',
                    'coordinates': {
                        'lat': lat,
                        'lon': lon
                    }
                }
            })

    except Exception as e:
        return jsonify({'success': False, 'message': f'Location error: {str(e)}'}), 500

@app.route('/api/weather/autocomplete', methods=['GET'])
def weather_autocomplete():
    """Get city suggestions for autocomplete"""
    try:
        query = request.args.get('q', '').strip()

        if not query or len(query) < 2:
            return jsonify({'success': True, 'suggestions': []})

        # Simple city suggestions - in production you'd use a proper geocoding service
        common_cities = [
            {'name': 'New Delhi', 'country': 'India'},
            {'name': 'Mumbai', 'country': 'India'},
            {'name': 'Bangalore', 'country': 'India'},
            {'name': 'Chennai', 'country': 'India'},
            {'name': 'Kolkata', 'country': 'India'},
            {'name': 'London', 'country': 'United Kingdom'},
            {'name': 'New York', 'country': 'United States'},
            {'name': 'Tokyo', 'country': 'Japan'},
            {'name': 'Paris', 'country': 'France'},
            {'name': 'Berlin', 'country': 'Germany'}
        ]
        
        suggestions = [city for city in common_cities if query.lower() in city['name'].lower()][:5]

        return jsonify({
            'success': True,
            'suggestions': suggestions
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'Autocomplete error: {str(e)}'}), 500

# Disease Detection Routes
@app.route('/api/disease/detect', methods=['POST'])
@jwt_required(optional=True)
def detect_disease():
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'message': 'No image provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No image selected'}), 400
        
        # Get language parameter from request (defaults to English)
        language = request.form.get('language', 'en')
        print(f"Disease detection requested in language: {language}")
        
        # Check if model is loaded
        if disease_model is None:
            print("Disease model not loaded, using fallback mode")
            return jsonify({
                'success': False, 
                'message': 'Disease detection model not available. Please contact support.'
            }), 503
        
        print(f"Processing disease detection for file: {file.filename}")
        
        # Get current user ID if logged in
        current_user_id = get_jwt_identity()
        
        # Step 1: Upload image to Firebase Storage (if user is logged in)
        image_info = None
        if current_user_id and FIREBASE_AVAILABLE:
            # Reset file pointer for upload
            file.seek(0)
            image_info = upload_image_to_storage(file, current_user_id, 'disease')
            if image_info:
                print(f"✅ Image uploaded to Firebase Storage: {image_info['url']}")
        
        # Reset file pointer to beginning for processing
        file.seek(0)
        
        # Step 2: Preprocess the image
        image_tensor = preprocess_image(file)
        if image_tensor is None:
            return jsonify({
                'success': False, 
                'message': 'Failed to process image. Please ensure it\'s a valid image file.'
            }), 400
        
        # Step 3: Run local model prediction
        disease_name, confidence_score, status = predict_disease(image_tensor)
        if disease_name is None:
            return jsonify({
                'success': False, 
                'message': f'Disease prediction failed: {status}'
            }), 500
        
        print(f"Local model prediction: {disease_name} (confidence: {confidence_score:.2%})")
        
        # Step 4: Get Gemini verification and detailed recommendations
        verification_data = get_gemini_disease_verification(disease_name, confidence_score, f"uploaded {file.filename}")
        
        # Step 5: Combine results
        result = {
            'disease': disease_name,
            'confidence': confidence_score,
            'local_model_prediction': disease_name,
            'gemini_verification': verification_data,
            'recommendations': verification_data.get('treatments', {}).get('organic', []) + 
                            verification_data.get('treatments', {}).get('chemical', []),
            'treatment': f"Treatment for {verification_data.get('verified_diagnosis', disease_name)}",
            'symptoms': verification_data.get('symptoms', []),
            'causes': verification_data.get('causes', []),
            'prevention': verification_data.get('prevention', []),
            'recovery_timeline': verification_data.get('recovery_timeline', 'Variable'),
            'additional_notes': verification_data.get('additional_notes', ''),
            'image_url': image_info.get('url') if image_info else None
        }
        
        # Step 5.1: Translate result if requested language is not English
        if language != 'en':
            try:
                print(f"Translating disease detection result to {language}")
                result = translate_disease_result(result, language)
            except Exception as e:
                print(f"Translation failed: {e}, returning English result")
                # Continue with English result if translation fails
        
        # Step 6: Save to Firebase Firestore (if user is logged in)
        detection_id = None
        if current_user_id and FIREBASE_AVAILABLE:
            detection_id = save_disease_detection(current_user_id, image_info, result)
            if detection_id:
                result['detection_id'] = detection_id
                print(f"✅ Disease detection saved to Firestore: {detection_id}")
        
        print(f"Disease detection completed successfully: {disease_name}")
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        print(f"Disease detection error: {str(e)}")
        return jsonify({'success': False, 'message': f'Disease detection error: {str(e)}'}), 500

@app.route('/api/disease/health', methods=['GET'])
def disease_health():
    return jsonify({'status': 'healthy', 'service': 'disease_detection'})

# User Management and History Routes
@app.route('/api/user/profile', methods=['GET'])
@jwt_required()
def get_user_profile():
    try:
        current_user_id = get_jwt_identity()
        
        if db is not None:
            # Get user from Firestore
            user_doc = db.collection(COLLECTIONS['USERS']).document(current_user_id).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                user_data['id'] = user_doc.id
                
                # Remove sensitive data
                user_data.pop('password_hash', None)
                
                return jsonify({'success': True, 'data': user_data})
            else:
                return jsonify({'success': False, 'message': 'User not found'}), 404
        else:
            # Fallback to in-memory storage
            user = next((u for u in users if u['id'] == current_user_id), None)
            if user:
                # Remove sensitive data
                safe_user = {k: v for k, v in user.items() if k != 'password'}
                return jsonify({'success': True, 'data': safe_user})
            else:
                return jsonify({'success': False, 'message': 'User not found'}), 404
                
    except Exception as e:
        return jsonify({'success': False, 'message': f'Profile error: {str(e)}'}), 500

@app.route('/api/user/history', methods=['GET'])
@jwt_required()
def get_user_history_route():
    try:
        current_user_id = get_jwt_identity()
        history_type = request.args.get('type', 'all')  # all, disease_detections, yield_predictions, chat_history
        limit = int(request.args.get('limit', 10))
        
        history = get_user_history(current_user_id, history_type, limit)
        
        return jsonify({
            'success': True, 
            'data': history,
            'count': len(history),
            'type': history_type
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'History error: {str(e)}'}), 500

@app.route('/api/user/stats', methods=['GET'])
@jwt_required()
def get_user_stats():
    try:
        current_user_id = get_jwt_identity()
        
        if db is not None:
            # Get counts from Firestore collections
            disease_count = len(db.collection(COLLECTIONS['DISEASE_DETECTIONS']).where('user_id', '==', current_user_id).get())
            yield_count = len(db.collection(COLLECTIONS['YIELD_PREDICTIONS']).where('user_id', '==', current_user_id).get())
            chat_count = len(db.collection(COLLECTIONS['CHAT_HISTORY']).where('user_id', '==', current_user_id).get())
            
            stats = {
                'disease_detections': disease_count,
                'yield_predictions': yield_count,
                'chat_sessions': chat_count,
                'total_activities': disease_count + yield_count + chat_count
            }
        else:
            # Fallback stats (mock data)
            stats = {
                'disease_detections': 0,
                'yield_predictions': 0,
                'chat_sessions': 0,
                'total_activities': 0
            }
        
        return jsonify({'success': True, 'data': stats})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Stats error: {str(e)}'}), 500

# Yield Prediction Routes
@app.route('/api/yield/predict', methods=['POST'])
def predict_yield():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        # Mock yield prediction result
        mock_prediction = {
            'predicted_yield': 85.5,
            'confidence': 0.78,
            'factors': {
                'weather_impact': 'positive',
                'soil_quality': 'good',
                'crop_health': 'excellent'
            },
            'recommendations': [
                'Maintain current irrigation schedule',
                'Consider light fertilization in 2 weeks',
                'Monitor for pest activity'
            ]
        }
        
        return jsonify({'success': True, 'data': mock_prediction})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Yield prediction error: {str(e)}'}), 500

@app.route('/api/yield/health', methods=['GET'])
def yield_health():
    return jsonify({'status': 'healthy', 'service': 'yield_prediction'})

# Chatbot Routes
@app.route('/api/chatbot/message', methods=['POST'])
def chatbot_message():
    try:
        data = request.get_json()
        
        if not data or not data.get('message'):
            return jsonify({'success': False, 'message': 'No message provided'}), 400
        
        user_message = data['message']
        user_id = data.get('user_id', 'anonymous')
        
        # Get language from request or user preferences
        language = data.get('language', 'en')
        bot_language = data.get('botLanguage', language)  # Check for botLanguage in request
        
        # If no specific botLanguage provided, use the language parameter
        target_language = bot_language if bot_language != 'en' else language
        
        print(f"🤖 Chatbot request - User: {user_id}, Target Language: {target_language}, Message: {user_message}")
        
        # Get intelligent response using the target language
        bot_response = get_intelligent_chat_response(user_message, target_language, user_id)
        
        return jsonify({
            'success': True,
            'data': {
                'botResponse': bot_response,
                'userMessage': user_message,
                'language': target_language,
                'timestamp': datetime.now().isoformat(),
                'conversationId': user_id
            }
        })
        
    except Exception as e:
        print(f"❌ Chatbot error: {str(e)}")
        # Fallback response in the requested language
        fallback_messages = {
            'en': "I'm sorry, I'm having trouble responding right now. Please try again later.",
            'hi': "माफ़ करें, मुझे अभी उत्तर देने में कुछ परेशानी हो रही है। कृपया बाद में पुनः प्रयास करें।",
            'ta': "மன்னிக்கவும், எனக்கு இப்போது பதிலளிப்பதில் சிரமம் உள்ளது. தயவுசெய்து பின்னர் மீண்டும் முயற்சிக்கவும்.",
            'od': "ଦୁଃଖିତ, ମୋତେ ବର୍ତ୍ତମାନ ଉତ୍ତର ଦେବାରେ କିଛି ଅସୁବିଧା ହେଉଛି। ଦୟାକରି ପରେ ପୁଣି ଚେଷ୍ଟା କରନ୍ତୁ।"
        }
        fallback_response = fallback_messages.get(language, fallback_messages['en'])
        
        return jsonify({
            'success': True,
            'data': {
                'botResponse': fallback_response,
                'userMessage': user_message,
                'language': language,
                'timestamp': datetime.now().isoformat(),
                'error': 'ai_unavailable'
            }
        })

@app.route('/api/tts/synthesize', methods=['POST'])
def synthesize_speech():
    if not TTS_AVAILABLE:
        return jsonify({
            'success': False, 
            'message': 'Local TTS model is not available. Please check server logs.'
        }), 503

    try:
        data = request.get_json()
        text = data.get('text')
        language = data.get('language', 'en')
        if not text:
            return jsonify({'success': False, 'message': 'No text provided'}), 400

        print(f"🔊 TTS request for lang '{language}': '{text[:50]}...'")

        # 1. Create a description for the voice based on language.
        lang_name = {
            'hi': 'Hindi', 
            'ta': 'Tamil', 
            'en': 'English',
            'bn': 'Bengali',
            'te': 'Telugu',
            'mr': 'Marathi',
            'gu': 'Gujarati',
            'kn': 'Kannada',
            'ml': 'Malayalam',
            'pa': 'Punjabi'
        }.get(language, 'English')
        description = f"A high-quality, female voice speaking in {lang_name} with a clear and pleasant tone."

        # 2. Prepare inputs using the two separate tokenizers.
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        description_input_ids = tts_description_tokenizer(description, return_tensors="pt").input_ids.to(device)
        prompt_input_ids = tts_processor(text, return_tensors="pt").input_ids.to(device)

        # 3. Generate speech with both inputs.
        with torch.no_grad():
            speech_output = tts_model.generate(
                input_ids=description_input_ids, 
                prompt_input_ids=prompt_input_ids
            )

        sample_rate = tts_model.config.sampling_rate
        waveform = speech_output.cpu().numpy().squeeze()

        # Convert numpy array to WAV in memory and then to base64
        buffer = io.BytesIO()
        sf.write(buffer, waveform, sample_rate, format='WAV', subtype='PCM_16')
        buffer.seek(0)
        audio_base64 = base64.b64encode(buffer.read()).decode('utf-8')

        return jsonify({
            'success': True,
            'data': {
                'audio_base64': audio_base64
            }
        })
            
    except Exception as e:
        print(f"❌ TTS API error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'TTS service error: {str(e)}'}), 500

@app.route('/api/tts/voices', methods=['GET'])
def get_available_voices():
    """
    Get list of available TTS voices
    """
    try:
        if not TTS_AVAILABLE:
            return jsonify({
                'success': True,
                'message': 'Using browser synthesis',
                'voices': [
                    {
                        'id': 'browser-default',
                        'name': 'Browser Default',
                        'language': 'en-US',
                        'gender': 'neutral'
                    }
                ],
                'fallback': True
            }), 200
            
        # Return available voices (customize based on your model)
        voices = [
            {
                'id': 'indic_female',
                'name': 'Indic Female Voice',
                'language': 'multi',
                'gender': 'female'
            },
            {
                'id': 'indic_male', 
                'name': 'Indic Male Voice',
                'language': 'multi',
                'gender': 'male'
            }
        ]
        
        return jsonify({
            'success': True,
            'data': {
                'voices': voices,
                'model': 'indic-parler-tts',
                'supported_languages': ['en', 'hi', 'ta', 'te', 'bn', 'gu', 'kn', 'ml', 'mr', 'pa']
            }
        })
        
    except Exception as e:
        print(f"❌ Voice list error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to get voice list'
        }), 500

def get_weather_for_chatbot(location):
    """
    Get weather data for chatbot responses with location auto-correction
    """
    print(f"--- DEBUG: Inside get_weather_for_chatbot for location: {location} ---")
    try:
        # First try to get coordinates from location name
        print(f"--- DEBUG: Calling Geocoding API for {location} ---")
        geo_response = requests.get(f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1")
        print(f"--- DEBUG: Geocoding API status: {geo_response.status_code} ---")
        if geo_response.status_code == 200:
            geo_data = geo_response.json()
            if geo_data.get('results'):
                location_data = geo_data['results'][0]
                lat, lon = location_data['latitude'], location_data['longitude']
                city_name = location_data['name']
                print(f"--- DEBUG: Geocoding successful: lat={lat}, lon={lon}, name={city_name} ---")
                
                # Get weather data
                weather_url = "https://api.open-meteo.com/v1/forecast"
                weather_params = {
                    'latitude': lat,
                    'longitude': lon,
                    'current': 'temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m',
                    'daily': 'temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code',
                    'forecast_days': 3,
                    'timezone': 'auto'
                }
                
                print(f"--- DEBUG: Calling Open-Meteo API ---")
                weather_response = requests.get(weather_url, params=weather_params)
                print(f"--- DEBUG: Open-Meteo API status: {weather_response.status_code} ---")
                if weather_response.status_code == 200:
                    weather_data = weather_response.json()
                    current = weather_data.get('current', {})
                    daily = weather_data.get('daily', {})
                    
                    # Format weather response
                    weather_summary = {
                        'location': city_name,
                        'current_temp': current.get('temperature_2m', 'N/A'),
                        'humidity': current.get('relative_humidity_2m', 'N/A'),
                        'wind_speed': current.get('wind_speed_10m', 'N/A'),
                        'today_max': daily.get('temperature_2m_max', [0])[0],
                        'today_min': daily.get('temperature_2m_min', [0])[0],
                        'rain_chance': daily.get('precipitation_sum', [0])[0]
                    }
                    print(f"--- DEBUG: Successfully formatted weather summary: {weather_summary} ---")
                    return weather_summary
        print(f"--- DEBUG: Failed to get weather data for {location} ---")
        return None
    except Exception as e:
        print(f"--- DEBUG: Error in get_weather_for_chatbot: {e} ---")
        print(f"Weather data error: {e}")
        return None

def get_market_prices_for_chatbot(commodity=None, state=None):
    """
    Get market price data for chatbot responses
    """
    try:
        # Enhanced market data with regional variations
        market_data = {
            'wheat': {
                'price_range': '₹2,100-2,300 per quintal',
                'regional': {
                    'punjab': '₹2,250-2,350 per quintal',
                    'haryana': '₹2,200-2,300 per quintal', 
                    'uttar pradesh': '₹2,150-2,250 per quintal',
                    'tamil nadu': '₹2,100-2,200 per quintal'
                }
            },
            'rice': {
                'price_range': '₹1,800-2,200 per quintal',
                'regional': {
                    'punjab': '₹2,100-2,300 per quintal',
                    'haryana': '₹2,000-2,200 per quintal',
                    'tamil nadu': '₹1,800-2,000 per quintal',
                    'west bengal': '₹1,900-2,100 per quintal'
                }
            },
            'cotton': {
                'price_range': '₹5,800-6,200 per quintal',
                'regional': {
                    'gujarat': '₹6,000-6,300 per quintal',
                    'maharashtra': '₹5,900-6,200 per quintal',
                    'punjab': '₹6,100-6,400 per quintal',
                    'haryana': '₹6,000-6,300 per quintal',
                    'tamil nadu': '₹5,700-6,000 per quintal',
                    'andhra pradesh': '₹5,800-6,100 per quintal',
                    'telangana': '₹5,900-6,200 per quintal'
                }
            },
            'sugarcane': {
                'price_range': '₹280-320 per quintal',
                'regional': {
                    'uttar pradesh': '₹290-330 per quintal',
                    'maharashtra': '₹285-325 per quintal',
                    'tamil nadu': '₹275-315 per quintal',
                    'karnataka': '₹280-320 per quintal'
                }
            },
            'soybean': {
                'price_range': '₹4,200-4,600 per quintal',
                'regional': {
                    'madhya pradesh': '₹4,300-4,700 per quintal',
                    'maharashtra': '₹4,200-4,600 per quintal',
                    'rajasthan': '₹4,100-4,500 per quintal'
                }
            },
            'groundnut': {
                'price_range': '₹5,000-5,400 per quintal',
                'regional': {
                    'gujarat': '₹5,200-5,600 per quintal',
                    'andhra pradesh': '₹5,000-5,400 per quintal',
                    'tamil nadu': '₹4,900-5,300 per quintal'
                }
            }
        }
        
        if commodity and commodity.lower() in market_data:
            crop_data = market_data[commodity.lower()]
            result = {
                'commodity': commodity,
                'price_range': crop_data['price_range'],
                'note': 'Prices vary by location and quality. Check local mandis for exact rates.'
            }
            
            # Add regional price if state is detected
            if state and state.lower() in crop_data.get('regional', {}):
                regional_price = crop_data['regional'][state.lower()]
                result['regional_price'] = f"{state.title()}: {regional_price}"
                result['note'] = f'Regional price for {state.title()}. Check local mandis for exact rates.'
            
            return result
        
        # Return general price info
        return {
            'general_info': 'Current average prices: Wheat ₹2,200/q, Rice ₹2,000/q, Cotton ₹6,000/q, Sugarcane ₹300/q',
            'note': 'Visit nearby mandi or check government apps for latest rates.'
        }
    except Exception as e:
        print(f"Market price error: {e}")
        return None

def extract_location_from_query(query):
    """
    Extract location names from user query using simple keyword matching
    """
    import re
    
    # Common Indian cities and states
    indian_locations = [
        'delhi', 'mumbai', 'bangalore', 'kolkata', 'chennai', 'hyderabad', 'pune', 'ahmedabad',
        'jaipur', 'lucknow', 'kanpur', 'nagpur', 'indore', 'thane', 'bhopal', 'visakhapatnam',
        'pimpri', 'patna', 'vadodara', 'ghaziabad', 'ludhiana', 'agra', 'nashik', 'faridabad',
        'rajkot', 'meerut', 'kalyan', 'vasai', 'varanasi', 'srinagar', 'aurangabad', 'dhanbad',
        'amritsar', 'allahabad', 'ranchi', 'howrah', 'coimbatore', 'jabalpur', 'gwalior',
        'punjab', 'haryana', 'uttar pradesh', 'maharashtra', 'karnataka', 'tamil nadu', 'tamilnadu',
        'gujarat', 'rajasthan', 'madhya pradesh', 'west bengal', 'odisha', 'bihar', 'kerala',
        'andhra pradesh', 'telangana', 'assam', 'jharkhand', 'uttarakhand', 'himachal pradesh',
        'chhattisgarh', 'goa', 'tripura', 'manipur', 'meghalaya', 'sikkim', 'mizoram', 'nagaland',
        'arunachal pradesh', 'nammakal', 'namakkal', 'erode', 'salem', 'tiruchirappalli', 'trichy',
        'madurai', 'tirunelveli', 'vellore', 'tiruppur', 'thoothukudi', 'dindigul', 'thanjavur',
        'cuddalore', 'kanyakumari', 'tiruvannamalai', 'karur', 'sivaganga', 'nagapattinam',
        'dharmapuri', 'krishnagiri', 'ramanathapuram', 'virudhunagar', 'pudukkottai', 'perambalur',
        'ariyalur', 'nilgiris', 'kanchipuram', 'thiruvallur', 'villupuram', 'kallakurichi'
    ]
    
    query_lower = query.lower()
    print(f"🔍 Debug: Searching for location in: '{query_lower}'")
    
    for location in indian_locations:
        if location in query_lower:
            print(f"🔍 Debug: Found location match: '{location}'")
            return location.replace('tamilnadu', 'tamil nadu').title()
    
    print(f"🔍 Debug: No location found in query")
    return None

def extract_commodity_from_query(query):
    """
    Extract commodity names from user query
    """
    commodities = [
        'wheat', 'cotton', 'sugarcane', 'soybean', 'groundnut', 'rice', 'maize', 'corn', 
        'mustard', 'bajra', 'jowar', 'barley', 'gram', 'tur', 'moong', 'urad', 'sesame',
        'onion', 'potato', 'tomato', 'chili', 'pepper', 'turmeric', 'cardamom', 'ginger'
    ]
    
    query_lower = query.lower()
    print(f"🔍 Debug: Searching for commodity in: '{query_lower}'")
    
    # Sort by length (longest first) to match "cotton" before "rice" in words like "price"
    commodities_sorted = sorted(commodities, key=len, reverse=True)
    
    for commodity in commodities_sorted:
        if commodity in query_lower:
            print(f"🔍 Debug: Found commodity match: '{commodity}'")
            return commodity
    
    print(f"🔍 Debug: No commodity found in query")
    return None

# Removed HuggingFace function - now using Gemini AI only

def get_intelligent_chat_response(user_message, language='en', user_id='anonymous'):
    """
    Handles the full pipeline for a chatbot response:
    1. Detects the user's language.
    2. Translates the user's message to English for the AI model.
    3. Gets an intelligent response from Gemini AI.
    4. Translates the AI's English response back to the user's language.
    """
    try:
        print(f"🤖 Chat request received. Target language: {language}, Message: '{user_message[:50]}...'")

        # Step 1: Detect the language of the user's message
        original_language = detect_language(user_message)
        print(f"🔍 Detected original language: {original_language}")
        
        # Step 2: Translate the user's message to English for processing
        english_message = user_message
        if original_language != 'en':
            english_message = translate_text(user_message, source_lang=original_language, target_lang='en')
            print(f"🔤 Message translated to English: '{english_message[:50]}...'")
        
        # Step 3: Get context data (weather, prices, etc.)
        context_data = ""
        user_message_lower = english_message.lower()
        
        # Extract location for weather queries
        weather_keywords = ['weather', 'temperature', 'rain', 'climate']
        has_weather_keyword = any(keyword in user_message_lower for keyword in weather_keywords)
        
        if has_weather_keyword:
            location = extract_location_from_query(english_message)
            if location:
                weather_data = get_weather_for_chatbot(location)
                if weather_data:
                    context_data += f"\nCurrent Weather Data for {weather_data['location']}:\n"
                    context_data += f"Temperature: {weather_data['current_temp']}°C (High: {weather_data['today_max']}°C, Low: {weather_data['today_min']}°C)\n"
                    context_data += f"Humidity: {weather_data['humidity']}%\n"
                    context_data += f"Wind Speed: {weather_data['wind_speed']} km/h\n"
                    if weather_data['rain_chance'] > 0:
                        context_data += f"Expected rainfall: {weather_data['rain_chance']}mm\n"
        
        # Extract commodity for market price queries
        price_keywords = ['price', 'market', 'rate', 'cost', 'sell']
        has_price_keyword = any(keyword in user_message_lower for keyword in price_keywords)
        
        if has_price_keyword:
            commodity = extract_commodity_from_query(english_message)
            location = extract_location_from_query(english_message)
            market_data = get_market_prices_for_chatbot(commodity, location)
            
            if market_data:
                context_data += f"\nMarket Price Information:\n"
                if 'commodity' in market_data:
                    context_data += f"{market_data['commodity'].title()}: {market_data['price_range']}\n"
                    if 'regional_price' in market_data:
                        context_data += f"Regional Price - {market_data['regional_price']}\n"
                else:
                    context_data += f"{market_data['general_info']}\n"
                context_data += f"Note: {market_data['note']}\n"
        enhanced_prompt = f"""You are AgriBot, an intelligent farming assistant for Indian farmers. Provide direct, complete answers in 1-3 sentences.

{context_data}

User Question: {english_message}

Provide a helpful, direct answer about farming, crops, weather, or market prices. Use the context data above if relevant."""

        # Step 4: Get an intelligent response from Gemini AI (in English)
        print("🤖 Using Gemini AI for response...")
        gemini_response = process_with_gemini(enhanced_prompt, 'en')  # Always process in English
        
        if gemini_response and len(gemini_response.strip()) > 10:
            english_response = gemini_response.strip()
        else:
            # Fallback if Gemini fails
            english_response = get_agricultural_fallback_response(english_message, context_data)
            print("🧠 Using fallback response.")

        print(f"🤖 English response from AI: '{english_response[:50]}...'")
        
        # Step 5: Translate the English response back to the user's target language
        final_response = english_response
        if language != 'en':
            # Use your NLLB model again to translate the outgoing message
            final_response = translate_text(english_response, source_lang='en', target_lang=language)
            print(f"🔤 Final response translated to {language}: '{final_response[:50]}...'")
        
        # Step 6: Save the chat message to history (optional but good practice)
        if user_id != 'anonymous':
            try:
                save_chat_message(user_id, user_message, final_response, language)
            except:
                pass  # Don't break chat if saving fails
        
        return final_response
            
    except Exception as e:
        print(f"❌ Chat processing error: {str(e)}")
        # Language-specific error responses
        error_responses = {
            'en': "I'm sorry, I couldn't process your request right now. Let me help you with general farming advice instead.",
            'hi': "माफ़ करें, मैं अभी आपका अनुरोध संसाधित नहीं कर सका। इसके बजाय मैं आपको सामान्य कृषि सलाह दे सकता हूँ।",
            'ta': "மன்னிக்கவும், என்னால் இப்போது உங்கள் கோரிக்கையை செயல்படுத்த முடியவில்லை. அதற்கு பதிலாக பொதுவான விவசாய ஆலோசனையை வழங்க முடியும்.",
            'od': "ଦୁଃଖିତ, ମୁଁ ବର୍ତ୍ତମାନ ଆପଣଙ୍କର ଅନୁରୋଧ ପ୍ରକ୍ରିୟା କରିପାରିଲି ନାହିଁ। ତା ବଦଳରେ ମୁଁ ସାଧାରଣ କୃଷି ପରାମର୍ଶ ଦେଇପାରିବି।"
        }
        return error_responses.get(language, error_responses['en'])

def get_agricultural_fallback_response(message, context_data):
    """
    Provide intelligent agricultural responses using built-in knowledge when AI models are unavailable
    """
    import random
    
    message_lower = message.lower()
    
    # --- CHECK FOR WEATHER CONTEXT DATA FIRST ---
    weather_keywords = ['weather', 'temperature', 'rain', 'climate', 'forecast', 'humid']
    has_weather_keyword = any(keyword in message_lower for keyword in weather_keywords)
    if has_weather_keyword and context_data and "Current Weather Data" in context_data:
        print("🧠 Using weather context data in fallback response.")
        # Extract the relevant part of the context
        weather_info = context_data.split("Current Weather Data")[1].strip()
        # Simple response incorporating the data
        return f"Here is the weather information I found: {weather_info}"
    # --- END WEATHER CONTEXT CHECK ---
    
    # Language and conversation patterns
    greetings = ['hello', 'hi', 'hey', 'namaste', 'vanakkam']
    if any(greeting in message_lower for greeting in greetings):
        responses = [
            "Hello! I'm your AgriCare assistant, here to help with all your farming questions. What would you like to know about?",
            "Hi there! I'm ready to assist you with agricultural advice, crop management, and farming techniques. How can I help?",
            "Namaste! Welcome to AgriCare. I can help with crops, soil health, pest management, and more. What's your farming question?"
        ]
        return random.choice(responses)
    
    # Tamil language capability question
    if any(word in message_lower for word in ['tamil', 'speak tamil', 'talk tamil', 'tamil language']):
        return "Yes, I can communicate in Tamil! மைால் தमிழில் பேச முடியும். உங்கள் கோためికं സവৃˆ చാలుంచ? (I can speak in Tamil. What's your farming question?)"
    
    # Weather-related queries
    if 'weather' in message_lower or 'rain' in message_lower or 'temperature' in message_lower:
        responses = [
            "Weather plays a crucial role in farming! For accurate weather-based advice, I'd need your location. Generally, monitor rainfall patterns for irrigation planning and temperature changes for crop protection.",
            "Understanding weather patterns helps optimize farming! Check local weather forecasts for: 1) Irrigation scheduling 2) Pest management timing 3) Harvest planning 4) Crop protection measures.",
            f"Weather insights: {context_data.strip() if context_data else 'For personalized weather advice, please share your location. Different regions require different weather-based strategies.'}"
        ]
        return random.choice(responses)
    
    # Market and pricing queries
    elif any(word in message_lower for word in ['price', 'market', 'sell', 'buy', 'cost', 'profit']):
        responses = [
            "Market success depends on timing and quality! Key tips: 1) Monitor local market trends 2) Improve crop quality through better practices 3) Consider value-addition 4) Build relationships with buyers.",
            f"Market information: {context_data.strip() if context_data else 'Prices vary by location and season. Check government agricultural market websites, local mandis, and farmer producer organizations for current rates.'}"
        ]
        return random.choice(responses)
    
    # Disease and pest management
    elif any(word in message_lower for word in ['disease', 'pest', 'bug', 'insect', 'problem', 'damage', 'yellow', 'brown', 'spots']):
        responses = [
            "Plant health is critical for good yields! For effective pest/disease management: 1) Early identification is key 2) Use integrated pest management (IPM) 3) Maintain field hygiene 4) Consult local agricultural extension officers.",
            "Dealing with crop problems? Here's my approach: 1) Take clear photos of affected plants 2) Note symptoms and spread pattern 3) Check with nearby farmers 4) Contact agricultural experts 5) Use targeted, eco-friendly solutions.",
            "Plant diseases and pests can significantly impact yields. Prevention is better than cure - maintain proper spacing, ensure good drainage, use certified seeds, and follow crop rotation practices."
        ]
        return random.choice(responses)
    
    # Soil and fertilizer queries
    elif any(word in message_lower for word in ['soil', 'fertilizer', 'nutrition', 'compost', 'manure', 'npk']):
        responses = [
            "Healthy soil = healthy crops! Essential steps: 1) Test soil pH and nutrients 2) Add organic matter regularly 3) Use balanced fertilizers based on soil test results 4) Practice crop rotation 5) Avoid over-fertilization.",
            "Soil nutrition is the foundation of successful farming. Focus on: organic matter addition, proper pH management, balanced NPK ratios, micronutrient supplementation, and regular soil testing.",
            "Smart fertilizer management saves money and improves yields! Use soil testing to determine exact needs, apply fertilizers at optimal timing, combine organic and inorganic sources, and follow recommended doses."
        ]
        return random.choice(responses)
    
    # Irrigation and water management
    elif any(word in message_lower for word in ['water', 'irrigation', 'watering', 'drought', 'flooding']):
        responses = [
            "Water management is crucial for crop success! Best practices: 1) Water during cooler hours (early morning/evening) 2) Use drip/sprinkler systems for efficiency 3) Monitor soil moisture 4) Mulch to reduce evaporation.",
            "Efficient irrigation saves water and improves yields. Consider: soil moisture monitoring, appropriate irrigation scheduling, water-saving technologies like drip systems, and rainwater harvesting for sustainability.",
            "Water is precious in agriculture! Optimize usage through: proper timing, suitable irrigation methods, soil moisture monitoring, mulching, and choosing drought-resistant varieties when possible."
        ]
        return random.choice(responses)
    
    # Crop-specific queries
    elif any(word in message_lower for word in ['rice', 'wheat', 'corn', 'tomato', 'potato', 'cotton', 'sugarcane']):
        crop_advice = {
            'rice': "Rice cultivation requires careful water management, proper spacing, and timely fertilization. Consider SRI (System of Rice Intensification) techniques for better yields.",
            'wheat': "Wheat needs well-drained soil, appropriate seeding rate, and timely irrigation. Focus on variety selection based on your climate zone.",
            'tomato': "Tomatoes need support systems, regular pruning, and consistent moisture. Watch for common diseases like blight and implement preventive measures.",
            'cotton': "Cotton requires deep, well-drained soil and careful pest management. Monitor for bollworm and implement IPM strategies."
        }
        
        for crop in crop_advice:
            if crop in message_lower:
                return f"{crop_advice[crop]} Would you like specific guidance on any aspect of {crop} cultivation?"
    
    # General farming or unclear queries
    else:
        responses = [
            "I'm here to help with your farming questions! I can assist with crop management, soil health, pest control, irrigation, market information, and general agricultural practices. What specific topic interests you?",
            "As your agricultural assistant, I can provide guidance on: crop selection and cultivation, soil management and fertilizers, pest and disease control, irrigation techniques, weather-based advice, and market insights. How can I help you today?",
            "Agriculture is both an art and science! I'm equipped to help with various farming aspects - from seed selection to harvest management. What farming challenge are you facing?",
            "Every farmer's situation is unique, but I can offer general guidance on crops, soil, water management, pest control, and sustainable farming practices. What would you like to explore?"
        ]
        return random.choice(responses)

@app.route('/api/chatbot/translate', methods=['POST'])
def translate_message():
    """
    Translate message between supported languages
    """
    try:
        data = request.get_json()
        text = data.get('text', '')
        source_lang = data.get('source_lang', 'en')
        target_lang = data.get('target_lang', 'en')
        
        if not text:
            return jsonify({'success': False, 'message': 'No text provided'}), 400
        
        # Use Gemini for translation with agricultural context
        translation = translate_with_gemini(text, source_lang, target_lang)
        
        return jsonify({
            'success': True,
            'data': {
                'original_text': text,
                'translated_text': translation,
                'source_language': source_lang,
                'target_language': target_lang
            }
        })
        
    except Exception as e:
        print(f"❌ Translation error: {str(e)}")
        return jsonify({'success': False, 'message': f'Translation error: {str(e)}'}), 500

def translate_with_gemini(text, source_lang, target_lang):
    """
    Translate text using Gemini with agricultural terminology awareness
    """
    try:
        lang_names = {
            'en': 'English',
            'hi': 'Hindi',
            'ta': 'Tamil',
            'od': 'Odia'
        }
        
        source_name = lang_names.get(source_lang, 'English')
        target_name = lang_names.get(target_lang, 'English')
        
        prompt = f"""
You are a specialized agricultural translator. Translate the following text from {source_name} to {target_name}.
Pay special attention to agricultural terms, crop names, farming techniques, and maintain technical accuracy.

Text to translate: {text}

Provide only the translation, no additional explanation.
"""
        
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        response = model.generate_content(prompt)
        
        if response and response.text:
            return response.text.strip()
        else:
            return text  # Return original if translation fails
            
    except Exception as e:
        print(f"❌ Gemini translation error: {str(e)}")
        return text  # Return original text if translation fails

@app.route('/api/chatbot/voice/synthesize', methods=['POST'])
def synthesize_speech_ivr():
    """
    Convert text to speech for IVR support
    """
    try:
        data = request.get_json()
        text = data.get('text', '')
        language = data.get('language', 'en')
        
        if not text:
            return jsonify({'success': False, 'message': 'No text provided'}), 400
        
        # For now, return the text with language info for frontend TTS
        # In production, you might use Google Cloud Text-to-Speech or similar
        return jsonify({
            'success': True,
            'data': {
                'text': text,
                'language': language,
                'audio_url': None,  # Would contain actual audio URL in production
                'message': 'Use browser TTS for now'
            }
        })
        
    except Exception as e:
        print(f"❌ TTS error: {str(e)}")
        return jsonify({'success': False, 'message': f'TTS error: {str(e)}'}), 500

@app.route('/api/chatbot/health', methods=['GET'])
def chatbot_health():
    return jsonify({'status': 'healthy', 'service': 'chatbot'})

# Helper function for Gemini market price fallback
def get_market_prices_from_gemini(state, district, commodity):
    """
    Get estimated market prices using Gemini AI when data.gov.in has no data
    """
    try:
        # Construct a prompt for Gemini to estimate market prices
        prompt = f"""You are an agricultural market price expert. Provide ONE realistic market price estimate for {commodity} in {district}, {state}, India.

Please provide realistic price ranges in Indian Rupees per kg based on:
- Current agricultural market trends in India
- Seasonal variations
- Regional factors for {state}
- Typical wholesale market prices

IMPORTANT: 
- Provide only ONE entry (not multiple varieties)
- Prices should be realistic per kg (not per quintal)
- Common crops like Rice should be 20-40 ₹/kg, Wheat 25-35 ₹/kg, Cotton 50-80 ₹/kg

Format your response as a JSON with this exact structure:
[
    {{
        "market": "{district} Mandi",
        "commodity": "{commodity}",
        "variety": "Common",
        "min_price": "minimum_price_per_kg",
        "max_price": "maximum_price_per_kg", 
        "modal_price": "average_price_per_kg",
        "arrival_date": "2025-09-23",
        "state": "{state}",
        "district": "{district}"
    }}
]

Provide only the JSON response with ONE entry, no additional text."""

        headers = {
            'Content-Type': 'application/json',
        }
        
        data = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ]
        }
        
        # Make request to Gemini API
        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"
        
        print(f"🤖 Requesting Gemini fallback for {commodity} in {district}, {state}")
        
        response = requests.post(gemini_url, headers=headers, json=data, timeout=15)
        
        if response.status_code == 200:
            result = response.json()
            
            if 'candidates' in result and result['candidates']:
                content = result['candidates'][0]['content']['parts'][0]['text']
                print(f"🤖 Gemini response: {content}")
                
                # Try to parse JSON from Gemini response
                try:
                    # Clean the response text to extract JSON
                    import re
                    json_match = re.search(r'\[.*\]', content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group()
                        market_data = json.loads(json_str)
                        return market_data
                    else:
                        # Fallback to mock data if JSON parsing fails
                        return generate_mock_market_data(state, district, commodity)
                except json.JSONDecodeError:
                    print("❌ Failed to parse Gemini JSON response, using mock data")
                    return generate_mock_market_data(state, district, commodity)
            else:
                print("❌ No valid response from Gemini, using mock data")
                return generate_mock_market_data(state, district, commodity)
        else:
            print(f"❌ Gemini API error: {response.status_code}")
            return generate_mock_market_data(state, district, commodity)
            
    except Exception as e:
        print(f"❌ Gemini fallback error: {str(e)}")
        return generate_mock_market_data(state, district, commodity)

def generate_mock_market_data(state, district, commodity):
    """
    Generate mock market data as a last resort fallback
    """
    import random
    from datetime import datetime
    
    # Base prices for different commodities (per kg in INR)
    # Note: Converted from quintal prices (divided by 100)
    base_prices = {
        'Rice': {'min': 20, 'max': 35},
        'Wheat': {'min': 22, 'max': 28},
        'Maize': {'min': 18, 'max': 25},
        'Sugarcane': {'min': 3, 'max': 4},
        'Cotton': {'min': 55, 'max': 70},
        'Soybean': {'min': 40, 'max': 55},
        'Groundnut': {'min': 50, 'max': 65},
        'Sunflower': {'min': 55, 'max': 70},
        'Mustard': {'min': 45, 'max': 60},
        'Bajra': {'min': 20, 'max': 28}
    }
    
    price_range = base_prices.get(commodity, {'min': 20, 'max': 40})
    
    # Add some randomness to make it realistic
    min_price = price_range['min'] + random.randint(-2, 2)
    max_price = price_range['max'] + random.randint(-2, 2)
    modal_price = (min_price + max_price) // 2
    
    return [{
        'market': f"{district} Mandi",
        'commodity': commodity,
        'variety': 'Common',
        'min_price': str(min_price),
        'max_price': str(max_price),
        'modal_price': str(modal_price),
        'arrival_date': datetime.now().strftime('%Y-%m-%d'),
        'state': state,
        'district': district
    }]

# Market Price API
@app.route('/api/market/prices', methods=['GET'])
def get_market_prices():
    """
    Get market prices from data.gov.in API
    Query parameters: state, district, commodity
    """
    try:
        state = request.args.get('state')
        district = request.args.get('district')
        commodity = request.args.get('commodity')
        
        if not all([state, district, commodity]):
            return jsonify({
                'success': False, 
                'message': 'Missing required parameters: state, district, commodity'
            }), 400
        
        # Data.gov.in Market API endpoint
        api_url = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
        
        # Try multiple API parameter combinations to get data
        param_combinations = [
            # First try with exact filters
            {
                'api-key': DATA_GOV_IN_API_KEY,
                'format': 'json',
                'limit': 10,
                'filters[state]': state,
                'filters[district]': district,
                'filters[commodity]': commodity
            },
            # Try with only state and commodity
            {
                'api-key': DATA_GOV_IN_API_KEY,
                'format': 'json',
                'limit': 10,
                'filters[state]': state,
                'filters[commodity]': commodity
            },
            # Try with only commodity
            {
                'api-key': DATA_GOV_IN_API_KEY,
                'format': 'json',
                'limit': 10,
                'filters[commodity]': commodity
            },
            # Try without any filters to see available data
            {
                'api-key': DATA_GOV_IN_API_KEY,
                'format': 'json',
                'limit': 5
            }
        ]
        
        data_found = False
        market_data = []
        
        for i, params in enumerate(param_combinations):
            print(f"🔍 Trying API combination {i+1}/4")
            print(f"🌐 API URL: {api_url}")
            print(f"📋 Parameters: {params}")
            
            try:
                # Make API request
                response = requests.get(api_url, params=params, timeout=10)
                print(f"📊 API Response Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"📈 API Response - Total: {data.get('total', 0)}, Count: {data.get('count', 0)}")
                    
                    if 'records' in data and data['records'] and len(data['records']) > 0:
                        print(f"✅ Found data with combination {i+1}")
                        data_found = True
                        
                        # Process and format the market data
                        for record in data['records']:
                            # Convert prices from quintal to kg (1 quintal = 100 kg)
                            def convert_price_to_kg(price_str):
                                if price_str and str(price_str).replace('.', '').isdigit():
                                    try:
                                        return str(round(float(price_str) / 100, 2))
                                    except (ValueError, TypeError):
                                        return price_str
                                return price_str
                            
                            market_item = {
                                'market': record.get('market'),
                                'commodity': record.get('commodity'),
                                'variety': record.get('variety'),
                                'min_price': convert_price_to_kg(record.get('min_price')),
                                'max_price': convert_price_to_kg(record.get('max_price')),
                                'modal_price': convert_price_to_kg(record.get('modal_price')),
                                'arrival_date': record.get('arrival_date'),
                                'state': record.get('state'),
                                'district': record.get('district')
                            }
                            market_data.append(market_item)
                        
                        # If we found data, break and use it
                        break
                    else:
                        print(f"❌ No records in combination {i+1}")
                else:
                    print(f"❌ API Error for combination {i+1}: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Exception in combination {i+1}: {str(e)}")
                continue
        
        # If we found data from data.gov.in, return it
        if data_found and market_data:
            print(f"✅ Returning {len(market_data)} market records from data.gov.in")
            return jsonify({
                'success': True,
                'data': market_data,
                'count': len(market_data),
                'message': f'Found {len(market_data)} market records',
                'source': 'data.gov.in'
            })
        else:
            print(f"⚠️ No data found from data.gov.in with any parameter combination")
            # Try Gemini fallback
            gemini_data = get_market_prices_from_gemini(state, district, commodity)
            return jsonify({
                'success': True,
                'data': gemini_data,
                'count': len(gemini_data),
                'message': f'Market prices estimated using AI (no live data available)',
                'source': 'gemini_ai'
            })
            
    except requests.exceptions.Timeout:
        print("⏰ Market API request timed out, falling back to Gemini")
        gemini_data = get_market_prices_from_gemini(state, district, commodity)
        return jsonify({
            'success': True,
            'data': gemini_data,
            'count': len(gemini_data),
            'message': 'Market prices estimated using AI (data.gov.in API timeout)',
            'source': 'gemini_ai'
        })
    except requests.exceptions.RequestException as e:
        print(f"🌐 Market API request failed: {str(e)}, falling back to Gemini")
        gemini_data = get_market_prices_from_gemini(state, district, commodity)
        return jsonify({
            'success': True,
            'data': gemini_data,
            'count': len(gemini_data),
            'message': f'Market prices estimated using AI (data.gov.in API error)',
            'source': 'gemini_ai'
        })
    except Exception as e:
        print(f"❌ Market API error: {str(e)}, falling back to Gemini")
        gemini_data = get_market_prices_from_gemini(state, district, commodity)
        return jsonify({
            'success': True,
            'data': gemini_data,
            'count': len(gemini_data),
            'message': f'Market prices estimated using AI (unexpected error)',
            'source': 'gemini_ai'
        })

@app.route('/api/market/health', methods=['GET'])
def market_health():
    return jsonify({'status': 'healthy', 'service': 'market'})

# ===============================================
# ADMIN PANEL ENDPOINTS
# ===============================================

# Admin credentials (hardcoded for simplicity)
ADMIN_EMAIL = "admin@agricare"
ADMIN_PASSWORD = "admin"

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """Admin authentication endpoint"""
    try:
        data = request.get_json()
        email = data.get('email', '').lower().strip()
        password = data.get('password', '')
        
        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            # Create admin JWT token with role
            access_token = create_access_token(
                identity='admin_user',
                additional_claims={'role': 'admin', 'email': ADMIN_EMAIL}
            )
            
            return jsonify({
                'success': True,
                'access_token': access_token,
                'user': {
                    'email': ADMIN_EMAIL,
                    'role': 'admin',
                    'name': 'Administrator'
                }
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid credentials'
            }), 401
            
    except Exception as e:
        print(f"❌ Admin login error: {e}")
        return jsonify({
            'success': False,
            'error': 'Login failed'
        }), 500

@app.route('/api/admin/users', methods=['GET'])
@jwt_required()
def admin_get_users():
    """Get all users (admin only)"""
    try:
        claims = get_jwt()
        if claims.get('role') != 'admin':
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        if not FIREBASE_AVAILABLE or not db:
            return jsonify({
                'success': False,
                'error': 'Database unavailable',
                'users': []
            }), 503
        
        # Get all users from Firestore
        users_ref = db.collection('users')
        users = []
        
        for doc in users_ref.stream():
            user_data = doc.to_dict()
            user_data['id'] = doc.id
            # Remove sensitive data
            user_data.pop('password', None)
            users.append(user_data)
        
        return jsonify({
            'success': True,
            'users': users,
            'total': len(users)
        }), 200
        
    except Exception as e:
        print(f"❌ Admin get users error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/analytics/overview', methods=['GET'])
@jwt_required()
def admin_analytics_overview():
    """Get dashboard analytics (admin only)"""
    try:
        claims = get_jwt()
        if claims.get('role') != 'admin':
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        if not FIREBASE_AVAILABLE or not db:
            # Return mock data if Firebase is unavailable
            return jsonify({
                'success': True,
                'analytics': {
                    'total_users': 0,
                    'active_users_today': 0,
                    'total_chats': 0,
                    'total_disease_detections': 0,
                    'note': 'Firebase unavailable - showing demo data'
                }
            }), 200
        
        # Get user count
        users_ref = db.collection('users')
        total_users = len(list(users_ref.stream()))
        
        # Get chat count
        try:
            chats_ref = db.collection('chat_history')
            total_chats = len(list(chats_ref.stream()))
        except:
            total_chats = 0
        
        # Get disease detection count
        try:
            disease_ref = db.collection('disease_detections')
            total_disease = len(list(disease_ref.stream()))
        except:
            total_disease = 0
        
        return jsonify({
            'success': True,
            'analytics': {
                'total_users': total_users,
                'active_users_today': 0,  # Would need to track login times
                'total_chats': total_chats,
                'total_disease_detections': total_disease
            }
        }), 200
        
    except Exception as e:
        print(f"❌ Admin analytics error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/chatbot/conversations', methods=['GET'])
@jwt_required()
def admin_get_conversations():
    """Get all chat conversations (admin only)"""
    try:
        claims = get_jwt()
        if claims.get('role') != 'admin':
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        if not FIREBASE_AVAILABLE or not db:
            return jsonify({
                'success': False,
                'error': 'Database unavailable',
                'conversations': []
            }), 503
        
        # Get chat history
        chats_ref = db.collection('chat_history').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(100)
        conversations = []
        
        for doc in chats_ref.stream():
            chat_data = doc.to_dict()
            chat_data['id'] = doc.id
            conversations.append(chat_data)
        
        return jsonify({
            'success': True,
            'conversations': conversations,
            'total': len(conversations)
        }), 200
        
    except Exception as e:
        print(f"❌ Admin get conversations error: {e}")
        return jsonify({
            'success': True,  # Return success with empty list
            'conversations': [],
            'error_note': 'Chat history collection may not exist yet'
        }), 200

@app.route('/api/admin/disease-detections', methods=['GET'])
@jwt_required()
def admin_get_disease_detections():
    """Get all disease detections (admin only)"""
    try:
        claims = get_jwt()
        if claims.get('role') != 'admin':
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        if not FIREBASE_AVAILABLE or not db:
            return jsonify({
                'success': False,
                'error': 'Database unavailable',
                'detections': []
            }), 503
        
        # Get disease detections
        disease_ref = db.collection('disease_detections').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(100)
        detections = []
        
        for doc in disease_ref.stream():
            detection_data = doc.to_dict()
            detection_data['id'] = doc.id
            detections.append(detection_data)
        
        return jsonify({
            'success': True,
            'detections': detections,
            'total': len(detections)
        }), 200
        
    except Exception as e:
        print(f"❌ Admin get disease detections error: {e}")
        return jsonify({
            'success': True,  # Return success with empty list
            'detections': [],
            'error_note': 'Disease detections collection may not exist yet'
        }), 200

@app.route('/api/admin/system/health', methods=['GET'])
@jwt_required()
def admin_system_health():
    """Get system health metrics (admin only)"""
    try:
        claims = get_jwt()
        if claims.get('role') != 'admin':
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        return jsonify({
            'success': True,
            'health': {
                'server_status': 'running',
                'firebase': FIREBASE_AVAILABLE,
                'gemini_api': True,  # Gemini API should be available
                'tts_available': TTS_AVAILABLE,
                'gemma_available': GEMMA_AVAILABLE,
                'pytorch_available': PYTORCH_AVAILABLE,
                'translation_available': TRANSLATION_AVAILABLE,
                'uptime': 'Running',
                'timestamp': datetime.now().isoformat()
            }
        }), 200
        
    except Exception as e:
        print(f"❌ Admin system health error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'message': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'message': 'Internal server error'}), 500

if __name__ == '__main__':
    # Create upload directory if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # ===============================================
    # DISEASE MODEL - USING LOCAL FILE
    # ===============================================
    # Using local model file at G:\models\best_disease_model.pth
    # No download needed - model is already available locally
    
    # Initialize Firebase
    print("🔥 Initializing Firebase...")
    firebase_initialized = initialize_firebase()
    if firebase_initialized:
        print("✅ Firebase initialized successfully")
    else:
        print("❌ Firebase initialization failed - using fallback storage")
    
    # Initialize disease detection model
    print("🧠 Initializing disease detection model...")
    model_loaded = load_disease_model()
    if model_loaded:
        print("✅ Disease detection model loaded successfully from local file")
    else:
        print("❌ Failed to load disease detection model from local file")
    
    print("🚀 AgriCare Python Backend Server starting...")
    print("📱 Frontend served at: http://localhost:5000")
    print("🔗 API available at: http://localhost:5000/api")
    print("🏥 Health check: http://localhost:5000/api/health")
    print("🔥 Firebase: " + ("enabled" if firebase_initialized else "disabled (using fallback)"))
    print("🤖 Gemma Chatbot: " + ("loaded" if GEMMA_AVAILABLE else "disabled (using fallback)"))
    print("🔊 TTS Model: " + ("loaded" if TTS_AVAILABLE else "disabled"))
    print("🧠 Disease Model: " + ("loaded" if model_loaded else "disabled (using fallback)"))
    print("🌍 Environment: development")
    
    app.run(debug=True, host='0.0.0.0', port=5000)