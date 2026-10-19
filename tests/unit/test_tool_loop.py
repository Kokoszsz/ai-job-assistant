"""
Unit Tests: Tool Calling Loop
=============================
Tests for BaseAgent.chat_with_tools and the tool messages it stores.
The OpenAI client is mocked, so no API calls are made.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from openai import OpenAIError

from src.ai.agents.base_agent import BaseAgent
from src.ai.memory.conversation_buffer import ConversationBuffer

TOOLS = [{"type": "function", "function": {"name": "search_jobs"}}]


def completion(content=None, tool_calls=None):
    """Build a fake chat completion like the OpenAI client returns."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    response.choices[0].message.tool_calls = tool_calls
    response.usage.total_tokens = 50
    return response


def tool_call(call_id, name, arguments):
    """Build a fake tool call (the model asking to run one tool)."""
    call = MagicMock()
    call.id = call_id
    call.function.name = name
    call.function.arguments = arguments
    return call


@pytest.fixture
def client():
    return MagicMock()


@pytest.fixture
def agent(client):
    with patch("src.ai.agents.base_agent.OpenAI", return_value=client):
        return BaseAgent(api_key="test-key", model="gpt-4o-mini", temperature=0.7, max_tokens=500, timeout=30)


def sent_messages(client, request_number):
    """Messages the agent sent to OpenAI in the given request (0-based)."""
    return client.chat.completions.create.call_args_list[request_number].kwargs["messages"]


