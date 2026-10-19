"""
Conversation Buffer
===================
Manages conversation context and history for AI agents.
Implements sliding window memory to stay within token limits.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class Message:
    """Represents a single message in the conversation."""
    role: str  # 'system', 'user', 'assistant', 'function'
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    function_call: Optional[Dict[str, Any]] = None
    name: Optional[str] = None  # For function messages
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to OpenAI API format."""
        msg = {
            'role': self.role,
            'content': self.content,
        }
        if self.function_call:
            msg['function_call'] = self.function_call
        if self.name:
            msg['name'] = self.name
        return msg


class ConversationBuffer:
    """
    Manages conversation history with automatic truncation to stay within token limits.
    
    Features:
    - Sliding window memory (keeps recent messages)
    - System message always included
    - Token estimation to prevent exceeding limits
    - Message persistence support
    """
    
    def __init__(
        self,
        max_messages: int = 20,
        max_tokens: int = 4000,
        system_message: Optional[str] = None
    ):
        """
        Initialize conversation buffer.
        
        Args:
            max_messages: Maximum number of messages to keep
            max_tokens: Approximate token limit for conversation
            system_message: Initial system message (always preserved)
        """
        self.max_messages = max_messages
        self.max_tokens = max_tokens
        self.messages: List[Message] = []
        
        if system_message:
            self.add_system_message(system_message)
    
    def add_system_message(self, content: str) -> None:
        """Add or update system message (always first)."""
        system_msg = Message(role='system', content=content)
        if self.messages and self.messages[0].role == 'system':
            self.messages[0] = system_msg
        else:
            self.messages.insert(0, system_msg)
    
    def add_user_message(self, content: str) -> None:
        """Add user message to conversation."""
        self.messages.append(Message(role='user', content=content))
        self._truncate_if_needed()
    
    def add_assistant_message(
        self,
        content: str,
        function_call: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add assistant message to conversation."""
        self.messages.append(
            Message(role='assistant', content=content, function_call=function_call)
        )
        self._truncate_if_needed()
    
    def add_function_message(self, name: str, content: str) -> None:
        """Add function result message to conversation."""
        self.messages.append(
            Message(role='function', content=content, name=name)
        )
        self._truncate_if_needed()
    
    def get_messages(self) -> List[Dict[str, Any]]:
        """Get all messages in OpenAI API format."""
        return [msg.to_dict() for msg in self.messages]
    
    def get_recent_messages(self, n: int) -> List[Dict[str, Any]]:
        """Get n most recent messages (excluding system)."""
        non_system = [msg for msg in self.messages if msg.role != 'system']
        recent = non_system[-n:] if n < len(non_system) else non_system
        
        # Always include system message first
        result = []
        if self.messages and self.messages[0].role == 'system':
            result.append(self.messages[0].to_dict())
        result.extend([msg.to_dict() for msg in recent])
        
        return result
    
    def clear(self, keep_system: bool = True) -> None:
        """Clear conversation history."""
        if keep_system and self.messages and self.messages[0].role == 'system':
            system_msg = self.messages[0]
            self.messages = [system_msg]
        else:
            self.messages = []
    
    def _truncate_if_needed(self) -> None:
        """Truncate messages if exceeding limits (preserves system message)."""
        if len(self.messages) <= self.max_messages:
            return
        
        # Keep system message + most recent messages
        if self.messages and self.messages[0].role == 'system':
            system_msg = self.messages[0]
            other_messages = self.messages[1:]
            # Keep most recent messages that fit within limit
            keep_count = self.max_messages - 1
            self.messages = [system_msg] + other_messages[-keep_count:]
        else:
            self.messages = self.messages[-self.max_messages:]
    
    def estimate_tokens(self) -> int:
        """
        Estimate token count for current conversation.
        Uses rough approximation: ~4 characters per token.
        """
        total_chars = sum(len(msg.content) for msg in self.messages)
        return total_chars // 4
    
    def get_summary(self) -> str:
        """Get a text summary of the conversation."""
        if not self.messages:
            return "No messages in conversation."
        
        summary = [
            f"Conversation with {len(self.messages)} messages",
            f"Estimated tokens: {self.estimate_tokens()}",
            f"Started: {self.messages[0].timestamp.isoformat()}",
        ]
        
        if len(self.messages) > 1:
            summary.append(f"Last message: {self.messages[-1].timestamp.isoformat()}")
        
        return "\n".join(summary)
    
    def __len__(self) -> int:
        """Return number of messages."""
        return len(self.messages)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"ConversationBuffer(messages={len(self.messages)}, tokens~{self.estimate_tokens()})"
