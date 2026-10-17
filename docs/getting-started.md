# Getting started with LinkNote

LinkNote is a note-taking app that suggests links between related notes and draws them as a graph. This page gets it running; the other guides go deeper:

| Guide | For |
|---|---|
| [deployment.md](deployment.md) | Production settings, backup and restore, troubleshooting |
| [testing.md](testing.md) | Running and extending the test suites |
| [database.md](database.md) | Tables, constraints, migrations |
| [api/README.md](api/README.md) | HTTP API and OpenAPI documents |
| [implementation-notes.md](implementation-notes.md) | How it works, deviations from the plan, known gaps |
| [branching-strategy.md](branching-strategy.md) | Git workflow |

(The repository's root `README.md` documents the SDLC pipeline that produced this project, not the application.)

## Run it with Docker

You need Docker with Compose v2. Nothing else.

```bash
cp .env.example .env
# Edit .env: set JWT_SECRET_KEY to a long random value (openssl rand -hex 32).
docker compose up -d --build
scripts/verify-deployment.sh        # every line should say PASS
```

Open <http://localhost>, create an account, and write a few notes. Notes that share keywords (for example two notes about "kubernetes deployment") produce a suggestion within a few seconds. Review it under **Suggestions**; accepted links appear in **Graph** and on each note.

`docker compose down` stops everything and keeps your data (the `postgres_data` and `redis_data` volumes). `docker compose down -v` deletes the data too.

On Windows, run the scripts from Git Bash or WSL.

## What runs

| Service | Role | Reachable at |
|---|---|---|
| `traefik` | Reverse proxy, the only public entry point; rate-limits login, register and refresh | <http://localhost> (80, 443) |
| `frontend` | Next.js app | `/` |
| `auth-service` | Accounts, sessions | `/api/auth` |
| `note-service` | Notes, tags, search | `/api/notes`, `/api/tags` |
| `link-service` | Suggestions and accepted links | `/api/suggestions`, `/api/links` |
| `graph-service` | Graph data | `/api/graph` |
| `outbox-publisher` | Publishes note events from the database outbox to Redis | none |
| `link-worker` | Consumes note events and computes suggestions | none |
| `migrate` | Applies database migrations, then exits | none |
| `postgres`, `redis` | Storage and event stream | `127.0.0.1:5432`, `127.0.0.1:6379` only |

The Traefik dashboard is on `127.0.0.1:8080` and is unauthenticated, so it must stay bound to localhost.

## Configuration

All settings come from `.env` (see `.env.example`, which explains each one). The ones you are most likely to change:

| Variable | Default | Meaning |
|---|---|---|
| `JWT_SECRET_KEY` | none, required | Signs sessions; at least 32 characters. Services refuse to start with the placeholder when `ENVIRONMENT=production`. |
| `COOKIE_SECURE` | `true` in Compose | Cookies are only sent over HTTPS (browsers exempt `localhost`). Set `false` only for plain-HTTP testing on another host name. |
| `LINK_SUGGESTION_THRESHOLD` | `0.30` | Similarity a pair of notes must reach to be suggested |
| `LINK_SUGGESTION_MIN_SHARED_KEYWORDS` | `2` | Shared keywords required |
| `LINK_SUGGESTION_MAX_PER_NOTE` | `10` | Suggestions kept per note |
| `GRAPH_MAX_NODES` | `500` | The graph shows at most this many notes, newest first, and says when it caps |

## Develop without Docker for the app itself

Backend (Python 3.14):

```bash
python -m venv .venv
.venv/Scripts/pip install -r backend/requirements-dev.txt     # .venv/bin/pip on Linux and macOS
cd backend && pytest
```

Frontend (Node 22 or newer):

```bash
cd frontend
npm ci
npm run dev                  # http://localhost:3000
```

The dev server proxies `/api` to the stack when you set `API_PROXY_TARGET`, for example `API_PROXY_TARGET=http://localhost npm run dev` with Compose running. Other scripts: `npm run lint`, `typecheck`, `test`, `build`, and `e2e` (see [testing.md](testing.md)).

## Using the API directly

Sessions are HttpOnly cookies. With curl, keep a cookie jar:

```bash
curl -c jar -X POST localhost/api/auth/register -H 'content-type: application/json' \
  -d '{"email":"me@example.com","password":"a long passphrase"}'
curl -c jar -b jar -X POST localhost/api/auth/login -H 'content-type: application/json' \
  -d '{"email":"me@example.com","password":"a long passphrase"}'
curl -b jar -X POST localhost/api/notes -H 'content-type: application/json' \
  -d '{"title":"First note","body":"Some **markdown**","tags":["demo"]}'
curl -b jar localhost/api/graph
```

Non-browser clients may send `Authorization: Bearer <access token>` instead. See [api/README.md](api/README.md).
