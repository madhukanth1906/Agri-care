# Firebase Configuration for AgriCare
# This file contains Firebase project configuration
# IMPORTANT: Do not commit actual API keys to version control
# Use environment variables instead

import os

# Firebase Web API Configuration
# Load these from environment variables for security
FIREBASE_CONFIG = {
    "apiKey": os.getenv("FIREBASE_API_KEY", ""),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN", ""),
    "projectId": os.getenv("FIREBASE_PROJECT_ID", ""),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET", ""),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID", ""),
    "appId": os.getenv("FIREBASE_APP_ID", ""),
    "measurementId": os.getenv("FIREBASE_MEASUREMENT_ID", "")
}

# Firebase Admin SDK Service Account Configuration
# Load from environment variables or a secure service account JSON file
SERVICE_ACCOUNT_KEY = {
    "type": "service_account",
    "project_id": os.getenv("FIREBASE_PROJECT_ID", ""),
    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID", ""),
    "private_key": os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n'),
    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL", ""),
    "client_id": os.getenv("FIREBASE_CLIENT_ID", ""),
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL", "")
}

# Authentication Providers
AUTH_PROVIDERS = {
    'EMAIL': 'password',
    'GOOGLE': 'google.com',
    'FACEBOOK': 'facebook.com',
    'TWITTER': 'twitter.com'
}

# Google OAuth Configuration
GOOGLE_OAUTH_CONFIG = {
    'client_id': os.getenv("GOOGLE_OAUTH_CLIENT_ID", ""),
    'client_secret': os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", ""),
    'redirect_uris': [
        os.getenv("APP_URL", "http://localhost:5000"),
        'http://localhost:3000',
        'http://localhost:5000'
    ]
}

# Database Collections
COLLECTIONS = {
    'USERS': 'users',
    'DISEASE_DETECTIONS': 'disease_detections', 
    'YIELD_PREDICTIONS': 'yield_predictions',
    'CHAT_HISTORY': 'chat_history',
    'USER_IMAGES': 'user_images'
}

# Storage paths
STORAGE_PATHS = {
    'DISEASE_IMAGES': 'disease_detection_images/',
    'USER_PROFILES': 'user_profiles/',
    'CHAT_ATTACHMENTS': 'chat_attachments/'
}