"""
AI Service
==========
Core AI service for managing OpenAI interactions.
Provides centralized AI functionality for all agents.
"""

import logging
from typing import Optional, Dict, Any
from flask import current_app

from ..ai.agents.base_agent import BaseAgent
from ..ai.tools.database_tools import DatabaseTools

logger = logging.getLogger(__name__)


class AIService:
    """
    Central AI service managing OpenAI interactions.
    
    This service:
    - Manages OpenAI client configuration
    - Provides base agents for specialized agents
    - Handles AI service availability
    - Manages database tools for function calling
    """
    
    def __init__(self, app=None, db_session=None):
        """
        Initialize AI service.
        
        Args:
            app: Flask application instance
            db_session: SQLAlchemy database session
        """
        self.app = app
        self.db_session = db_session
        self._agent: Optional[BaseAgent] = None
        self._db_tools: Optional[DatabaseTools] = None
        
        if app is not None:
            self.init_app(app, db_session)
    
    def init_app(self, app, db_session=None):
        """
        Initialize with Flask application.
        
        Args:
            app: Flask application instance
            db_session: SQLAlchemy database session
        """
        self.app = app
        self.db_session = db_session
        
        # Validate configuration
        if not app.config.get('OPENAI_API_KEY'):
            logger.warning("OPENAI_API_KEY not configured - AI features will be disabled")
        else:
            logger.info("AI service initialized with OpenAI")
    
    def create_agent(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        max_messages: Optional[int] = None,
        max_tokens_memory: Optional[int] = None,
    ) -> BaseAgent:
        """
        Create a new base agent instance.
        
        Args:
            model: OpenAI model to use (default: from config)
            temperature: Sampling temperature (default: from config)
            max_tokens: Maximum response tokens (default: from config)
            
        Returns:
            Configured BaseAgent instance
            
        Raises:
            ValueError: If OpenAI API key not configured
        """
        api_key = self._get_config('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OpenAI API key not configured")
        
        agent = BaseAgent(
            api_key=api_key,
            model=model or self._get_config('OPENAI_MODEL', 'gpt-4-turbo-preview'),
            temperature=temperature or self._get_config('OPENAI_TEMPERATURE', 0.7),
            max_tokens=max_tokens or self._get_config('OPENAI_MAX_TOKENS', 1500),
            timeout=self._get_config('OPENAI_TIMEOUT', 30),
        )
        
        # Set conversation memory limits from config
        agent.max_messages = max_messages or self._get_config('CONVERSATION_MAX_MESSAGES', 20)
        agent.max_tokens_memory = max_tokens_memory or self._get_config('CONVERSATION_MAX_TOKENS', 4000)
        
        return agent
    
    def get_db_tools(self) -> DatabaseTools:
        """
        Get database tools for function calling.
        
        Returns:
            DatabaseTools instance
            
        Raises:
            ValueError: If database session not configured
        """
        if not self.db_session:
            raise ValueError("Database session not configured")
        
        if self._db_tools is None:
            self._db_tools = DatabaseTools(self.db_session)
        
        return self._db_tools
    
    def is_available(self) -> bool:
        """
        Check if AI service is available.
        
        Returns:
            True if OpenAI API is configured and accessible
        """
        try:
            api_key = self._get_config('OPENAI_API_KEY')
            if not api_key:
                return False
            
            # Try creating and testing an agent
            agent = self.create_agent()
            return agent.is_available()
            
        except Exception as e:
            logger.error(f"AI service availability check failed: {e}")
            return False
    
    def get_fallback_response(self, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Get fallback response when AI service unavailable.
        
        Args:
            context: Context about what was being attempted
            
        Returns:
            Error response dict
        """
        message = "I apologize, but the AI assistant is temporarily unavailable. "
        
        if context == 'chat':
            message += "Please try again in a moment. In the meantime, you can browse job listings directly."
        elif context == 'job_search':
            message += "You can still search for jobs using the filters on the jobs page."
        elif context == 'cv':
            message += "CV generation is temporarily unavailable. Please try again later."
        else:
            message += "Please try again in a moment."
        
        return {
            'success': False,
            'error': {
                'code': 'AI_SERVICE_UNAVAILABLE',
                'message': message,
            },
        }
    
    def _get_config(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.
        
        Args:
            key: Configuration key
            default: Default value if not found
            
        Returns:
            Configuration value
        """
        if self.app:
            return self.app.config.get(key, default)
        
        # Fallback to current_app if available
        try:
            return current_app.config.get(key, default)
        except RuntimeError:
            return default
    
    def __repr__(self) -> str:
        """String representation."""
        available = "available" if self.is_available() else "unavailable"
        return f"AIService(status={available})"


# Global AI service instance
_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """
    Get global AI service instance.
    
    Returns:
        AIService instance
    """
    global _ai_service
    
    if _ai_service is None:
        _ai_service = AIService()
    
    return _ai_service


def init_ai_service(app, db_session=None) -> AIService:
    """
    Initialize global AI service with Flask app.
    
    Args:
        app: Flask application instance
        db_session: SQLAlchemy database session
        
    Returns:
        Initialized AIService instance
    """
    global _ai_service
    
    _ai_service = AIService(app, db_session)
    return _ai_service
