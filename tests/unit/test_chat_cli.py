"""
Unit Tests: Terminal Chat Client
================================
Tests for scripts/chat_cli.py against a mocked API (no server needed).
"""

import requests
import responses

from scripts import chat_cli

API = "http://localhost:5000"


def mock_login_and_conversation():
    responses.add(
        responses.POST, f"{API}/api/auth/login", json={"success": True, "data": {"access_token": "token-123"}}
    )
    responses.add(
        responses.POST,
        f"{API}/api/chat/conversations",
        json={"success": True, "data": {"conversation": {"id": 7}}},
        status=201,
    )


def type_lines(monkeypatch, *lines):
    """Feed lines to input() as if the user typed them."""
    typed = iter(lines)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(typed))


@responses.activate
def test_prints_tool_calls_then_the_answer(monkeypatch, capsys):
    mock_login_and_conversation()
    responses.add(
        responses.POST,
        f"{API}/api/chat/conversations/7/messages",
        json={
            "success": True,
            "data": {
                "assistant_message": {"content": "Two jobs match."},
                "tool_calls": [
                    {"name": "search_jobs", "arguments": {"keywords": "python", "location": "remote"}},
                    {"name": "get_job_details", "arguments": {"job_id": 3}},
                ],
            },
        },
        status=201,
    )
    type_lines(monkeypatch, "Find python jobs", "exit")

    exit_code = chat_cli.main(["--email", "a@example.com", "--password", "secret"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "-> search_jobs(keywords='python', location='remote')" in output
    assert "-> get_job_details(job_id=3)" in output
    assert "agent> Two jobs match." in output
    assert responses.calls[2].request.headers["Authorization"] == "Bearer token-123"


@responses.activate
def test_failed_login_exits_with_the_api_error(capsys):
    responses.add(
        responses.POST,
        f"{API}/api/auth/login",
        json={"success": False, "error": {"message": "Invalid email or password"}},
        status=401,
    )

    assert chat_cli.main(["--email", "a@example.com", "--password", "wrong"]) == 1
    assert "Invalid email or password" in capsys.readouterr().err


@responses.activate
def test_unreachable_api_gives_a_hint(capsys):
    responses.add(responses.POST, f"{API}/api/auth/login", body=requests.ConnectionError())

    assert chat_cli.main(["--email", "a@example.com", "--password", "secret"]) == 1
    assert "Is it running?" in capsys.readouterr().err


@responses.activate
def test_api_errors_do_not_end_the_session(monkeypatch, capsys):
    mock_login_and_conversation()
    responses.add(
        responses.POST,
        f"{API}/api/chat/conversations/7/messages",
        json={"success": False, "error": {"message": "AI service is currently unavailable"}},
        status=503,
    )
    type_lines(monkeypatch, "Hello", "quit")

    assert chat_cli.main(["--email", "a@example.com", "--password", "secret"]) == 0
    assert "AI service is currently unavailable" in capsys.readouterr().err
