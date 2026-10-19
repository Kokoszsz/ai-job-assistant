"""
Authentication Middleware
=========================
JWT authentication decorator for protected routes.
"""

from functools import wraps
from flask import request, jsonify, current_app
from src.services.auth_service import AuthService, TokenError, TokenExpiredError, TokenInvalidError, TokenBlacklistedError


def require_auth(f):
    """
    Decorator to require JWT authentication on routes.
    
    Extracts and validates JWT token from Authorization header.
    Injects user_id and email into the decorated function.
    
    Usage:
        @app.route('/api/profile')
        @require_auth
        def get_profile(user_id, email):
            # user_id and email automatically available
            return {'user_id': user_id}
    
    Returns 401 if:
    - No Authorization header present
    - Token is invalid, expired, or blacklisted
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Extract token from cookie first, then Authorization header
        token = request.cookies.get('access_token')
        
        # Fallback to Authorization header if not in cookie
        if not token:
            auth_header = request.headers.get('Authorization')
            
            if not auth_header:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'NO_TOKEN',
                        'message': 'Access token is required'
                    }
                }), 401
            
            # Check Bearer prefix
            parts = auth_header.split()
            if len(parts) != 2 or parts[0].lower() != 'bearer':
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'INVALID_HEADER',
                        'message': 'Authorization header must be Bearer token'
                    }
                }), 401
            
            token = parts[1]
        
        try:
            # Validate token and extract user info
            auth_service = AuthService()
            user_info = auth_service.extract_user_from_token(token)
            
            # Inject user_id and email into function
            kwargs['user_id'] = user_info['user_id']
            kwargs['email'] = user_info['email']
            
            return f(*args, **kwargs)
            
        except TokenExpiredError:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'TOKEN_EXPIRED',
                    'message': 'Token has expired'
                }
            }), 401
            
        except TokenBlacklistedError:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'TOKEN_REVOKED',
                    'message': 'Token has been revoked'
                }
            }), 401
            
        except TokenInvalidError as e:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_TOKEN',
                    'message': str(e)
                }
            }), 401
            
        except TokenError as e:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'AUTH_ERROR',
                    'message': str(e)
                }
            }), 401
    
    return decorated_function


def optional_auth(f):
    """
    Decorator for optional authentication.
    
    If token is present and valid, injects user_id and email.
    If no token or invalid token, continues without user info.
    
    Usage:
        @app.route('/api/public')
        @optional_auth
        def public_route(user_id=None, email=None):
            if user_id:
                # Authenticated user
                pass
            else:
                # Anonymous user
                pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Try to extract token
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            # No token, continue without auth
            return f(*args, **kwargs)
        
        # Check Bearer prefix
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            # Invalid format, continue without auth
            return f(*args, **kwargs)
        
        token = parts[1]
        
        try:
            # Validate token and extract user info
            auth_service = AuthService()
            user_info = auth_service.extract_user_from_token(token)
            
            # Inject user_id and email into function
            kwargs['user_id'] = user_info['user_id']
            kwargs['email'] = user_info['email']
            
        except TokenError:
            # Invalid token, continue without auth
            pass
        
        return f(*args, **kwargs)
    
    return decorated_function
