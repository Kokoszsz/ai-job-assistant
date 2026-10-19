# AI Job Search Assistant (backend + AI agent)

A Flask REST API with an LLM chat agent that helps with a job search. The agent
uses OpenAI tool calling to look things up in the app's own database: it can
search job offers, read a job's details, read your profile, and generate a CV
tailored to a specific offer.

> **Origin.** This started as an academic team project at university
> (2025/26). This repository contains only the parts I wrote, the backend API
> and the AI agent, imported into a fresh repo. My teammates' work (the Next.js
> frontend and a separate tool service) is not included. The cleanup after the
> import is visible in the commit history.

## What's inside

```
src/
├── ai/          # agent: prompts, conversation memory, tool definitions
│   └── tools/   # tools the model can call (search_jobs, get_job_details, ...)
├── api/         # Flask blueprints: auth, chat, jobs, cv, profile, health
├── services/    # business logic (auth, CVs, job sync from Remotive, ...)
├── models/      # SQLAlchemy models
└── middleware/  # JWT auth, rate limiting, logging, error handling
migrations/      # Alembic database migrations
scripts/         # seed data and admin helpers
tests/           # unit/ and integration/ (pytest)
```

**How a chat message flows:** `POST /api/chat/conversations/<id>/messages` →
the agent sends the conversation plus the tool definitions to OpenAI → if the
model asks for a tool, the backend runs it against the database (for example
`search_jobs(keywords="python", location="remote")`) → the result goes back to
the model → the final answer is saved and returned.

**Tools the agent can call:** `search_jobs`, `get_job_details`,
`get_user_profile`, `generate_cv`, `list_user_cvs`.

**Stack:** Python 3.11, Flask, SQLAlchemy + Alembic, PostgreSQL, Redis,
OpenAI API, JWT auth, pytest, Docker Compose, GitHub Actions.

## Run it

You need Docker and an OpenAI API key.

```bash
cp .env.example .env          # then set OPENAI_API_KEY in .env
docker compose up -d          # starts the API, PostgreSQL and Redis
docker compose exec backend flask db upgrade                         # create tables
docker compose exec backend python scripts/seed_data.py --all       # demo users and jobs
docker compose exec backend flask sync-jobs --category=software-dev # optional: real offers from Remotive
```

The API is now on http://localhost:5000. Check it with
`curl http://localhost:5000/api/health`.

The seed script creates users `testuser1@example.com` ... `testuser10@example.com`
with the password `TestPassword123!` (demo data only).

## Try the agent with curl

```bash
# 1. Log in and keep the access token
TOKEN=$(curl -s -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "testuser1@example.com", "password": "TestPassword123!"}' \
  | python -c "import sys, json; print(json.load(sys.stdin)['data']['access_token'])")

# 2. Start a conversation
curl -s -X POST http://localhost:5000/api/chat/conversations \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{}'
# -> {"success": true, "data": {"conversation": {"id": 1, ...}}}

# 3. Ask something that needs a tool call
curl -s -X POST http://localhost:5000/api/chat/conversations/1/messages \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"content": "Find me remote Python jobs and tell me which one fits my profile best"}'
```

The same token works for the other endpoints:

| Area    | Endpoints |
|---------|-----------|
| Auth    | `POST /api/auth/register`, `/login`, `/refresh`, `/logout`, `/password-reset/request`, `/password-reset/confirm` |
| Chat    | `GET/POST /api/chat/conversations`, `DELETE /api/chat/conversations/<id>`, `GET/POST /api/chat/conversations/<id>/messages`, `POST .../messages/stream` |
| Jobs    | `GET /api/jobs/search?q=python&location=remote`, `GET /api/jobs/<id>`, favorites under `/api/jobs/favorites` and `/api/jobs/<id>/favorite` |
| CVs     | `GET/POST /api/cv`, `GET/PUT/DELETE /api/cv/<id>`, `POST /api/cv/generate/generic`, `POST /api/cv/generate/job/<job_id>`, `GET /api/cv/<id>/pdf` |
| Profile | CRUD under `/api/profile` (experience, education, skills, ...) |

## Tests

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/pytest tests/unit          # no services needed
.venv/bin/pytest tests/integration   # password-reset tests need Redis on localhost:6379
```

CI (GitHub Actions) runs lint (flake8, black, isort), type checks (mypy),
the full test suite against PostgreSQL and Redis, and a Docker image build.

## Known limitations

These are the next things I'd fix:

- The agent loop runs one round with only the first tool call. A question
  that needs two tools (search, then read details) gets a partial answer.
- Tool results go back to the model as a user message instead of a proper
  `tool` message linked to its `tool_call_id`.
- There is no automated evaluation of the agent's answers yet; the tests
  check the API, not answer quality.
