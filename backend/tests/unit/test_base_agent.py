"""
Unit Tests: Base Agent
======================
Tests for base AI agent functionality.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from src.ai.agents.base_agent import BaseAgent
from src.ai.memory.conversation_buffer import ConversationBuffer


@pytest.fixture
def mock_openai_client():
    """Create mock OpenAI client."""
    client = MagicMock()
    
    # Mock chat completion response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Test response"
    mock_response.choices[0].message.tool_calls = None
    mock_response.usage.total_tokens = 100
    
    client.chat.completions.create.return_value = mock_response
    
    # Mock models.list for availability check
    client.models.list.return_value = []
    
    return client


@pytest.fixture
def agent(mock_openai_client):
    """Create agent with mocked OpenAI client."""
    with patch('src.ai.agents.base_agent.OpenAI', return_value=mock_openai_client):
        agent = BaseAgent(
            api_key='test-key',
            model='gpt-4-turbo-preview',
            temperature=0.7,
            max_tokens=1500,
            timeout=30,
        )
        return agent


class TestBaseAgentInitialization:
    """Test agent initialization."""
    
    def test_initialization_success(self, mock_openai_client):
        """Test successful agent initialization."""
        with patch('src.ai.agents.base_agent.OpenAI', return_value=mock_openai_client):
            agent = BaseAgent(
                api_key='test-key',
                model='gpt-4',
                temperature=0.5,
                max_tokens=1000,
                timeout=30,
            )
            
            assert agent.model == 'gpt-4'
            assert agent.temperature == 0.5
            assert agent.max_tokens == 1000
            assert agent.conversation is None
    
    def test_initialization_with_invalid_key(self):
        """Test initialization with invalid API key."""
        with patch('src.ai.agents.base_agent.OpenAI', side_effect=Exception('Invalid API key')):
            with pytest.raises(Exception):
                BaseAgent(api_key='invalid-key')


class TestConversationManagement:
    """Test conversation management."""
    
    def test_initialize_conversation(self, agent):
        """Test conversation initialization."""
        agent.initialize_conversation()
        
        assert agent.conversation is not None
        assert isinstance(agent.conversation, ConversationBuffer)
        assert len(agent.conversation) == 1  # System message
        assert agent.conversation.messages[0].role == 'system'
    
    def test_initialize_conversation_with_custom_prompt(self, agent):
        """Test conversation with custom system prompt."""
        custom_prompt = "You are a job search assistant."
        agent.initialize_conversation(system_prompt=custom_prompt)
        
        assert agent.conversation.messages[0].content == custom_prompt
    
    def test_set_system_prompt(self, agent):
        """Test setting system prompt."""
        agent.initialize_conversation()
        agent.set_system_prompt("New system prompt")
        
        assert agent.conversation.messages[0].content == "New system prompt"
    
    def test_get_system_prompt(self, agent):
        """Test getting default system prompt."""
        prompt = agent.get_system_prompt()
        
        assert 'AI assistant' in prompt
        assert 'job search' in prompt
    
    def test_clear_conversation(self, agent):
        """Test clearing conversation."""
        agent.initialize_conversation()
        agent.conversation.add_user_message("Test")
        agent.conversation.add_assistant_message("Response")
        
        agent.clear_conversation(keep_system=True)
        
        assert len(agent.conversation) == 1
        assert agent.conversation.messages[0].role == 'system'


class TestSendMessage:
    """Test sending messages to AI."""
    
    def test_send_message_basic(self, agent, mock_openai_client):
        """Test basic message sending."""
        response = agent.send_message("Hello")
        
        assert response == "Test response"
        assert mock_openai_client.chat.completions.create.called
        
        # Verify conversation updated
        assert len(agent.conversation) == 3  # system, user, assistant
    
    def test_send_message_initializes_conversation(self, agent):
        """Test that send_message initializes conversation if needed."""
        assert agent.conversation is None
        
        agent.send_message("Hello")
        
        assert agent.conversation is not None
    
    def test_send_message_with_tools(self, agent, mock_openai_client):
        """Test message with tool definitions."""
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_jobs",
                    "description": "Search for jobs",
                }
            }
        ]
        
        agent.send_message("Find Python jobs", tools=tools)
        
        # Verify tools passed to API
        call_kwargs = mock_openai_client.chat.completions.create.call_args[1]
        assert 'tools' in call_kwargs
        assert call_kwargs['tools'] == tools
    
    def test_send_message_handles_openai_error(self, agent, mock_openai_client):
        """Test error handling for OpenAI errors."""
        from openai import OpenAIError
        
        mock_openai_client.chat.completions.create.side_effect = OpenAIError('API error')
        
        response = agent.send_message("Hello")
        
        assert 'apologize' in response.lower()
        assert 'trouble' in response.lower()
    
    def test_send_message_handles_general_error(self, agent, mock_openai_client):
        """Test error handling for general errors."""
        mock_openai_client.chat.completions.create.side_effect = Exception('Unexpected error')
        
        response = agent.send_message("Hello")
        
        assert 'apologize' in response.lower()
        assert 'error' in response.lower()


class TestFunctionCalling:
    """Test function calling support."""
    
    def test_add_function_result(self, agent):
        """Test adding function result to conversation."""
        agent.initialize_conversation()
        
        agent.add_function_result('search_jobs', '{"results": []}')
        
        # Should have system + function message
        assert len(agent.conversation) == 2
        assert agent.conversation.messages[1].role == 'function'
        assert agent.conversation.messages[1].name == 'search_jobs'


class TestAvailability:
    """Test AI service availability check."""
    
    def test_is_available_success(self, agent, mock_openai_client):
        """Test availability check when service is up."""
        mock_openai_client.models.list.return_value = []
        
        assert agent.is_available() is True
    
    def test_is_available_failure(self, agent, mock_openai_client):
        """Test availability check when service is down."""
        mock_openai_client.models.list.side_effect = Exception('Connection error')
        
        assert agent.is_available() is False


class TestUtilityMethods:
    """Test utility methods."""
    
    def test_get_conversation_summary(self, agent):
        """Test getting conversation summary."""
        agent.initialize_conversation()
        agent.send_message("Hello")
        
        summary = agent.get_conversation_summary()
        
        assert 'messages' in summary.lower()
        assert 'tokens' in summary.lower()
    
    def test_get_conversation_summary_no_conversation(self, agent):
        """Test summary when no conversation."""
        summary = agent.get_conversation_summary()
        
        assert 'no active conversation' in summary.lower()
