from functools import wraps
from flask import request, jsonify

# Mock token validation – in production use OAuth2/JWT
VALID_TOKENS = {'mock-token-for-demo': 'admin'}

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid token'}), 401
        token = auth_header.split(' ')[1]
        if token not in VALID_TOKENS:
            return jsonify({'error': 'Invalid token'}), 401
        # Optionally attach user role to request
        request.user_role = VALID_TOKENS[token]
        return f(*args, **kwargs)
    return decorated