class TestChatWithTools:
    def test_answers_directly_when_no_tool_is_needed(self, agent, client):
        client.chat.completions.create.return_value = completion(content="Hello!")
        execute_tool = MagicMock()

        answer, calls = agent.chat_with_tools("Hi", tools=TOOLS, execute_tool=execute_tool)

        assert answer == "Hello!"
        assert calls == []
        execute_tool.assert_not_called()

    def test_runs_every_tool_call_in_a_round(self, agent, client):
        client.chat.completions.create.side_effect = [
            completion(
                tool_calls=[
                    tool_call("call_1", "search_jobs", '{"keywords": "python"}'),
                    tool_call("call_2", "get_user_profile", "{}"),
                ]
            ),
            completion(content="Two jobs fit your profile."),
        ]
        execute_tool = MagicMock(return_value='{"success": true}')

        answer, calls = agent.chat_with_tools("Find jobs for me", tools=TOOLS, execute_tool=execute_tool)

        assert answer == "Two jobs fit your profile."
        assert calls == [
            {"name": "search_jobs", "arguments": {"keywords": "python"}},
            {"name": "get_user_profile", "arguments": {}},
        ]
        assert execute_tool.call_count == 2

    def test_results_are_linked_to_their_tool_calls(self, agent, client):
        client.chat.completions.create.side_effect = [
            completion(
                tool_calls=[
                    tool_call("call_1", "search_jobs", '{"keywords": "python"}'),
                    tool_call("call_2", "get_user_profile", "{}"),
                ]
            ),
            completion(content="Done."),
        ]
        execute_tool = MagicMock(side_effect=['{"jobs": []}', '{"name": "Ana"}'])

        agent.chat_with_tools("Find jobs for me", tools=TOOLS, execute_tool=execute_tool)

        # Second request: the assistant's tool calls, then one tool message per call
        assistant, first, second = sent_messages(client, 1)[-3:]
        assert assistant["role"] == "assistant"
        assert assistant["content"] is None
        assert [c["id"] for c in assistant["tool_calls"]] == ["call_1", "call_2"]
        assert first == {"role": "tool", "content": '{"jobs": []}', "tool_call_id": "call_1"}
        assert second == {"role": "tool", "content": '{"name": "Ana"}', "tool_call_id": "call_2"}

    def test_chains_tool_calls_across_rounds(self, agent, client):
        client.chat.completions.create.side_effect = [
            completion(tool_calls=[tool_call("call_1", "search_jobs", '{"keywords": "python"}')]),
            completion(tool_calls=[tool_call("call_2", "get_job_details", '{"job_id": 7}')]),
            completion(content="Job 7 is the best match."),
        ]

        answer, calls = agent.chat_with_tools(
            "Which python job fits best?", tools=TOOLS, execute_tool=MagicMock(return_value="{}")
        )

        assert answer == "Job 7 is the best match."
        assert [c["name"] for c in calls] == ["search_jobs", "get_job_details"]

    def test_stops_offering_tools_after_max_rounds(self, agent, client):
        keeps_calling = completion(tool_calls=[tool_call("call_x", "search_jobs", "{}")])
        client.chat.completions.create.side_effect = [keeps_calling, keeps_calling, completion(content="Final.")]

        answer, calls = agent.chat_with_tools(
            "Find jobs", tools=TOOLS, execute_tool=MagicMock(return_value="{}"), max_rounds=2
        )

        assert answer == "Final."
        assert len(calls) == 2
        requests = client.chat.completions.create.call_args_list
        assert "tools" in requests[1].kwargs
        assert "tools" not in requests[2].kwargs

    def test_tool_errors_go_back_to_the_model(self, agent, client):
        client.chat.completions.create.side_effect = [
            completion(tool_calls=[tool_call("call_1", "search_jobs", "{}")]),
            completion(content="Sorry, the search failed."),
        ]

        answer, calls = agent.chat_with_tools(
            "Find jobs", tools=TOOLS, execute_tool=MagicMock(side_effect=ValueError("db down"))
        )

        assert answer == "Sorry, the search failed."
        tool_message = sent_messages(client, 1)[-1]
        assert json.loads(tool_message["content"])["success"] is False
        # The exception text stays in the logs, not in what the model sees
        assert "db down" not in tool_message["content"]

    def test_invalid_arguments_are_not_executed(self, agent, client):
        client.chat.completions.create.side_effect = [
            completion(tool_calls=[tool_call("call_1", "search_jobs", "{not json")]),
            completion(content="Let me try again."),
        ]
        execute_tool = MagicMock()

        _, calls = agent.chat_with_tools("Find jobs", tools=TOOLS, execute_tool=execute_tool)

        execute_tool.assert_not_called()
        assert calls == [{"name": "search_jobs", "arguments": None}]
        assert json.loads(sent_messages(client, 1)[-1]["content"])["success"] is False

    def test_recorded_arguments_ignore_changes_made_by_the_executor(self, agent, client):
        client.chat.completions.create.side_effect = [
            completion(tool_calls=[tool_call("call_1", "get_user_profile", "{}")]),
            completion(content="Done."),
        ]

        def execute_tool(name, arguments):
            arguments["user_id"] = 42  # what the chat endpoint does
            return "{}"

        _, calls = agent.chat_with_tools("Show my profile", tools=TOOLS, execute_tool=execute_tool)

        assert calls == [{"name": "get_user_profile", "arguments": {}}]

    def test_openai_error_returns_an_apology(self, agent, client):
        client.chat.completions.create.side_effect = OpenAIError("service down")

        answer, calls = agent.chat_with_tools("Hi", tools=TOOLS, execute_tool=MagicMock())

        assert "trouble connecting" in answer
        assert calls == []


class TestToolMessagesInBuffer:
    CALLS = [{"id": "call_1", "type": "function", "function": {"name": "search_jobs", "arguments": "{}"}}]

    def test_truncation_keeps_a_tool_result_with_its_request(self):
        buffer = ConversationBuffer(max_messages=3, system_message="system")
        buffer.add_user_message("find jobs")
        buffer.add_assistant_tool_calls("", self.CALLS)
        buffer.add_tool_result("call_1", "[]")

        assert [m["role"] for m in buffer.get_messages()] == ["system", "assistant", "tool"]

    def test_truncation_drops_a_tool_result_whose_request_was_cut(self):
        buffer = ConversationBuffer(max_messages=3, system_message="system")
        buffer.add_user_message("find jobs")
        buffer.add_assistant_tool_calls("", self.CALLS)
        buffer.add_tool_result("call_1", "[]")
        buffer.add_assistant_message("Here they are.")

        # Keeping the tool result without its request would make OpenAI reject the history
        assert [m["role"] for m in buffer.get_messages()] == ["system", "assistant"]
        assert buffer.get_messages()[1]["content"] == "Here they are."
