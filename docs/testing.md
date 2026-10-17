# Testing guide

Three layers, each answering a different question.

| Layer | Question | Where | Needs |
|---|---|---|---|
| Backend (pytest) | Does each service and the shared code behave, against a real PostgreSQL? | `backend/*/tests` | PostgreSQL; Redis optional |
| Frontend unit (Vitest) | Do components and the API client behave? | `frontend/src/**/*.test.*` | Node only |
| End to end (Playwright) | Does the whole stack work in a real browser? | `frontend/e2e` | The running Docker stack |

Current results are in [implementation-notes.md](implementation-notes.md) under "Verified".

## Backend

```bash
python -m venv .venv
.venv/Scripts/pip install -r backend/requirements-dev.txt        # .venv/bin/pip on Linux and macOS
cd backend
pytest                                    # everything
pytest note-service/tests/test_search.py  # one file
pytest -k suggestion                      # by name
ruff check . && ruff format --check .     # lint and formatting
mypy shared auth-service/auth_service note-service/note_service   # as in CI
```

**The tests wipe the database they connect to.** They read `TEST_DATABASE_URL` only; the ambient `DATABASE_URL` is ignored on purpose so a test can never hit a real database by accident. The default is `postgresql://postgres@127.0.0.1:5433/postgres?sslmode=disable`. Never point it at data you want to keep.

Two ways to get a database:

- **Docker:** `docker run -d -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:15-alpine`, then `TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres`. CI does this with a service container.
- **No Docker:** PGlite (PostgreSQL compiled to WASM) behind a socket server on port 5433; setup steps are in [implementation-notes.md](implementation-notes.md#running-the-tests). It serves one connection at a time and stops responding after some SQL errors; restart it if tests hang. The test engine is configured for this (`NullPool`, no prepared statements), and constraint-violation tests run inside server-side `DO ... EXCEPTION` blocks.

Redis: most tests use `fakeredis`. `link-service/tests/test_event_durability.py` also uses a real Redis (`TEST_REDIS_URL`, default `redis://127.0.0.1:6379`) and **skips** when none is reachable, so a green run without Redis has not exercised that file. CI provides Redis.

What the suites cover:

| Area | Tests |
|---|---|
| `shared/tests` | Model-versus-migration schema equality; JSON logging, secret redaction, correlation ids |
| `auth-service` | Registration, login, cookies, refresh rotation and reuse, logout and revocation, `/me`, validation, enumeration resistance |
| `note-service` | CRUD, ownership isolation, tags, search ranking, outbox events, publisher retry and ordering |
| `link-service` | Similarity scoring, idempotent processing, consumer delivery and redelivery, suggestion accept/reject/stale, durability across a Redis outage |
| `graph-service` | Nodes and edges, AND tag filter, 500-node cap, no dangling edges, isolation between users |

### Writing backend tests

- Use the fixtures in `backend/conftest.py` (`make_user`, the test client, the engine) rather than your own database setup.
- Prove a new test can fail: break the code under test, see the test go red, restore it. This repository's security and idempotency tests were checked that way.
- Compare `detail` and field names in error responses, not whole bodies; every error body carries a per-request `correlation_id`.

## Frontend unit tests

```bash
cd frontend
npm ci
npm test                 # vitest run
npm run test:watch
npm run lint && npm run typecheck && npm run build
```

Tests use Testing Library with jsdom and a small fetch mock (`src/test/utils.tsx`, `fixtures.ts`). Query by role and accessible name, as the end-to-end tests do, so the tests also guard accessibility.

## End-to-end tests

They drive Chromium against the real stack through Traefik.

```bash
docker compose up -d --build
scripts/verify-deployment.sh
cd frontend
npm ci
npx playwright install chromium     # once
npm run e2e                         # all specs
npx playwright test e2e/journey.spec.ts
E2E_BASE_URL=https://staging.example npm run e2e   # another environment (default http://localhost)
```

| Spec | Covers |
|---|---|
| `journey.spec.ts` | Redirect to sign-in, register, create notes, search and AND tag filter, wait for a suggestion, accept it, graph (canvas and accessible list), tag filter on the graph, linked notes on a note, edit, delete, sign out and in; a rejected suggestion stays dismissed |
| `security.spec.ts` | HttpOnly `SameSite=Lax` cookies not readable by scripts; script, image-handler and `javascript:` content in notes does not run; another user's note is unreachable; unauthenticated API calls get 401; open-redirect attempt stays on site; an expired access token is refreshed on reload |
| `accessibility.spec.ts` | axe-core WCAG 2.1 A/AA scans (serious and critical issues fail) of sign-in, register, notes, editor, suggestions, graph in both views; keyboard-only navigation |
| `graph-performance.spec.ts` | Creates 520 notes and checks the 500-node graph is drawn in under 2 seconds (best of three loads) |

Things to know:

- Every test registers a fresh user, so runs do not interfere with each other or need cleanup. They do leave those users and notes behind; run them against a stack whose data you can discard.
- Login, register and refresh are rate-limited to 30/minute per IP (burst 10). The suite stays under that on its own, but running it repeatedly in quick succession can produce `429` failures; wait a minute.
- Suggestions arrive asynchronously, so specs poll for up to 45 seconds rather than sleeping.
- The performance test measures a real browser on your machine. It is a regression guard, not a benchmark; the 2 second target is for typical hardware.
- E2E is not part of CI yet: CI builds the images and checks that the stack starts, but does not run Playwright.

## Before you merge

```bash
cd backend && ruff check . && ruff format --check . && pytest
cd ../frontend && npm run lint && npm run typecheck && npm test && npm run build
docker compose up -d --build && scripts/verify-deployment.sh && npm run e2e
```
