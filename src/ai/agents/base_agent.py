"""
Base Agent
==========
Base class for all AI agents with common functionality.
Provides OpenAI integration, conversation management, and error handling.
"""

import logging
from typing import Dict, Any, Optional, List, AsyncIterator
from datetime import datetime
from openai import OpenAI, OpenAIError
from openai.types.chat import ChatCompletionChunk

from ..memory.conversation_buffer import ConversationBuffer
from ..prompts.base_prompts import SYSTEM_PROMPT_BASE, ERROR_HANDLING_PROMPT


logger = logging.getLogger(__name__)


class BaseAgent:
    """
    Base AI agent with OpenAI integration and common functionality.

    All specific agents (job search, CV generation, etc.) inherit from this class.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float,
        max_tokens: int,
        timeout: int,
    ):
        """
        Initialize base agent.

        Args:
            api_key: OpenAI API key
            model: Model to use (gpt-4-turbo-preview, gpt-3.5-turbo, etc.)
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens in response
            timeout: Request timeout in seconds
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens  # Max tokens for API response
        self.timeout = timeout

        # Conversation memory limits (set by service, defaults for tests)
        self.max_messages = 20
        self.max_tokens_memory = 4000

        # Initialize OpenAI client
        try:
            self.client = OpenAI(api_key=api_key, timeout=timeout)
            logger.info(f"Initialized {self.__class__.__name__} with model {model}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise

        # Conversation memory (will be set per conversation)
        self.conversation: Optional[ConversationBuffer] = None

    def set_system_prompt(self, prompt: str) -> None:
        """Set or update system prompt for this agent."""
        if self.conversation is None:
            self.conversation = ConversationBuffer(system_message=prompt)
        else:
            self.conversation.add_system_message(prompt)

    def get_system_prompt(self) -> str:
        """
        Get the system prompt for this agent.
        Override in subclasses to provide agent-specific prompts.
        """
        current_date = datetime.utcnow().strftime("%Y-%m-%d")
        return SYSTEM_PROMPT_BASE.format(current_date=current_date)

    def initialize_conversation(
        self,
        system_prompt: Optional[str] = None,
        max_messages: Optional[int] = None,
        max_tokens: Optional[int] = None,
    ) -> None:
        """
        Initialize a new conversation.

        Args:
            system_prompt: Custom system prompt (uses default if None)
            max_messages: Maximum messages to keep in memory (uses config if None)
            max_tokens: Maximum tokens for conversation (uses config if None)
        """
        prompt = system_prompt or self.get_system_prompt()
        self.conversation = ConversationBuffer(
            max_messages=max_messages or self.max_messages,
            max_tokens=max_tokens or self.max_tokens_memory,
            system_message=prompt,
        )
        logger.debug(f"Initialized conversation for {self.__class__.__name__}")

    def send_message(
        self,
        message: str,
        user_context: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Send a message and get response.

        Args:
            message: User message
            user_context: Additional context (profile, preferences, etc.)
            tools: Tool definitions for function calling

        Returns:
            Assistant response text
        """
        if self.conversation is None:
            self.initialize_conversation()

        # Add user message
        self.conversation.add_user_message(message)

        try:
            # Prepare messages
            messages = self.conversation.get_messages()

            # Call OpenAI API
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }

            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            response = self.client.chat.completions.create(**kwargs)

            # Extract response
            assistant_message = response.choices[0].message
            content = assistant_message.content or ""

            # Handle function calling
            function_call = None
            if (
                hasattr(assistant_message, "tool_calls")
                and assistant_message.tool_calls
            ):
                function_call = {
                    "name": assistant_message.tool_calls[0].function.name,
                    "arguments": assistant_message.tool_calls[0].function.arguments,
                }

            # Add to conversation
            self.conversation.add_assistant_message(content, function_call)

            logger.info(
                f"Generated response: {len(content)} chars, tokens used: {response.usage.total_tokens}"
            )

            return content

        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            error_msg = "I apologize, but I'm having trouble connecting to the AI service. Please try again in a moment."
            self.conversation.add_assistant_message(error_msg)
            return error_msg

        except Exception as e:
            logger.error(f"Unexpected error in send_message: {e}", exc_info=True)
            error_msg = (
                "I apologize, but an unexpected error occurred. Please try again."
            )
            self.conversation.add_assistant_message(error_msg)
            return error_msg

    async def send_message_stream(
        self,
        message: str,
        user_context: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        """
        Send a message and stream response chunks.

        Args:
            message: User message
            user_context: Additional context
            tools: Tool definitions for function calling

        Yields:
            Response chunks as they arrive
        """
        if self.conversation is None:
            self.initialize_conversation()

        # Add user message
        self.conversation.add_user_message(message)

        try:
            # Prepare messages
            messages = self.conversation.get_messages()

            # Call OpenAI API with streaming
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": True,
            }

            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            full_response = ""

            stream = self.client.chat.completions.create(**kwargs)

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content

            # Add complete response to conversation
            self.conversation.add_assistant_message(full_response)

            logger.info(f"Streamed response: {len(full_response)} chars")

        except OpenAIError as e:
            logger.error(f"OpenAI API error during streaming: {e}")
            error_msg = (
                "I apologize, but I'm having trouble connecting to the AI service."
            )
            self.conversation.add_assistant_message(error_msg)
            yield error_msg

        except Exception as e:
            logger.error(f"Unexpected error in send_message_stream: {e}", exc_info=True)
            error_msg = "I apologize, but an unexpected error occurred."
            self.conversation.add_assistant_message(error_msg)
            yield error_msg

    def send_message_stream_sync(
        self,
        message: str,
        user_context: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Send a message and stream response chunks (synchronous version for Flask).

        Args:
            message: User message
            user_context: Additional context
            tools: Tool definitions for function calling

        Yields:
            Response chunks as they arrive
        """
        if self.conversation is None:
            self.initialize_conversation()

        # Add user message
        self.conversation.add_user_message(message)

        try:
            # Prepare messages
            messages = self.conversation.get_messages()

            # Call OpenAI API with streaming
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": True,
            }

            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            full_response = ""

            stream = self.client.chat.completions.create(**kwargs)

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content

            # Add complete response to conversation
            self.conversation.add_assistant_message(full_response)

            logger.info(f"Streamed response (sync): {len(full_response)} chars")

        except OpenAIError as e:
            logger.error(f"OpenAI API error during streaming: {e}")
            error_msg = (
                "I apologize, but I'm having trouble connecting to the AI service."
            )
            self.conversation.add_assistant_message(error_msg)
            yield error_msg

        except Exception as e:
            logger.error(
                f"Unexpected error in send_message_stream_sync: {e}", exc_info=True
            )
            error_msg = "I apologize, but an unexpected error occurred."
            self.conversation.add_assistant_message(error_msg)
            yield error_msg

    def add_function_result(self, function_name: str, result: str) -> None:
        """
        Add function call result to conversation.

        Args:
            function_name: Name of the function that was called
            result: Function execution result (JSON string)
        """
        if self.conversation:
            self.conversation.add_function_message(function_name, result)

    def clear_conversation(self, keep_system: bool = True) -> None:
        """Clear conversation history."""
        if self.conversation:
            self.conversation.clear(keep_system=keep_system)
            logger.debug(f"Cleared conversation for {self.__class__.__name__}")

    def get_conversation_summary(self) -> str:
        """Get summary of current conversation."""
        if self.conversation:
            return self.conversation.get_summary()
        return "No active conversation."

    def is_available(self) -> bool:
        """
        Check if AI service is available.

        Returns:
            True if OpenAI API is accessible
        """
        try:
            # Try a simple API call
            self.client.models.list()
            return True
        except Exception as e:
            logger.warning(f"AI service unavailable: {e}")
            return False
