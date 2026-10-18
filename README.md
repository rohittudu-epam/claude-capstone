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

- **Docker & Docker Compose** (recommended for quickest setup)
- OR manually: Node.js 18+, Python 3.12+, PostgreSQL 14+

### Docker Setup (Recommended)

1. **Clone the repository:**
```bash
git clone <repository-url>
cd claude-capstone
```

2. **Copy environment file:**
```bash
cp .env.example .env
# Edit .env if needed (defaults work for local development)
```

3. **Start the stack:**
```bash
docker compose up --build
```

This will:
- Start PostgreSQL and Redis
- Run database migrations
- **Automatically seed demo data** (18 sample notes, links, suggestions)
- Start all backend microservices
- Start the frontend

4. **Access the app:**

Open **http://localhost:3000** in your browser.

**Demo Login (seeded automatically):**
- Email: `demo@linknote.local`
- Password: `demo123456`

The demo account includes:
- **18 realistic notes** across AI, software testing, and productivity topics
- **Interconnected knowledge graph** with accepted links
- **Pending suggestions** to approve or reject
- **Tagged organization** for filtering and discovery

5. **Verify everything works:**
```bash
npm run smoke
```

This runs automated checks:
- ✅ Frontend serves on port 3000
- ✅ All backend services are healthy
- ✅ Demo login succeeds
- ✅ Seed data is present (notes, links, suggestions)

### Reset and Re-Seed

To start fresh:

```bash
# Stop and remove volumes
docker compose down -v

# Restart (re-seeds automatically)
docker compose up --build
```

Or use the convenience command:

```bash
npm run seed:reset
```

### Disable Auto-Seeding

Set `SEED_ON_START=false` in `.env` to disable automatic seeding on startup.

### Manual Development Setup (without Docker)

If you prefer local development without Docker:

1. **Install dependencies:**
```bash
# Frontend
cd frontend && npm install && cd ..

# Backend (in virtual environment)
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd ..
```

2. **Start PostgreSQL and Redis** (via Docker or locally)

3. **Run migrations:**
```bash
cd backend
alembic upgrade head
cd ..
```

4. **Seed demo data:**
```bash
npm run seed
# Or with custom credentials:
python scripts/seed-data.py --email user@example.com --password mypass
```

5. **Start services:**
```bash
# Terminal 1: Backend services
cd backend
uvicorn auth_service.main:app --reload --port 8001 &
uvicorn note_service.main:app --reload --port 8002 &
uvicorn link_service.main:app --reload --port 8003 &
uvicorn graph_service.main:app --reload --port 8004 &

# Terminal 2: Frontend
cd frontend
npm run dev
```

6. **Access:** http://localhost:3000

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
│   └── shared/        # Shared models and seed utilities
├── scripts/           # Utility scripts
│   ├── seed-data.py   # Populate with sample data
│   └── smoke-test.sh  # Automated smoke tests
└── docs/              # Documentation
```

## Configuration

### Environment Variables

Key variables in `.env`:

```bash
# Frontend
FRONTEND_PORT=3000                         # Port for frontend (default: 3000)
NEXT_PUBLIC_API_BASE_URL=http://localhost  # API base URL for browser

# Seed Data
SEED_ON_START=true                          # Auto-seed on docker compose up
SEED_DEMO_EMAIL=demo@linknote.local         # Demo account email
SEED_DEMO_PASSWORD=demo123456               # Demo account password (dev only!)

# Database
POSTGRES_USER=linknote
POSTGRES_PASSWORD=linknote_password
POSTGRES_DB=linknote

# Authentication
JWT_SECRET_KEY=your-secret-here             # Generate: openssl rand -hex 32
COOKIE_SECURE=false                         # Set true for HTTPS in production

# Link Suggestions
LINK_SUGGESTION_THRESHOLD=0.30              # Similarity threshold (0-1)
LINK_SUGGESTION_MIN_SHARED_KEYWORDS=2       # Minimum shared keywords
LINK_SUGGESTION_MAX_PER_NOTE=10             # Max suggestions per note
```

### Changing the Frontend Port

Edit `.env`:
```bash
FRONTEND_PORT=4000
```

Then restart:
```bash
docker compose up -d frontend
```

Access at **http://localhost:4000**

## Development Scripts

### Seed Data
```bash
# Seed with default demo account
npm run seed

