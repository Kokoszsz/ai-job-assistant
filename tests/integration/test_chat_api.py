"""
Integration Tests: Chat API
===========================
Test chat conversation and message endpoints.
"""

import json
from datetime import datetime

import pytest

from src.app import create_app
from src.models import Conversation, Message, Profile, User, db
from src.services.auth_service import AuthService


@pytest.fixture
def app():
    """Create test Flask app."""
    app = create_app("testing")

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def test_user(app):
    """Create a test user with profile."""
    user = User(email="chatuser@example.com", name="Chat Test User", is_active=True)
    user.set_password("SecurePass123")
    db.session.add(user)
    db.session.commit()

    profile = Profile(user_id=user.id)
    db.session.add(profile)
    db.session.commit()

    return user


@pytest.fixture
def auth_token(test_user):
    """Generate JWT token for test user."""
    auth_service = AuthService()
    token = auth_service.generate_access_token(test_user.id, test_user.email)
    return token


@pytest.fixture
def auth_headers(auth_token):
    """Create authorization headers."""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestCreateConversation:
    """Test POST /api/chat/conversations"""

    def test_create_conversation_success(self, client, auth_headers):
        """Test successful conversation creation."""
        response = client.post(
            "/api/chat/conversations",
            headers=auth_headers,
            json={"title": "My First Chat"},
        )

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["success"] is True
        assert "conversation" in data["data"]

        conversation = data["data"]["conversation"]
        assert conversation["title"] == "My First Chat"
        assert conversation["is_archived"] is False
        assert conversation["message_count"] == 0
        assert "id" in conversation
        assert "created_at" in conversation

    def test_create_conversation_without_title(self, client, auth_headers):
        """Test conversation creation without title."""
        response = client.post("/api/chat/conversations", headers=auth_headers, json={})

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["data"]["conversation"]["title"] is None

    def test_create_conversation_title_too_long(self, client, auth_headers):
        """Test conversation creation with title exceeding max length."""
        long_title = "A" * 201  # Exceeds 200 char limit

        response = client.post("/api/chat/conversations", headers=auth_headers, json={"title": long_title})

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_TITLE"

    def test_create_conversation_unauthorized(self, client):
        """Test conversation creation without authentication."""
        response = client.post("/api/chat/conversations", json={"title": "Test"})

        assert response.status_code == 401


