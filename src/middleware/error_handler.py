"""
Global Error Handler
====================
Handles all exceptions and returns consistent JSON error responses.
"""

from flask import jsonify, request, g
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError
import traceback


def register_error_handlers(app):
    """
    Register global error handlers for the Flask application.
    
    Args:
        app: Flask application instance
    """
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Handle HTTP exceptions (4xx, 5xx)."""
        request_id = getattr(g, 'request_id', 'unknown')
        
        response = {
            'success': False,
            'error': {
                'code': error.name.upper().replace(' ', '_'),
                'message': error.description,
                'status_code': error.code,
            },
            'request_id': request_id,
        }
        
        # Log error
        app.logger.warning(
            f"HTTP error: {error.code} - {error.description}",
            extra={
                'request_id': request_id,
                'error_code': response['error']['code'],
                'path': request.path,
                'method': request.method,
            }
        )
        
        return jsonify(response), error.code
    
    @app.errorhandler(SQLAlchemyError)
    def handle_database_error(error):
        """Handle database errors."""
        request_id = getattr(g, 'request_id', 'unknown')
        
        # Log the full error for debugging
        app.logger.error(
            f"Database error: {str(error)}",
            extra={
                'request_id': request_id,
                'error_type': type(error).__name__,
                'path': request.path,
                'method': request.method,
            },
            exc_info=True
        )
        
        # Return generic error to client (don't expose DB details)
        response = {
            'success': False,
            'error': {
                'code': 'DATABASE_ERROR',
                'message': 'A database error occurred. Please try again later.',
                'status_code': 500,
            },
            'request_id': request_id,
        }
        
        # In development, include more details
        if app.config.get('DEBUG'):
            response['error']['details'] = str(error)
        
        return jsonify(response), 500
    
    @app.errorhandler(ValueError)
    def handle_value_error(error):
        """Handle validation errors."""
        request_id = getattr(g, 'request_id', 'unknown')
        
        response = {
            'success': False,
            'error': {
                'code': 'VALIDATION_ERROR',
                'message': str(error),
                'status_code': 400,
            },
            'request_id': request_id,
        }
        
        app.logger.warning(
            f"Validation error: {str(error)}",
            extra={
                'request_id': request_id,
                'path': request.path,
                'method': request.method,
            }
        )
        
        return jsonify(response), 400
    
    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle 404 Not Found errors."""
        request_id = getattr(g, 'request_id', 'unknown')
        
        response = {
            'success': False,
            'error': {
                'code': 'NOT_FOUND',
                'message': f'The requested resource was not found: {request.path}',
                'status_code': 404,
            },
            'request_id': request_id,
        }
        
        return jsonify(response), 404
    
    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        """Handle 405 Method Not Allowed errors."""
        request_id = getattr(g, 'request_id', 'unknown')
        
        response = {
            'success': False,
            'error': {
                'code': 'METHOD_NOT_ALLOWED',
                'message': f'Method {request.method} is not allowed for {request.path}',
                'status_code': 405,
            },
            'request_id': request_id,
        }
        
        return jsonify(response), 405
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Handle all unexpected errors."""
        request_id = getattr(g, 'request_id', 'unknown')
        
        # Log the full traceback
        app.logger.error(
            f"Unexpected error: {str(error)}",
            extra={
                'request_id': request_id,
                'error_type': type(error).__name__,
                'path': request.path,
                'method': request.method,
            },
            exc_info=True
        )
        
        response = {
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An unexpected error occurred. Please try again later.',
                'status_code': 500,
            },
            'request_id': request_id,
        }
        
        # In development, include error details
        if app.config.get('DEBUG'):
            response['error']['details'] = str(error)
            response['error']['traceback'] = traceback.format_exc()
        
        return jsonify(response), 500
    
    app.logger.info("Error handlers registered")
