"""
Terminal Chat Client
====================
Chat with the job search agent from a terminal and see every tool it calls.

Start the API first (see README), then:
    python scripts/chat_cli.py --email testuser1@example.com

Example session:
    you> Find me remote Python jobs
      -> search_jobs(keywords='python', location='remote')
    agent> I found 3 remote Python jobs: ...
"""

import argparse
import getpass
import sys

import requests


def format_tool_call(call):
    """Render one tool call as name(arg=value, ...)."""
    arguments = call.get("arguments") or {}
    args_text = ", ".join(f"{key}={value!r}" for key, value in arguments.items())
    return f"{call['name']}({args_text})"


def error_message(response):
    """Pull the API's error message out of a failed response."""
    try:
        return response.json()["error"]["message"]
    except (ValueError, KeyError, TypeError):
        return f"HTTP {response.status_code}"


def start_conversation(session, url, email, password):
    """Log in and create a conversation. Returns its messages URL, or None on failure."""
    try:
        login = session.post(f"{url}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    except requests.ConnectionError:
        print(f"Cannot reach the API at {url}. Is it running? (docker compose up -d)", file=sys.stderr)
        return None
    if login.status_code != 200:
        print(f"Login failed: {error_message(login)}", file=sys.stderr)
        return None
    session.headers["Authorization"] = f"Bearer {login.json()['data']['access_token']}"

    created = session.post(f"{url}/api/chat/conversations", json={}, timeout=30)
    if created.status_code != 201:
        print(f"Could not start a conversation: {error_message(created)}", file=sys.stderr)
        return None
    conversation_id = created.json()["data"]["conversation"]["id"]
    return f"{url}/api/chat/conversations/{conversation_id}/messages"


def chat_loop(session, messages_url):
    """Read messages from the terminal until the user quits."""
    print("Connected. Type a message, or 'exit' to quit.\n")
    while True:
        try:
            text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if text.lower() in ("exit", "quit"):
            return
        if not text:
            continue

        # The agent may run several tools before it answers, so allow a long wait
        response = session.post(messages_url, json={"content": text}, timeout=120)
        if response.status_code != 201:
            print(f"Error: {error_message(response)}\n", file=sys.stderr)
            continue

        data = response.json()["data"]
        for call in data.get("tool_calls", []):
            print(f"  -> {format_tool_call(call)}")
        print(f"agent> {data['assistant_message']['content']}\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Chat with the job search agent and see its tool calls.")
    parser.add_argument("--url", default="http://localhost:5000", help="API base URL")
    parser.add_argument("--email", default="testuser1@example.com")
    parser.add_argument("--password", help="asked for if omitted")
    args = parser.parse_args(argv)
    password = args.password or getpass.getpass("Password: ")

    session = requests.Session()
    messages_url = start_conversation(session, args.url, args.email, password)
    if messages_url is None:
        return 1
    chat_loop(session, messages_url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
