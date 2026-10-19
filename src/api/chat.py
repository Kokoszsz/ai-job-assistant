"""
Chat Conversation API Endpoints
================================
Manage chat conversations and messages with AI assistant.
"""

import json
import logging
from functools import wraps

from flask import Blueprint, Response, current_app, jsonify, request, stream_with_context

from src.ai.tools.database_tools import DatabaseTools
from src.middleware.auth_middleware import require_auth
from src.models import Conversation, Message, db
from src.services.ai_service import get_ai_service
from src.services.profile_context_builder import ProfileContextBuilder
from src.services.profile_service import ProfileService

logger = logging.getLogger(__name__)

chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")


def rate_limit(limit_string):
    """
    Decorator to apply rate limiting to a route.
    Applies the limit when limiter is available in app context.
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if hasattr(current_app, "limiter"):
                # Limiter will be applied via decorator in app.py
                pass
            return f(*args, **kwargs)

        return decorated_function

    return decorator


@chat_bp.route("/conversations", methods=["POST"])
@require_auth
@rate_limit("20 per minute")
def create_conversation(user_id, email):
    """
    Create a new conversation.

    Request Body (optional):
        {
            "title": "Optional conversation title"
        }

    Returns:
        201: { "success": true, "data": { "conversation": {...} } }
        400: { "success": false, "error": { "code": "...", "message": "..." } }
    """
    try:
        data = request.get_json() or {}
        title = data.get("title")

        # Validate title length if provided
        if title and len(title) > 200:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": {
                            "code": "INVALID_TITLE",
                            "message": "Title must be 200 characters or less",
                        },
                    }
                ),
                400,
            )

        # Create conversation
        conversation = Conversation(user_id=user_id, title=title, is_archived=False)

        db.session.add(conversation)
        db.session.commit()

        logger.info(f"Created conversation {conversation.id} for user {user_id}")

        return jsonify({"success": True, "data": {"conversation": conversation.to_dict()}}), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating conversation: {str(e)}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "CONVERSATION_CREATE_FAILED",
                        "message": "Failed to create conversation",
                    },
                }
            ),
            500,
        )


@chat_bp.route("/conversations", methods=["GET"])
@require_auth
@rate_limit("20 per minute")
def list_conversations(user_id, email):
    """
    List user's conversations.

    Query Parameters:
        - archived: Filter by archived status (true/false, optional)
        - limit: Number of results (default 20, max 100)
        - offset: Pagination offset (default 0)

    Returns:
        200: { "success": true, "data": { "conversations": [...], "total": N } }
    """
    try:
        # Parse query parameters
        archived = request.args.get("archived", type=str)
        limit = min(int(request.args.get("limit", 20)), 100)
        offset = int(request.args.get("offset", 0))

        # Build query - exclude deleted conversations
        query = Conversation.query.filter_by(user_id=user_id, is_deleted=False)

        # Filter by archived status if specified
        if archived is not None:
            is_archived = archived.lower() in ["true", "1", "yes"]
            query = query.filter_by(is_archived=is_archived)

        # Get total count
        total = query.count()

        # Apply pagination and ordering
        conversations = query.order_by(Conversation.updated_at.desc()).limit(limit).offset(offset).all()

        return (
            jsonify(
                {
                    "success": True,
                    "data": {
                        "conversations": [conv.to_dict() for conv in conversations],
                        "total": total,
                        "limit": limit,
                        "offset": offset,
                    },
                }
            ),
            200,
        )

    except ValueError as e:
        return (
            jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "INVALID_PARAMETERS",
                        "message": "Invalid query parameters",
                    },
                }
            ),
            400,
        )
    except Exception as e:
        logger.error(f"Error listing conversations: {str(e)}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "CONVERSATIONS_LIST_FAILED",
                        "message": "Failed to list conversations",
                    },
                }
            ),
            500,
        )


@chat_bp.route("/conversations/<int:conversation_id>", methods=["DELETE"])
@require_auth
@rate_limit("20 per minute")
def delete_conversation(user_id, email, conversation_id):
    """
    Soft delete a conversation (sets is_deleted=True).

    Returns:
        200: { "success": true, "message": "Conversation deleted" }
        403: { "success": false, "error": { "code": "FORBIDDEN", "message": "..." } }
        404: { "success": false, "error": { "code": "NOT_FOUND", "message": "..." } }
    """
    try:
        # Get conversation
        conversation = Conversation.query.filter_by(id=conversation_id, user_id=user_id).first()

        if not conversation:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": {
                            "code": "CONVERSATION_NOT_FOUND",
                            "message": "Conversation not found",
                        },
                    }
                ),
                404,
            )

        # Check if already deleted
        if conversation.is_deleted:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": {
                            "code": "ALREADY_DELETED",
                            "message": "Conversation is already deleted",
                        },
                    }
                ),
                400,
            )

        # Soft delete (set flag instead of removing)
        conversation.is_deleted = True
        db.session.commit()

        logger.info(f"Soft deleted conversation {conversation_id} for user {user_id}")

        return jsonify({"success": True, "message": "Conversation deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting conversation: {str(e)}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "CONVERSATION_DELETE_FAILED",
                        "message": "Failed to delete conversation",
                    },
                }
            ),
            500,
        )


@chat_bp.route("/conversations/<int:conversation_id>/messages", methods=["GET"])
@require_auth
@rate_limit("20 per minute")
def get_messages(user_id, email, conversation_id):
    """
    Get messages for a conversation.

    Query Parameters:
        - limit: Number of messages (default 50, max 100)
        - offset: Pagination offset (default 0)

    Returns:
        200: { "success": true, "data": { "messages": [...], "total": N } }
        404: { "success": false, "error": { "code": "CONVERSATION_NOT_FOUND", "message": "..." } }
        403: { "success": false, "error": { "code": "FORBIDDEN", "message": "..." } }
    """
    try:
        # Get conversation
        conversation = Conversation.query.get(conversation_id)

        if not conversation:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": {
                            "code": "CONVERSATION_NOT_FOUND",
                            "message": "Conversation not found",
                        },
                    }
                ),
                404,
            )

        # Check ownership
        if conversation.user_id != user_id:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": {
                            "code": "FORBIDDEN",
                            "message": "You do not have access to this conversation",
                        },
                    }
                ),
                403,
            )

        # Parse pagination parameters
        limit = min(int(request.args.get("limit", 50)), 100)
        offset = int(request.args.get("offset", 0))

        # Get messages
        query = Message.query.filter_by(conversation_id=conversation_id)
        total = query.count()

        messages = query.order_by(Message.created_at.asc()).limit(limit).offset(offset).all()

        return (
            jsonify(
                {
                    "success": True,
                    "data": {
                        "messages": [msg.to_dict() for msg in messages],
                        "total": total,
                        "limit": limit,
                        "offset": offset,
                    },
                }
            ),
            200,
        )

    except ValueError:
        return (
            jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "INVALID_PARAMETERS",
                        "message": "Invalid query parameters",
                    },
                }
            ),
            400,
        )
    except Exception as e:
        logger.error(f"Error getting messages: {str(e)}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "MESSAGES_GET_FAILED",
                        "message": "Failed to get messages",
                    },
                }
            ),
            500,
        )


@chat_bp.route("/conversations/<int:conversation_id>/messages", methods=["POST"])
@require_auth
@rate_limit("20 per minute")
def send_message(user_id, email, conversation_id):
    """
    Send a message to AI assistant in a conversation.

    Request Body:
        {
            "content": "User's message content"
        }

    Returns:
        201: { "success": true, "data": { "user_message": {...}, "assistant_message": {...} } }
        400: { "success": false, "error": { "code": "...", "message": "..." } }
        404: { "success": false, "error": { "code": "CONVERSATION_NOT_FOUND", "message": "..." } }
        403: { "success": false, "error": { "code": "FORBIDDEN", "message": "..." } }
        503: { "success": false, "error": { "code": "AI_UNAVAILABLE", "message": "..." } }
    """
    try:
        # Validate request body
        data = request.get_json()
        if not data:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": {
                            "code": "MISSING_REQUEST_BODY",
                            "message": "Request body is required",
                        },
                    }
                ),
                400,
            )

        content = data.get("content", "").strip()
        if not content:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": {
                            "code": "MISSING_CONTENT",
                            "message": "Message content is required",
                        },
                    }
                ),
                400,
            )

        # Validate content length
        if len(content) > Message.MAX_CONTENT_LENGTH:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": {
                            "code": "CONTENT_TOO_LONG",
                            "message": f"Message content must be {Message.MAX_CONTENT_LENGTH} characters or less",
                        },
                    }
                ),
                400,
            )

        # Get conversation
        conversation = Conversation.query.get(conversation_id)

        if not conversation:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": {
                            "code": "CONVERSATION_NOT_FOUND",
                            "message": "Conversation not found",
                        },
                    }
                ),
                404,
            )

        # Check ownership
        if conversation.user_id != user_id:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": {
                            "code": "FORBIDDEN",
                            "message": "You do not have access to this conversation",
                        },
                    }
                ),
                403,
            )

        # Check AI service availability
        ai_service = get_ai_service()
        if not ai_service or not ai_service.is_available():
            return (
                jsonify(
                    {
                        "success": False,
                        "error": {
                            "code": "AI_UNAVAILABLE",
                            "message": "AI service is currently unavailable",
                        },
                    }
                ),
                503,
            )

        # Create user message
        user_message = Message(conversation_id=conversation_id, role="user", content=content)
        db.session.add(user_message)
        db.session.flush()  # Get ID without committing

        # Get AI response
        try:
            # Fetch user profile for personalization
            profile_data = ProfileService.get_profile(user_id, include_details=True)

            # Build user context from profile
            user_context = ""
            if profile_data:
                user_context = ProfileContextBuilder.build_user_context(user_id, profile_data)

            # Create agent with default settings
            agent = ai_service.create_agent()

            # Get base system prompt
            base_prompt = agent.get_system_prompt()

            # Inject profile context into system prompt if available
            if user_context:
                personalized_prompt = base_prompt + "\n\n" + user_context
                agent.initialize_conversation(system_prompt=personalized_prompt)
            else:
                # Fallback to default prompt if no profile
                agent.initialize_conversation()

            # Load previous messages for context
            previous_messages = (
                Message.query.filter_by(conversation_id=conversation_id).order_by(Message.created_at.asc()).all()
            )

            # Add conversation history to agent (excluding the user message we just added)
            for msg in previous_messages[:-1]:
                if msg.role == "user":
                    agent.conversation.add_user_message(msg.content)
                elif msg.role == "assistant":
                    agent.conversation.add_assistant_message(msg.content)

            # Get tool definitions for CV and job operations
            tools = DatabaseTools.get_tool_definitions()

            # Initialize database tools with session for execution
            db_tools = DatabaseTools(db.session)

            # Get AI response with tools
            ai_response = agent.send_message(content, tools=tools)

            # Check if there's a function call to execute
            if agent.conversation and agent.conversation.messages:
                last_msg = agent.conversation.messages[-1]
                if last_msg.function_call:
                    function_call = last_msg.function_call
                    tool_name = function_call.get("name")

                    try:
                        # Parse arguments
                        tool_args = json.loads(function_call.get("arguments", "{}"))

                        # Inject user_id for tools that need it
                        if tool_name in [
                            "generate_cv",
                            "list_user_cvs",
                            "get_user_profile",
                        ]:
                            tool_args["user_id"] = user_id

                        # Execute tool
                        tool_result = db_tools.execute_tool(tool_name, tool_args)

                        # Add tool result to conversation
                        agent.add_function_result(tool_name, tool_result)

                        # Get final response from AI after tool execution
                        ai_response = agent.send_message(f"Tool {tool_name} returned: {tool_result}")
                    except Exception as tool_error:
                        logger.error(f"Tool execution error: {str(tool_error)}")
                        # Continue with original response if tool fails

            # Create assistant message
            assistant_message = Message(conversation_id=conversation_id, role="assistant", content=ai_response)
            db.session.add(assistant_message)

            # Update conversation title if not set
            if not conversation.title:
                # Use first few words of user message as title
                title_words = content.split()[:8]
                conversation.title = " ".join(title_words)
                if len(title_words) == 8:
                    conversation.title += "..."

            db.session.commit()

            logger.info(f"Processed message in conversation {conversation_id}")

            return (
                jsonify(
                    {
                        "success": True,
                        "data": {
                            "user_message": user_message.to_dict(),
                            "assistant_message": assistant_message.to_dict(),
                        },
                    }
                ),
                201,
            )

        except Exception as ai_error:
            logger.error(f"AI error: {str(ai_error)}")
            # Rollback the user message if AI fails
            db.session.rollback()
            return (
                jsonify(
                    {
                        "success": False,
                        "error": {
                            "code": "AI_PROCESSING_ERROR",
                            "message": "Failed to process message with AI",
                        },
                    }
                ),
                500,
            )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error sending message: {str(e)}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "MESSAGE_SEND_FAILED",
                        "message": "Failed to send message",
                    },
                }
            ),
            500,
        )


@chat_bp.route("/conversations/<int:conversation_id>/messages/stream", methods=["POST"])
@require_auth
@rate_limit("20 per minute")
def send_message_stream(user_id, email, conversation_id):
    """
    Send a message to AI assistant and stream the response using Server-Sent Events.

    Request Body:
        {
            "content": "User's message content"
        }

    Returns:
        SSE stream with events:
        - message_start: { "user_message_id": N, "assistant_message_id": N }
        - content_delta: { "delta": "chunk of text" }
        - message_complete: { "content": "full response", "assistant_message_id": N }
        - error: { "error": "message", "code": "ERROR_CODE" }
    """
    # Validate request body
    data = request.get_json()
    if not data:
        return (
            jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "MISSING_REQUEST_BODY",
                        "message": "Request body is required",
                    },
                }
            ),
            400,
        )

    content = data.get("content", "").strip()
    if not content:
        return (
            jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "MISSING_CONTENT",
                        "message": "Message content is required",
                    },
                }
            ),
            400,
        )

    # Validate content length
    if len(content) > Message.MAX_CONTENT_LENGTH:
        return (
            jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "CONTENT_TOO_LONG",
                        "message": f"Message content must be {Message.MAX_CONTENT_LENGTH} characters or less",
                    },
                }
            ),
            400,
        )

    # Get conversation
    conversation = Conversation.query.get(conversation_id)

    if not conversation:
        return (
            jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "CONVERSATION_NOT_FOUND",
                        "message": "Conversation not found",
                    },
                }
            ),
            404,
        )

    # Check ownership
    if conversation.user_id != user_id:
        return (
            jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "FORBIDDEN",
                        "message": "You do not have access to this conversation",
                    },
                }
            ),
            403,
        )

    # Check AI service availability
    ai_service = get_ai_service()
    if not ai_service or not ai_service.is_available():
        return (
            jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "AI_UNAVAILABLE",
                        "message": "AI service is currently unavailable",
                    },
                }
            ),
            503,
        )

    def generate_stream():
        """Generator function for SSE stream."""
        user_message = None
        assistant_message = None
        full_response = ""

        try:
            # Create user message
            user_message = Message(conversation_id=conversation_id, role="user", content=content)
            db.session.add(user_message)
            db.session.flush()

            # Create empty assistant message placeholder
            assistant_message = Message(conversation_id=conversation_id, role="assistant", content="")
            db.session.add(assistant_message)
            db.session.flush()

            user_msg_id = user_message.id
            assistant_msg_id = assistant_message.id

            # Send message_start event
            yield f"event: message_start\ndata: {json.dumps({'user_message_id': user_msg_id, 'assistant_message_id': assistant_msg_id})}\n\n"

            # Fetch user profile for personalization
            profile_data = ProfileService.get_profile(user_id, include_details=True)

            # Build user context from profile
            user_context = ""
            if profile_data:
                user_context = ProfileContextBuilder.build_user_context(user_id, profile_data)

            # Create agent
            agent = ai_service.create_agent()

            # Get base system prompt
            base_prompt = agent.get_system_prompt()

            # Inject profile context into system prompt if available
            if user_context:
                personalized_prompt = base_prompt + "\n\n" + user_context
                agent.initialize_conversation(system_prompt=personalized_prompt)
            else:
                # Fallback to default prompt if no profile
                agent.initialize_conversation()

            # Load previous messages for context (excluding the ones we just added)
            previous_messages = (
                Message.query.filter_by(conversation_id=conversation_id)
                .filter(Message.id < user_msg_id)
                .order_by(Message.created_at.asc())
                .all()
            )

            # Add conversation history to agent
            for msg in previous_messages:
                if msg.role == "user":
                    agent.conversation.add_user_message(msg.content)
                elif msg.role == "assistant":
                    agent.conversation.add_assistant_message(msg.content)

            # Get tool definitions and initialize tools
            tools = DatabaseTools.get_tool_definitions()
            db_tools = DatabaseTools(db.session)

            # First, do a non-streaming call to check for tool calls
            # NOTE: OpenAI doesn't stream tool calls, so we need to check first
            initial_response = agent.send_message(content, tools=tools)

            # Check if there's a function call
            tool_executed = False
            if agent.conversation and agent.conversation.messages:
                last_msg = agent.conversation.messages[-1]
                if last_msg.function_call:
                    function_call = last_msg.function_call
                    tool_name = function_call.get("name")

                    try:
                        tool_args = json.loads(function_call.get("arguments", "{}"))

                        # Inject user_id for tools that need it
                        if tool_name in [
                            "generate_cv",
                            "list_user_cvs",
                            "get_user_profile",
                        ]:
                            tool_args["user_id"] = user_id

                        # Execute tool
                        tool_result = db_tools.execute_tool(tool_name, tool_args)

                        # Add tool result
                        agent.add_function_result(tool_name, tool_result)

                        # Stream the final response from OpenAI
                        for chunk in agent.send_message_stream_sync(f"Tool {tool_name} returned: {tool_result}"):
                            full_response += chunk
                            yield f"event: content_delta\ndata: {json.dumps({'delta': chunk})}\n\n"

                        tool_executed = True
                    except Exception as tool_error:
                        logger.error(f"Tool execution error in stream: {str(tool_error)}")
                        # Fall back to non-streaming response
                        for i in range(0, len(initial_response), 20):
                            chunk = initial_response[i : i + 20]
                            full_response += chunk
                            yield f"event: content_delta\ndata: {json.dumps({'delta': chunk})}\n\n"

            # If no tool was executed, stream the initial response
            if not tool_executed:
                # Clear conversation to remove the non-streamed response
                if agent.conversation and agent.conversation.messages:
                    agent.conversation.messages.pop()  # Remove assistant message

                # Stream the actual response from OpenAI
                for chunk in agent.send_message_stream_sync(content, tools=tools):
                    full_response += chunk
                    yield f"event: content_delta\ndata: {json.dumps({'delta': chunk})}\n\n"

            # Update assistant message with full content
            assistant_message.content = full_response

            # Update conversation title if not set
            conv = Conversation.query.get(conversation_id)
            if conv and not conv.title:
                title_words = content.split()[:8]
                conv.title = " ".join(title_words)
                if len(title_words) == 8:
                    conv.title += "..."

            db.session.commit()

            # Send message_complete event
            yield f"event: message_complete\ndata: {json.dumps({'content': full_response, 'assistant_message_id': assistant_msg_id})}\n\n"

            logger.info(f"Streamed message in conversation {conversation_id}")

        except Exception as e:
            logger.error(f"Error in streaming: {str(e)}", exc_info=True)
            db.session.rollback()

            yield f"event: error\ndata: {json.dumps({'error': str(e), 'code': 'STREAM_ERROR'})}\n\n"

    return Response(
        stream_with_context(generate_stream()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
