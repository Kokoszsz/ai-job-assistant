# AI-Powered Job Search Assistant

A web application that uses AI agents to help users find job offers, generate CVs, and prepare for interviews.

## Project Structure

```
├── backend/              # Flask backend API
│   ├── src/             # Source code
│   ├── tests/           # Test files
│   ├── scripts/         # Utility scripts (seeding, admin)
│   └── Dockerfile
├── frontend/            # React/Next.js frontend application
│   └── Dockerfile
├── mcp/                 # AI agents (MCP service)
│   └── Dockerfile
├── docker/              # Docker configuration files
│   ├── db/             # Database init scripts
│   └── nginx/          # Nginx reverse proxy config
├── .github/workflows/   # CI/CD pipelines
├── docker-compose.yml   # Development environment
├── docker-compose.prod.yml  # Production environment
├── DEPLOYMENT.md        # Deployment guide
└── README.md
```

## Prerequisites

- **Docker Desktop** (Windows/Mac) or Docker Engine + Docker Compose (Linux)
- **Git** for version control
- **API Keys**:
  - OpenAI API key ([Get one here](https://platform.openai.com/api-keys))
  - Adzuna API key ([Get one here](https://developer.adzuna.com/))

## Quick Start (5 minutes)

### 1. Clone and configure environment

```powershell
# Clone repository
git clone <repository-url>
cd SE-project

# Copy environment templates
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
cp mcp/.env.example mcp/.env

# Edit .env files with your API keys
notepad .env
```

### 2. Start all services with Docker

```powershell
# Build and start all containers
docker-compose up --build

# Services will be available at:
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:5000
# - MCP Service: http://localhost:8000
# - PostgreSQL: localhost:5432
# - Redis: localhost:6379
```

### 3. Initialize database

```powershell
# Run migrations (in new terminal)
docker-compose exec backend flask db upgrade

# (Optional) Seed sample data
docker-compose exec backend python scripts/seed_data.py --jobs 100 --users 10
```

**Done!** Open http://localhost:3000 to see the application.

### Manual Setup (Without Docker)

#### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt -r requirements-dev.txt
flask run
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

#### MCP Agents

```bash
cd mcp
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
uvicorn src.server:app --reload --port 8000
```

## Environment Variables

See the `.env.example` files in each directory for all available options:

| File | Description |
|------|-------------|
| `.env.example` | Root configuration (shared settings) |
| `backend/.env.example` | Backend-specific settings |
| `frontend/.env.example` | Frontend-specific settings |
| `mcp/.env.example` | MCP service settings |

### Required Environment Variables

```env
# Security (generate with: python -c "import secrets; print(secrets.token_hex(32))")
SECRET_KEY=your-secure-random-string
JWT_SECRET_KEY=another-secure-random-string

# API Keys
OPENAI_API_KEY=sk-...
ADZUNA_APP_ID=your-app-id
ADZUNA_API_KEY=your-api-key

# Database (auto-configured in Docker)
DATABASE_URL=postgresql://postgres:postgres@db:5432/jobassistant

# Development mode (use dummy data without external APIs)
USE_DUMMY_DATA=true
```

## Features

- 🤖 AI Chatbot for job search assistance
- 📄 AI-powered CV generation and optimization
- 💼 Job offers aggregation and matching
- 🎯 Interview preparation assistant
- 📱 Responsive web interface

## Deployment

This project includes automated CI/CD pipelines for staging and production environments.

📖 **[Read the complete deployment guide →](DEPLOYMENT.md)**

Quick overview:
- **Staging**: Auto-deploys from `develop` branch
- **Production**: Auto-deploys from `main` branch
- **See also**: [Quick Reference](DEPLOYMENT_QUICK_REFERENCE.md) | [Setup Summary](SETUP_SUMMARY.md)

## Contributing

1. Create a feature branch from `develop`
2. Make your changes
3. Test locally
4. Push to `develop` for staging deployment
5. Merge to `main` for production deployment

## Test Accounts (for demo)

Use these test accounts to sign in quickly during development or demos:

- Alice Johnson — email: `alice@example.com` — password: `password123`
- Bob Smith — email: `bob@example.com` — password: `password123`
- Charlie Davis — email: `charlie@example.com` — password: `password123`

Note: These users are pre-created in the development SQLite database located at `backend/jobsearch.db` (or created at runtime). Remove or change these credentials before publishing.

## Development

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

### API Documentation

Once the backend is running, visit: http://localhost:5000/api/docs

## Team

- **Frontend Team:** React development
- **Backend Team:** Flask API development
- **MCP Team:** AI agents and tools

## License

Academic project - 2025
