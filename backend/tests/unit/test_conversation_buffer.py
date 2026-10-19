"""
Unit Tests: Conversation Buffer
================================
Tests for conversation memory management.
"""

import pytest
from datetime import datetime
from src.ai.memory.conversation_buffer import ConversationBuffer, Message


class TestMessage:
    """Test Message class."""
    
    def test_create_message(self):
        """Test message creation."""
        msg = Message(role='user', content='Hello')
        
        assert msg.role == 'user'
        assert msg.content == 'Hello'
        assert isinstance(msg.timestamp, datetime)
        assert msg.function_call is None
        assert msg.name is None
    
    def test_message_to_dict(self):
        """Test message conversion to dict."""
        msg = Message(role='assistant', content='Hi there')
        result = msg.to_dict()
        
        assert result == {'role': 'assistant', 'content': 'Hi there'}
    
    def test_message_with_function_call(self):
        """Test message with function call."""
        func_call = {'name': 'search_jobs', 'arguments': '{"keywords": "python"}'}
        msg = Message(role='assistant', content='', function_call=func_call)
        result = msg.to_dict()
        
        assert result['function_call'] == func_call
    
    def test_message_with_name(self):
        """Test function message with name."""
        msg = Message(role='function', content='{"results": []}', name='search_jobs')
        result = msg.to_dict()
        
        assert result['name'] == 'search_jobs'


class TestConversationBuffer:
    """Test ConversationBuffer class."""
    
    def test_initialization_empty(self):
        """Test buffer initialization without system message."""
        buffer = ConversationBuffer()
        
        assert len(buffer) == 0
        assert buffer.messages == []
    
    def test_initialization_with_system(self):
        """Test buffer initialization with system message."""
        buffer = ConversationBuffer(system_message='You are a helpful assistant.')
        
        assert len(buffer) == 1
        assert buffer.messages[0].role == 'system'
        assert buffer.messages[0].content == 'You are a helpful assistant.'
    
    def test_add_user_message(self):
        """Test adding user message."""
        buffer = ConversationBuffer()
        buffer.add_user_message('Hello')
        
        assert len(buffer) == 1
        assert buffer.messages[0].role == 'user'
        assert buffer.messages[0].content == 'Hello'
    
    def test_add_assistant_message(self):
        """Test adding assistant message."""
        buffer = ConversationBuffer()
        buffer.add_assistant_message('Hi there')
        
        assert len(buffer) == 1
        assert buffer.messages[0].role == 'assistant'
        assert buffer.messages[0].content == 'Hi there'
    
    def test_add_function_message(self):
        """Test adding function message."""
        buffer = ConversationBuffer()
        buffer.add_function_message('search_jobs', '{"results": []}')
        
        assert len(buffer) == 1
        assert buffer.messages[0].role == 'function'
        assert buffer.messages[0].name == 'search_jobs'
    
    def test_get_messages(self):
        """Test getting all messages in API format."""
        buffer = ConversationBuffer(system_message='System prompt')
        buffer.add_user_message('User message')
        buffer.add_assistant_message('Assistant response')
        
        messages = buffer.get_messages()
        
        assert len(messages) == 3
        assert messages[0]['role'] == 'system'
        assert messages[1]['role'] == 'user'
        assert messages[2]['role'] == 'assistant'
    
    def test_get_recent_messages(self):
        """Test getting recent messages."""
        buffer = ConversationBuffer(system_message='System prompt')
        
        # Add 5 user/assistant pairs
        for i in range(5):
            buffer.add_user_message(f'User {i}')
            buffer.add_assistant_message(f'Assistant {i}')
        
        # Get 3 most recent
        recent = buffer.get_recent_messages(3)
        
        # Should have system + 3 most recent messages
        assert len(recent) == 4  # system + 3 recent
        assert recent[0]['role'] == 'system'
        # Most recent 3 should be: Assistant 4, User 4, Assistant 3
        assert 'Assistant 4' in recent[1]['content'] or 'Assistant 3' in recent[1]['content']
    
    def test_clear_conversation(self):
        """Test clearing conversation."""
        buffer = ConversationBuffer(system_message='System prompt')
        buffer.add_user_message('User message')
        buffer.add_assistant_message('Response')
        
        buffer.clear(keep_system=True)
        
        assert len(buffer) == 1
        assert buffer.messages[0].role == 'system'
    
    def test_clear_all(self):
        """Test clearing all messages."""
        buffer = ConversationBuffer(system_message='System prompt')
        buffer.add_user_message('User message')
        
        buffer.clear(keep_system=False)
        
        assert len(buffer) == 0
    
    def test_truncate_on_max_messages(self):
        """Test automatic truncation at max messages."""
        buffer = ConversationBuffer(max_messages=5, system_message='System')
        
        # Add 10 messages (should keep only 5 including system)
        for i in range(10):
            buffer.add_user_message(f'Message {i}')
        
        assert len(buffer) <= 5
        assert buffer.messages[0].role == 'system'  # System always preserved
        # Most recent messages kept
        assert 'Message 9' in buffer.messages[-1].content
    
    def test_estimate_tokens(self):
        """Test token estimation."""
        buffer = ConversationBuffer()
        buffer.add_user_message('This is a test message')
        buffer.add_assistant_message('This is a response')
        
        tokens = buffer.estimate_tokens()
        
        # Rough estimate: ~4 chars per token
        assert tokens > 0
        assert tokens < 100  # Short conversation
    
    def test_add_system_message_updates_existing(self):
        """Test that adding system message updates the first one."""
        buffer = ConversationBuffer(system_message='Original system')
        buffer.add_user_message('User message')
        
        buffer.add_system_message('Updated system')
        
        assert len(buffer) == 2  # system + user
        assert buffer.messages[0].content == 'Updated system'
    
    def test_get_summary(self):
        """Test conversation summary."""
        buffer = ConversationBuffer(system_message='System')
        buffer.add_user_message('Hello')
        buffer.add_assistant_message('Hi')
        
        summary = buffer.get_summary()
        
        assert 'messages' in summary.lower()
        assert 'tokens' in summary.lower()
    
    def test_repr(self):
        """Test string representation."""
        buffer = ConversationBuffer()
        buffer.add_user_message('Test')
        
        repr_str = repr(buffer)
        
        assert 'ConversationBuffer' in repr_str
        assert 'messages=1' in repr_str
