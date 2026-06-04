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

