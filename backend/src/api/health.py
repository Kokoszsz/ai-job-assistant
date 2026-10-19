"""
Health Check Endpoint
=====================
System health and status monitoring endpoint.
"""

from flask import Blueprint, jsonify, current_app
from datetime import datetime
from src.models import db


health_bp = Blueprint('health', __name__, url_prefix='/api')


@health_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for monitoring and container orchestration.
    
    Returns:
        JSON response with service health status
        
    Example Response:
        {
            "status": "healthy",
            "timestamp": "2025-12-14T10:30:00Z",
            "service": "backend",
            "version": "0.1.0",
            "services": {
                "database": "connected",
                "redis": "connected"
            }
        }
    """
    # Check database connectivity
    db_status = 'connected'
    try:
        db.session.execute(db.text('SELECT 1'))
        db.session.commit()
    except Exception as e:
        db_status = f'error: {str(e)}'
        current_app.logger.error(f"Database health check failed: {str(e)}")
    
    # Check Redis connectivity (if configured)
    redis_status = 'not_configured'
    try:
        from redis import Redis
        redis_url = current_app.config.get('REDIS_URL')
        if redis_url:
            redis_client = Redis.from_url(redis_url, socket_connect_timeout=2)
            redis_client.ping()
            redis_status = 'connected'
    except ImportError:
        redis_status = 'not_installed'
    except Exception as e:
        redis_status = f'error: {str(e)}'
        current_app.logger.warning(f"Redis health check failed: {str(e)}")
    
    # Determine overall status
    overall_status = 'healthy'
    if db_status != 'connected':
        overall_status = 'unhealthy'
    elif 'error' in redis_status:
        overall_status = 'degraded'
    
    # Build response
    response = {
        'status': overall_status,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'service': 'backend',
        'version': current_app.config.get('APP_VERSION', '0.1.0'),
        'services': {
            'database': db_status,
            'redis': redis_status,
        }
    }
    
    # Return appropriate status code
    status_code = 200 if overall_status == 'healthy' else 503
    
    return jsonify(response), status_code


@health_bp.route('/', methods=['GET'])
def api_root():
    """
    API root endpoint.
    
    Returns basic API information and available endpoints.
    """
    return jsonify({
        'message': current_app.config.get('APP_NAME', 'AI Job Search Assistant API'),
        'version': current_app.config.get('APP_VERSION', '0.1.0'),
        'status': 'operational',
        'documentation': '/api/docs (coming soon)',
        'endpoints': {
            'health': '/api/health',
            'profile': '/api/profile/:user_id',
            'jobs': '/api/jobs/search',
            'chat': '/api/chat (coming soon)',
            'cv': '/api/cv (coming soon)',
        }
    }), 200
