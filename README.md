# LinkNote - Markdown Notes with Smart Link Suggestions

A knowledge management tool that turns your Markdown notes into an interconnected knowledge graph.

## Features

- **Markdown Editor**: Write notes with live preview and syntax highlighting
- **Smart Link Suggestions**: AI-powered suggestions for connecting related notes
- **Interactive Graph**: Visualize connections between your notes
- **Tag-Based Organization**: Flexible tagging system with filtering
- **Full-Text Search**: Find any note instantly
- **You Control Everything**: No links are created until you approve them

## Quick Start

### Prerequisites

- Node.js 18+ and npm
- Python 3.12+
- PostgreSQL 14+ (or use the included PGlite for development)

### Development Setup

1. **Clone and install dependencies:**
```bash
git clone <repository-url>
cd claude-capstone

# Install frontend dependencies
cd frontend && npm install && cd ..

# Install backend dependencies (in a virtual environment)
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && cd ..
```

2. **Start the development servers:**
```bash
# Terminal 1: Start backend (from backend directory)
cd backend
uvicorn note_service.main:app --reload --port 8001 &
uvicorn link_service.main:app --reload --port 8002 &
uvicorn graph_service.main:app --reload --port 8003 &
uvicorn auth_service.main:app --reload --port 8004

# Terminal 2: Start frontend (from frontend directory)
cd frontend
npm run dev
```

3. **Seed sample data (optional):**
```bash
# From project root, with backend activated
python scripts/seed-data.py --email demo@example.com --password demo123456
```

The seed script creates a demo account with 15 sample notes covering topics like Python, JavaScript, databases, DevOps, and more. Perfect for testing the link suggestions and knowledge graph features!

4. **Open the app:**
Visit `http://localhost:3000` and either:
- Create a new account
- Sign in with seeded demo account: `demo@example.com` / `demo123456`

## Project Structure

```
claude-capstone/
├── frontend/          # Next.js 15 + React 19 + TypeScript
│   ├── src/
│   │   ├── app/       # Next.js app router
│   │   ├── components/ # React components
│   │   └── lib/       # Utilities and API client
│   └── package.json
├── backend/           # Python microservices
│   ├── auth-service/  # User authentication
│   ├── note-service/  # Notes CRUD
│   ├── link-service/  # Link suggestions
│   ├── graph-service/ # Knowledge graph
│   └── shared/        # Shared models and utilities
├── scripts/           # Utility scripts
│   └── seed-data.py   # Populate with sample data
└── docs/              # Documentation
```

## Development Scripts

### Seed Data
```bash
# Create demo user with sample notes
python scripts/seed-data.py --email user@example.com

# Use custom password
python scripts/seed-data.py --email user@example.com --password mypassword
```

### Frontend
```bash
cd frontend
npm run dev          # Start dev server
npm run build        # Production build
npm run lint         # Run ESLint
npm run typecheck    # Type check with TypeScript
npm test             # Run unit tests
npm run e2e          # Run E2E tests
```

### Backend
```bash
cd backend
pytest               # Run all tests
pytest -v            # Verbose output
ruff check .         # Lint Python code
mypy .               # Type check Python
```

## Documentation

See `docs/` for detailed documentation on architecture, API design, and development guidelines.