class TestListConversations:
    """Test GET /api/chat/conversations"""

    @pytest.fixture(autouse=True)
    def setup_conversations(self, app, test_user):
        """Create test conversations."""
        # Create 3 active conversations
        for i in range(3):
            conv = Conversation(user_id=test_user.id, title=f"Conversation {i + 1}", is_archived=False)
            db.session.add(conv)

        # Create 2 archived conversations
        for i in range(2):
            conv = Conversation(user_id=test_user.id, title=f"Archived {i + 1}", is_archived=True)
            db.session.add(conv)

        db.session.commit()

    def test_list_all_conversations(self, client, auth_headers):
        """Test listing all conversations."""
        response = client.get("/api/chat/conversations", headers=auth_headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["data"]["total"] == 5
        assert len(data["data"]["conversations"]) == 5

    def test_list_active_conversations_only(self, client, auth_headers):
        """Test listing only active conversations."""
        response = client.get("/api/chat/conversations?archived=false", headers=auth_headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["data"]["total"] == 3
        assert all(not conv["is_archived"] for conv in data["data"]["conversations"])

    def test_list_archived_conversations_only(self, client, auth_headers):
        """Test listing only archived conversations."""
        response = client.get("/api/chat/conversations?archived=true", headers=auth_headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["data"]["total"] == 2
        assert all(conv["is_archived"] for conv in data["data"]["conversations"])

    def test_list_conversations_with_pagination(self, client, auth_headers):
        """Test pagination of conversation list."""
        response = client.get("/api/chat/conversations?limit=2&offset=0", headers=auth_headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert len(data["data"]["conversations"]) == 2
        assert data["data"]["limit"] == 2
        assert data["data"]["offset"] == 0
        assert data["data"]["total"] == 5

    def test_list_conversations_unauthorized(self, client):
        """Test listing conversations without authentication."""
        response = client.get("/api/chat/conversations")
        assert response.status_code == 401


class TestGetMessages:
    """Test GET /api/chat/conversations/{id}/messages"""

    @pytest.fixture
    def conversation(self, test_user):
        """Create a conversation with messages."""
        conv = Conversation(user_id=test_user.id, title="Test Conversation")
        db.session.add(conv)
        db.session.flush()

        # Add some messages
        for i in range(5):
            msg = Message(
                conversation_id=conv.id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i + 1}",
            )
            db.session.add(msg)

        db.session.commit()
        return conv

    def test_get_messages_success(self, client, auth_headers, conversation):
        """Test successful message retrieval."""
        response = client.get(f"/api/chat/conversations/{conversation.id}/messages", headers=auth_headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["data"]["total"] == 5
        assert len(data["data"]["messages"]) == 5

        # Verify messages are ordered by created_at
        messages = data["data"]["messages"]
        for i in range(len(messages) - 1):
            assert messages[i]["created_at"] <= messages[i + 1]["created_at"]

    def test_get_messages_with_pagination(self, client, auth_headers, conversation):
        """Test message retrieval with pagination."""
        response = client.get(
            f"/api/chat/conversations/{conversation.id}/messages?limit=2&offset=0",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert len(data["data"]["messages"]) == 2
        assert data["data"]["limit"] == 2
        assert data["data"]["total"] == 5

    def test_get_messages_conversation_not_found(self, client, auth_headers):
        """Test getting messages for non-existent conversation."""
        response = client.get("/api/chat/conversations/99999/messages", headers=auth_headers)

        assert response.status_code == 404
        data = json.loads(response.data)
        assert data["success"] is False
        assert data["error"]["code"] == "CONVERSATION_NOT_FOUND"

    def test_get_messages_forbidden(self, client, auth_headers, test_user):
        """Test accessing another user's conversation."""
        # Create conversation for different user
        other_user = User(email="other@example.com", name="Other User")
        other_user.set_password("SecurePass123")
        db.session.add(other_user)
        db.session.flush()

        conv = Conversation(user_id=other_user.id, title="Other Conversation")
        db.session.add(conv)
        db.session.commit()

        response = client.get(f"/api/chat/conversations/{conv.id}/messages", headers=auth_headers)

        assert response.status_code == 403
        data = json.loads(response.data)
        assert data["error"]["code"] == "FORBIDDEN"


class TestSendMessage:
    """Test POST /api/chat/conversations/{id}/messages"""

    @pytest.fixture
    def conversation(self, test_user):
        """Create an empty conversation."""
        conv = Conversation(
            user_id=test_user.id,
            title=None,  # Will be auto-generated
        )
        db.session.add(conv)
        db.session.commit()
        return conv

    @pytest.fixture
    def mock_ai_service(self, monkeypatch):
        """Mock AI service to avoid actual OpenAI calls."""

        class MockAgent:
            def __init__(self):
                self.conversation = type(
                    "obj",
                    (object,),
                    {
                        "add_user_message": lambda self, x: None,
                        "add_assistant_message": lambda self, x: None,
                        "messages": [],
                    },
                )()

            def get_system_prompt(self):
                return "You are an AI assistant."

            def initialize_conversation(self, system_prompt=None):
                pass

            def send_message(self, content, tools=None):
                return f"AI response to: {content}"

            def chat_with_tools(self, content, tools, execute_tool, max_rounds=5):
                return f"AI response to: {content}", []

        class MockAIService:
            def is_available(self):
                return True

            def create_agent(self):
                return MockAgent()

        from src.api import chat

        original_get_service = chat.get_ai_service

        def mock_get_service():
            return MockAIService()

        monkeypatch.setattr(chat, "get_ai_service", mock_get_service)

        yield MockAIService()

        monkeypatch.setattr(chat, "get_ai_service", original_get_service)

    def test_send_message_success(self, client, auth_headers, conversation, mock_ai_service):
        """Test successful message sending."""
        response = client.post(
            f"/api/chat/conversations/{conversation.id}/messages",
            headers=auth_headers,
            json={"content": "Hello AI!"},
        )

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["success"] is True

        # Check user message
        user_msg = data["data"]["user_message"]
        assert user_msg["role"] == "user"
        assert user_msg["content"] == "Hello AI!"

        # Check assistant message
        assistant_msg = data["data"]["assistant_message"]
        assert assistant_msg["role"] == "assistant"
        assert "AI response to: Hello AI!" in assistant_msg["content"]

        # Verify conversation title was auto-generated
        db.session.refresh(conversation)
        assert conversation.title == "Hello AI!"

    def test_send_message_auto_title_truncation(self, client, auth_headers, conversation, mock_ai_service):
        """Test auto-generated title is truncated for long messages."""
        long_message = " ".join(["word"] * 20)  # More than 8 words

        response = client.post(
            f"/api/chat/conversations/{conversation.id}/messages",
            headers=auth_headers,
            json={"content": long_message},
        )

        assert response.status_code == 201
        db.session.refresh(conversation)
        assert conversation.title.endswith("...")
        # Title is "word word word word word word word word..."
        # That's 8 words followed by "..."
        assert len(conversation.title.split()) == 8

    def test_send_message_missing_content(self, client, auth_headers, conversation):
        """Test sending message without content in body."""
        response = client.post(
            f"/api/chat/conversations/{conversation.id}/messages",
            headers=auth_headers,
            json={"content": ""},
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["error"]["code"] == "MISSING_CONTENT"

    def test_send_message_empty_content(self, client, auth_headers, conversation):
        """Test sending message with empty content."""
        response = client.post(
            f"/api/chat/conversations/{conversation.id}/messages",
            headers=auth_headers,
            json={"content": "   "},
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["error"]["code"] == "MISSING_CONTENT"

    def test_send_message_content_too_long(self, client, auth_headers, conversation):
        """Test sending message exceeding max length."""
        long_content = "A" * (Message.MAX_CONTENT_LENGTH + 1)

        response = client.post(
            f"/api/chat/conversations/{conversation.id}/messages",
            headers=auth_headers,
            json={"content": long_content},
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["error"]["code"] == "CONTENT_TOO_LONG"

    def test_send_message_conversation_not_found(self, client, auth_headers, mock_ai_service):
        """Test sending message to non-existent conversation."""
        response = client.post(
            "/api/chat/conversations/99999/messages",
            headers=auth_headers,
            json={"content": "Hello"},
        )

        assert response.status_code == 404
        data = json.loads(response.data)
        assert data["error"]["code"] == "CONVERSATION_NOT_FOUND"

    def test_send_message_forbidden(self, client, auth_headers, test_user, mock_ai_service):
        """Test sending message to another user's conversation."""
        # Create conversation for different user
        other_user = User(email="other2@example.com", name="Other User 2")
        other_user.set_password("SecurePass123")
        db.session.add(other_user)
        db.session.flush()

        conv = Conversation(user_id=other_user.id, title="Other Conversation")
        db.session.add(conv)
        db.session.commit()

        response = client.post(
            f"/api/chat/conversations/{conv.id}/messages",
            headers=auth_headers,
            json={"content": "Hello"},
        )

        assert response.status_code == 403
        data = json.loads(response.data)
        assert data["error"]["code"] == "FORBIDDEN"

    def test_send_message_ai_unavailable(self, client, auth_headers, conversation, monkeypatch):
        """Test sending message when AI service is unavailable."""
        from src.api import chat

        def mock_get_service():
            return None

        monkeypatch.setattr(chat, "get_ai_service", mock_get_service)

        response = client.post(
            f"/api/chat/conversations/{conversation.id}/messages",
            headers=auth_headers,
            json={"content": "Hello"},
        )

        assert response.status_code == 503
        data = json.loads(response.data)
        assert data["error"]["code"] == "AI_UNAVAILABLE"

    def test_send_message_preserves_context(self, client, auth_headers, conversation, mock_ai_service):
        """Test that conversation context is maintained across messages."""
        # Send first message
        response1 = client.post(
            f"/api/chat/conversations/{conversation.id}/messages",
            headers=auth_headers,
            json={"content": "First message"},
        )
        assert response1.status_code == 201

        # Send second message
        response2 = client.post(
            f"/api/chat/conversations/{conversation.id}/messages",
            headers=auth_headers,
            json={"content": "Second message"},
        )
        assert response2.status_code == 201

        # Verify both messages are in conversation
        messages = Message.query.filter_by(conversation_id=conversation.id).all()
        assert len(messages) == 4  # 2 user + 2 assistant messages

        # Verify order
        assert messages[0].role == "user"
        assert messages[0].content == "First message"
        assert messages[1].role == "assistant"
        assert messages[2].role == "user"
        assert messages[2].content == "Second message"
        assert messages[3].role == "assistant"
