# Firebase Functions for AgriCare Backend
from firebase_functions import https_fn
from firebase_functions.options import set_global_options
from firebase_admin import initialize_app
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import os
from datetime import timedelta, datetime
import hashlib
import json
import requests
from werkzeug.utils import secure_filename

# For cost control, set the maximum number of containers
set_global_options(max_instances=10)

# Initialize Firebase Admin
initialize_app()

# Firebase imports
try:
    import firebase_admin
    from firebase_admin import credentials, firestore, storage, auth
    import pyrebase
    FIREBASE_AVAILABLE = True
    print("Firebase dependencies loaded successfully")
except ImportError as e:
    print(f"Firebase not available: {e}")
    FIREBASE_AVAILABLE = False
    # Mock Firebase classes
    class firestore:
        @staticmethod
        def client():
            return None

# Google Generative AI import
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    print("Gemini AI not available")
    GEMINI_AVAILABLE = False

# PyTorch imports - conditional loading
try:
    import torch
    import torchvision.transforms as transforms
    from PIL import Image
    PYTORCH_AVAILABLE = True
    print("PyTorch dependencies loaded successfully")
except ImportError as e:
    print(f"PyTorch not available: {e}")
    PYTORCH_AVAILABLE = False
    # Mock classes for when PyTorch isn't available
    class torch:
        @staticmethod
        def device(device_type):
            return None
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