# Seed with custom credentials
npm run seed:custom -- --email user@example.com --password mypass

# Reset database and re-seed
npm run seed:reset

# Smoke test (verify seed worked)
npm run smoke
```

The seed script is **idempotent** — safe to run multiple times without creating duplicates.

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

### Full Stack
```bash
# Run smoke test to verify the entire stack
npm run smoke

# Build production images
docker compose build

# View logs
docker compose logs -f [service-name]

# Stop everything
docker compose down

# Stop and remove all data
docker compose down -v
```

## Seed Data Details

The automatic seed creates:

### Demo Account
- **Email:** `demo@linknote.local` (configurable via `SEED_DEMO_EMAIL`)
- **Password:** `demo123456` (configurable via `SEED_DEMO_PASSWORD`)
- ⚠️ **Never use default credentials in production!**

### Sample Notes (18 total)

**Cluster 1: AI & Machine Learning (5 notes)**
- Understanding Artificial Intelligence
- Machine Learning in Automation
- Neural Networks Basics
- Prompt Engineering Tips
- AI Ethics and Bias

Tags: `ai`, `machine-learning`, `automation`, `deep-learning`, `llm`, `ethics`

**Cluster 2: Software Testing (5 notes)**
- AI-Powered Software Testing
- Selenium vs Playwright
- Writing Reliable Test Cases
- API Testing with REST Assured
- Test Pyramid Strategy

Tags: `software-testing`, `automation`, `qa`, `api`, `selenium`, `playwright`

**Cluster 3: Productivity & Learning (3 notes)**
- Spaced Repetition for Learning
- Weekly Review Template
- Zettelkasten Method

Tags: `productivity`, `learning`, `note-taking`, `knowledge-management`

**Bridge Notes (connect clusters):**
- Automated Testing ROI (Testing + ML)
- Learning New Programming Languages (Learning + Programming)

**Isolated Notes (for testing):**
- Hello World
- Another Text

### Pre-populated Features

- **13+ accepted links** between related notes (visible in Graph)
- **1 rejected suggestion** (for testing reject flow)
- **Timestamps** spread over last 30 days (realistic sorting)
- **Rich Markdown** formatting (code blocks, lists, headings, blockquotes)
- **Cross-cluster connections** (shows knowledge graph strength)

### Verification

After seeding, the Graph page should show:
- Multiple connected clusters
- Cross-cluster bridge connections
- Two isolated nodes (Hello World, Another Text)
- Accepted link edges

The Suggestions page should show:
- Pending suggestions based on keyword overlap
- Scores and shared keywords

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 3000 already in use | Change `FRONTEND_PORT` in `.env` or stop the other process |
| "Connection refused" from frontend | Wait for backend services to be healthy (check `docker compose ps`) |
| Seed service fails | Check `docker compose logs seed` for details; ensure migrations ran |
| No suggestions appearing | Suggestions are generated by background worker; check `docker compose logs link-worker` |
| Tests not running | Ensure test framework installed: `cd backend && pip install -r requirements-dev.txt` |
| Login fails | Verify `COOKIE_SECURE=false` in `.env` for local HTTP development |
| Graph shows no connections | Links require two notes with shared tags/keywords; check seed logs |

### Health Check URLs

- Frontend: http://localhost:3000
- Auth Service: http://localhost:8001/health
- Note Service: http://localhost:8002/health
- Link Service: http://localhost:8003/health
- Graph Service: http://localhost:8004/health
- Traefik Dashboard: http://localhost:8080 (when `with-proxy` profile active)

### Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f auth-service
docker compose logs -f frontend
docker compose logs -f seed

# Last 100 lines
docker compose logs --tail=100 link-worker
```

## Documentation

See `docs/` for detailed documentation on architecture, API design, and development guidelines.