# Create Flask app for Firebase Functions
def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['JWT_SECRET_KEY'] = 'agricare-super-secret-key-change-in-production'
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    
    # Initialize extensions
    jwt = JWTManager(app)
    CORS(app)
    
    # API Keys (use environment variables in production)
    GEMINI_API_KEY = "AIzaSyCvAcqKAph3_FHm3pWB7I5VwlDDnZmeSQo"
    HUGGING_FACE_API_KEY = "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"
    
    # Firebase Configuration
    FIREBASE_CONFIG = {
        "apiKey": "AIzaSyCvAcqKAph3_FHm3pWB7I5VwlDDnZmeSQo",
        "authDomain": "agricare-project.firebaseapp.com",
        "databaseURL": "https://agricare-project-default-rtdb.firebaseio.com",
        "projectId": "agricare-project",
        "storageBucket": "agricare-project.appspot.com",
        "messagingSenderId": "930751502005",
        "appId": "1:930751502005:web:db3e04a23cea3411efbdae",
        "measurementId": "G-3SB5EMG81B"
    }
    
    # Initialize Gemini AI
    if GEMINI_AVAILABLE:
        genai.configure(api_key=GEMINI_API_KEY)
    
    # Initialize Firestore
    db = None
    if FIREBASE_AVAILABLE:
        try:
            db = firestore.client()
            print("Firestore initialized successfully")
        except Exception as e:
            print(f"Failed to initialize Firestore: {e}")
    
    # Utility functions
    def hash_password(password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(password, hashed):
        return hashlib.sha256(password.encode()).hexdigest() == hashed
    
    def find_user_by_email(email):
        if not db:
            return None
        try:
            users_ref = db.collection('users')
            query = users_ref.where('email', '==', email).limit(1)
            docs = list(query.stream())
            if docs:
                doc = docs[0]
                user_data = doc.to_dict()
                user_data['id'] = doc.id
                return user_data
            return None
        except Exception as e:
            print(f"Error finding user: {e}")
            return None
    
    # Routes
    @app.route('/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'services': {
                'firebase': FIREBASE_AVAILABLE,
                'gemini': GEMINI_AVAILABLE,
                'pytorch': PYTORCH_AVAILABLE
            }
        })
    
    @app.route('/')
    def api_info():
        return jsonify({
            'name': 'AgriCare API',
            'version': '2.0.0',
            'description': 'AI-powered farming assistant backend',
            'endpoints': [
                '/health',
                '/auth/register',
                '/auth/login', 
                '/auth/verify',
                '/auth/google-login',
                '/weather/current',
                '/weather/forecast',
                '/disease/detect',
                '/yield/predict',
                '/chatbot/message'
            ]
        })
    
    @app.route('/auth/register', methods=['POST'])
    def register():
        try:
            data = request.get_json()
            
            if not data or not data.get('email') or not data.get('password'):
                return jsonify({'error': 'Email and password are required'}), 400
            
            email = data['email'].lower().strip()
            password = data['password']
            full_name = data.get('full_name', '')
            
            # Check if user already exists
            if find_user_by_email(email):
                return jsonify({'error': 'User already exists'}), 409
            
            # Create user in Firestore
            if not db:
                return jsonify({'error': 'Database unavailable'}), 500
                
            user_data = {
                'email': email,
                'password': hash_password(password),
                'full_name': full_name,
                'created_at': datetime.utcnow(),
                'last_login': None,
                'login_count': 0,
                'provider': 'email',
                'verified': False
            }
            
            doc_ref = db.collection('users').add(user_data)
            user_id = doc_ref[1].id
            
            # Create access token
            access_token = create_access_token(identity=user_id)
            
            return jsonify({
                'message': 'User registered successfully',
                'access_token': access_token,
                'user': {
                    'id': user_id,
                    'email': email,
                    'full_name': full_name
                }
            }), 201
            
        except Exception as e:
            print(f"Registration error: {e}")
            return jsonify({'error': 'Registration failed'}), 500
    
    @app.route('/auth/login', methods=['POST'])
    def login():
        try:
            data = request.get_json()
            
            if not data or not data.get('email') or not data.get('password'):
                return jsonify({'error': 'Email and password are required'}), 400
            
            email = data['email'].lower().strip()
            password = data['password']
            
            # Find user
            user = find_user_by_email(email)
            if not user or not verify_password(password, user['password']):
                return jsonify({'error': 'Invalid email or password'}), 401
            
            # Update last login
            if db:
                try:
                    db.collection('users').document(user['id']).update({
                        'last_login': datetime.utcnow(),
                        'login_count': user.get('login_count', 0) + 1
                    })
                except Exception as e:
                    print(f"Error updating login info: {e}")
            
            # Create access token
            access_token = create_access_token(identity=user['id'])
            
            return jsonify({
                'message': 'Login successful',
                'access_token': access_token,
                'user': {
                    'id': user['id'],
                    'email': user['email'],
                    'full_name': user.get('full_name', ''),
                    'login_count': user.get('login_count', 0) + 1
                }
            }), 200
            
        except Exception as e:
            print(f"Login error: {e}")
            return jsonify({'error': 'Login failed'}), 500
    
    @app.route('/auth/verify', methods=['GET'])
    @jwt_required()
    def verify_token():
        try:
            user_id = get_jwt_identity()
            
            if not db:
                return jsonify({'valid': True, 'user_id': user_id}), 200
                
            # Get user data
            user_doc = db.collection('users').document(user_id).get()
            if not user_doc.exists:
                return jsonify({'error': 'User not found'}), 404
            
            user_data = user_doc.to_dict()
            
            return jsonify({
                'valid': True,
                'user': {
                    'id': user_id,
                    'email': user_data.get('email'),
                    'full_name': user_data.get('full_name', ''),
                    'provider': user_data.get('provider', 'email')
                }
            }), 200
            
        except Exception as e:
            print(f"Token verification error: {e}")
            return jsonify({'error': 'Token verification failed'}), 500
    
    @app.route('/weather/current', methods=['GET'])
    def get_current_weather():
        try:
            lat = request.args.get('lat')
            lng = request.args.get('lng')
            
            if not lat or not lng:
                return jsonify({'error': 'Latitude and longitude are required'}), 400
            
            # Call Open-Meteo API
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,wind_speed_10m,wind_direction_10m&timezone=auto"
            
            response = requests.get(url)
            if response.status_code == 200:
                return jsonify(response.json()), 200
            else:
                return jsonify({'error': 'Weather service unavailable'}), 503
                
        except Exception as e:
            print(f"Weather error: {e}")
            return jsonify({'error': 'Failed to fetch weather'}), 500
    
    @app.route('/weather/forecast', methods=['GET'])
    def get_weather_forecast():
        try:
            lat = request.args.get('lat')
            lng = request.args.get('lng')
            
            if not lat or not lng:
                return jsonify({'error': 'Latitude and longitude are required'}), 400
            
            # Call Open-Meteo API for 7-day forecast
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max&timezone=auto&forecast_days=7"
            
            response = requests.get(url)
            if response.status_code == 200:
                return jsonify(response.json()), 200
            else:
                return jsonify({'error': 'Weather forecast service unavailable'}), 503
                
        except Exception as e:
            print(f"Weather forecast error: {e}")
            return jsonify({'error': 'Failed to fetch weather forecast'}), 500
    
    @app.route('/chatbot/message', methods=['POST'])
    def chatbot_message():
        try:
            data = request.get_json()
            
            if not data or not data.get('message'):
                return jsonify({'error': 'Message is required'}), 400
            
            user_message = data['message']
            language = data.get('language', 'en')
            
            if not GEMINI_AVAILABLE:
                return jsonify({
                    'response': 'I am AgriBot, your farming assistant. However, AI services are currently unavailable. Please try again later.',
                    'language': language
                }), 200
            
            # Create context-aware prompt
            system_prompt = f"""You are AgriBot, an expert agricultural assistant for Indian farmers. 
            Always provide helpful, accurate, and practical farming advice.
            Respond in the requested language: {language}
            Keep responses concise but informative.
            
            User question: {user_message}
            """
            
            try:
                model = genai.GenerativeModel('gemini-pro')
                response = model.generate_content(system_prompt)
                
                return jsonify({
                    'response': response.text,
                    'language': language,
                    'timestamp': datetime.utcnow().isoformat()
                }), 200
                
            except Exception as e:
                print(f"Gemini API error: {e}")
                return jsonify({
                    'response': 'I apologize, but I am experiencing technical difficulties. Please try asking your question again.',
                    'language': language
                }), 200
            
        except Exception as e:
            print(f"Chatbot error: {e}")
            return jsonify({'error': 'Chatbot service failed'}), 500
    
    # Additional simplified endpoints can be added here
    # For now, including core functionality
    
    return app

# Create the Flask app
app = create_app()

@https_fn.on_request()
def api(req: https_fn.Request) -> https_fn.Response:
    """Firebase Function entry point"""
    with app.request_context(req.environ):
        return app.full_dispatch_request()