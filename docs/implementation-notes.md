# Implementation Notes

Records what Phases 1-3 actually built, where it departs from `impl-plan.md` / `architecture.md` and why, how to run the tests, and what is not yet verified.

## Backend layout

```
backend/
  Dockerfile              one image definition; build with --build-arg SERVICE=<dir>, context backend/
  alembic.ini, migrations/  001 initial schema, 002 search/outbox/note_tags changes
  shared/                 config, db, models, security (bcrypt/JWT), auth dependency, events, outbox, health
  auth-service/auth_service/   register, login, refresh, logout, verify
  note-service/note_service/   notes CRUD, tags, search, outbox publisher (python -m note_service.publisher)
  link-service/link_service/   Redis Streams consumer + worker (python -m link_service.worker), similarity, suggestion/link API
  graph-service/graph_service/ graph API
```

## API (Phases 2-3)

| Method and path | Notes |
|---|---|
| `POST /api/auth/register` | 201; 409 duplicate email (case-insensitive); 400 invalid input |
| `POST /api/auth/login` | Sets HttpOnly `access_token` (path `/`) and `refresh_token` (path `/api/auth`) cookies; generic 401 on any failure |
| `POST /api/auth/refresh` | Rotates: the presented refresh token is revoked, a new pair is issued; reuse gives 401 |
| `POST /api/auth/logout` | 204, idempotent; revokes access and refresh tokens |
| `GET /api/auth/verify?token=` | 200 with `user_id`, 401 if invalid, expired, or revoked; also accepts `Authorization: Bearer` |
| `POST /api/notes`, `GET /api/notes`, `GET/PUT/DELETE /api/notes/{id}` | Owner-scoped; another user's note is 404 |
| `GET /api/notes?tags=a,b&limit=&offset=` | Tag filter is AND; list items omit the body |
| `GET /api/notes/search?q=&tags=&limit=&offset=` | `q` required (empty is 400); ranked, title matches above body-only; no body in results |
| `GET /api/tags` | Tags with note counts |
| `GET /api/suggestions?note_id=&limit=&offset=` | Pending suggestions for the caller, best score first, with both note titles, score and explanation. Stale suggestions are hidden. |
| `POST /api/suggestions/{id}/accept` | Creates one canonical link (201; 200 if it already existed) and removes the suggestion |
| `POST /api/suggestions/{id}/reject` | 204; the pair stays suppressed until either note changes |
| `GET /api/links?note_id=` | Accepted links, optionally those touching one note from either side |
| `GET /api/graph?tags=a,b` | `nodes`, `edges` (`source`/`target`), `total_nodes`, `max_nodes`, `is_capped`, `message`; tag filter is AND |
| `GET /health`, `GET /ready` | Liveness; readiness checks database (and Redis for note/link services), 503 if any is down |

Access tokens last 15 minutes, refresh tokens 7 days. Validation errors return 400 `{"detail": "Invalid request", "errors": [{field, message}]}` and never echo the offending input.

Event contract (`note_events` stream, schema version 1): `event_id`, `schema_version`, `event_type` (created | updated | deleted), `note_id`, `owner_id`, `occurred_at`. No note content. For created/updated, `occurred_at` equals the note's `updated_at`.

## Link suggestions: how they work

- **Trigger.** The worker reacts to `created`/`updated` events. It ignores the event payload and rebuilds that note's suggestions from the current database state in one transaction, so duplicates, retries and reordering all converge on the same result, and a failure leaves nothing half-written.
- **Score.** Weighted Jaccard over keywords: lowercase letter/digit runs of 3+ characters, minus English stopwords and numbers, no stemming. A keyword weighs 3 if it is in the note's title, otherwise 1. A pair qualifies at score >= `LINK_SUGGESTION_THRESHOLD` (default 0.30) with at least `LINK_SUGGESTION_MIN_SHARED_KEYWORDS` (default 2) shared keywords; the best `LINK_SUGGESTION_MAX_PER_NOTE` (default 10) are kept. Full detail is in `similarity.py`.
- **Candidates.** Postgres full-text search narrows the same owner's notes to those sharing one of the source note's 15 strongest keywords (at most 200, best `ts_rank` first); the Python score decides. This bounds the work per event at the cost of recall for very large accounts.
- **Exclusions.** The note itself, other owners' notes, deleted notes (foreign keys remove their rows), pairs that are already linked, and pairs rejected at the current note versions.
- **Staleness.** Each suggestion stores the `updated_at` of both notes it was computed from. It is visible and actionable only while both still match. After an edit, the next event for that note refreshes it, or drops it if the notes no longer qualify.
- **Rejection.** A rejection is a stored row, suppressing the pair only while both note versions still match. Editing either note lifts it, which is exactly the "until either endpoint changes" rule, and replaying an old event cannot undo a rejection.
- **Action errors.** 404: unknown, someone else's, or already accepted/rejected. 409: stale. Accepting twice therefore never makes a second link.

## Deviations from the plan and architecture

| Area | Plan / architecture | Built | Why |
|---|---|---|---|
| Token validation in note/link/graph | Call auth-service or verify the JWT | Verify the JWT locally and check the shared `revoked_tokens` table | Architecture allows either; avoids a network hop per request and a hard runtime dependency on auth-service. `/verify` still exists. |
| Token delivery (IMPL-6) | Cookies and response headers | HttpOnly cookies only | FR-12 says tokens must never be exposed to JavaScript; response headers and bodies are readable by it. Non-browser clients read `Set-Cookie` or send `Authorization: Bearer`. |
| Validation status (IMPL-5, 8) | 400 for invalid input | 400 (FastAPI default 422 overridden) | Matches the plan's acceptance criteria. |
| Note body limit (IMPL-8) | 10 MB | 512 KiB (`NOTE_MAX_BODY_BYTES`) | The generated full-text vector is a PostgreSQL `tsvector`, which is capped at about 1 MB; a 10 MB body could be accepted and then fail on insert. |
| Events (IMPL-11) | created, updated | created, updated, deleted | US-04 requires deletion events. Tag-only edits emit none, since link analysis does not read tags. |
| Schema changes (migration 002) | n/a | Title-weighted generated `search_vector` with GIN index; `outbox.note_id` no longer a foreign key; `note_tags` keyed by `(note_id, tag_id)`; redundant indexes and constraints from 001 removed; missing `suggestions.target_note_id` index added | A FK would cascade-delete a "deleted" event together with its note. The old body-only index could not rank titles above bodies. The rest fixes drift found by the model-vs-migration test. |
| Rate limiting | Traefik | Traefik middleware on `/api/auth` (30 requests/min/IP, burst 10) | As planned; configuration only, not testable offline. |
| Traefik routes | `/api/note`, `/api/link` | `/api/notes` + `/api/tags`, `/api/suggestions` | Match the real endpoint paths. |
| Traefik version | v2.10 | v3.6 | v2.10's bundled Docker client is rejected by Docker Engine 29, so it discovered no containers and every route returned 404. Pinning `DOCKER_API_VERSION` did not help. The labels and flags used here are unchanged in v3. |
| Suggestion storage (IMPL-13/15) | Pending suggestions only | One row per unordered note pair with `status` (pending/rejected) and the note versions used (migration 003) | Needed to remember rejections and detect stale suggestions. Existing rows are normalised by the migration. |
| Stale suggestions (IMPL-14) | 404 | 409 for stale; 404 for already-processed | Lets the UI tell "this changed under you" from "already handled". |
| Accepted-link read endpoint | Not planned | `GET /api/links`, routed to link-service | "Visible from both notes" needed a way to read links by either endpoint. |
| Graph limits | 500 nodes | 500 nodes, configurable with `GRAPH_MAX_NODES` | Makes the cap testable. |
| Docker build | Per-service contexts | One parameterized Dockerfile, context `backend/` | Per-service contexts could not import `shared`. |
| Published ports | Every service published | Only Traefik (80/443), plus Postgres/Redis/dashboard on 127.0.0.1 | Backend services must not be reachable around the proxy. |
| Frontend in Compose | Always started | Behind the `frontend` profile until IMPL-18 | There is no frontend to build yet. |
| Python and pins | 3.11, old pins | 3.14 and the exact versions in `backend/requirements.txt` | Those are the versions the tests ran on; the old pins do not install on 3.14. |

## Running the tests

```
python -m venv .venv && .venv/Scripts/pip install -r backend/requirements-dev.txt   # bin/ on Linux and macOS
cd backend && pytest
```

Tests need a real PostgreSQL and **wipe it**. They use `TEST_DATABASE_URL` (the ambient `DATABASE_URL` is ignored on purpose). The default is `postgresql://postgres@127.0.0.1:5433/postgres?sslmode=disable`.

- **With Docker:** `docker run -d -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:15-alpine`, then set `TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres`. CI does this with a service container.
- **Without Docker:** PGlite (real PostgreSQL compiled to WASM) behind a socket server. In a gitignored `.tools/pglite/`: `npm init -y && npm i @electric-sql/pglite @electric-sql/pglite-socket`, then a `server.mjs` with
  `const db = await PGlite.create(); await new PGLiteSocketServer({ db, port: 5433, host: '127.0.0.1' }).start();`
  (imports from the two packages) and `node server.mjs`. PGlite serves one connection at a time and does not survive a client-visible SQL error, so the test engine uses `NullPool` with auto-prepare off, and constraint-violation tests run inside a server-side `DO ... EXCEPTION` block. If the server stops responding, restart it.

Most tests use `fakeredis`. `link-service/tests/test_event_durability.py` also runs against a real Redis (`TEST_REDIS_URL`, default `redis://127.0.0.1:6379`) and skips when none is reachable; CI provides one. Lint and types: `ruff check . && ruff format --check .` and the `mypy` command in `.github/workflows/ci.yml`.

## Verified on the real stack

Checked 2026-10-17 on Docker Desktop (Engine 29.8.1) with `docker compose build && docker compose up -d`:

- All seven images build; every service reports healthy; `migrate` exits cleanly.
- Through Traefik on port 80: register (201), login (200, two HttpOnly cookies), wrong password (generic 401), unauthenticated request (401), create, search, tag filter, update, delete, and logout followed by a rejected request (401).
- Real Redis: three events (created, updated, deleted) reached `note_events` and were consumed by the `link-service` group with nothing pending.
- Rate limiting: 60 rapid logins gave 20 x 401 and 40 x 429.
- Phase 3 journey (18 checks): two similar notes and one unrelated note produced exactly one suggestion; accept created one link, visible from both notes, and a repeat accept was a 404; the graph showed 3 nodes and 1 edge, and an AND tag filter dropped the edge; a new similar note produced suggestions and a rejection stayed rejected.
- Real Redis outage: with the Redis container stopped, note creation still returned 201 and no suggestion appeared; after Redis restarted, the queued event was published and the suggestion appeared.

## Not yet verified

- The two `IntegrityError` to rollback branches in auth (concurrent duplicate registration, concurrent refresh-token reuse) are not exercised: the local test database cannot survive a SQL error. The pre-checks in front of them are tested.
- Search performance: p95 about 50 ms over 10,000 notes on PGlite (target 500 ms). Re-measure on real PostgreSQL.

## Known gaps

- Suggestions are only created in response to note events. Notes that existed before the worker started, or whose events were lost to stream trimming, get none until they are next edited; there is no backfill job.
- Matching is exact-keyword with no stemming or synonyms, and candidate search is capped (15 keywords, 200 notes), so recall drops for very large accounts. Threshold tuning on representative notes is still needed (open question in `requirements.md`).
- There is no endpoint to remove an accepted link.
- Rejection rows stay until the pair changes, so they grow slowly with use.

- Expired rows in `revoked_tokens` are never purged.
- Password reset, account recovery, and account deletion are undefined (open question in `requirements.md`).
- The outbox publisher must run as a single instance to preserve ordering.
- `GET /api/auth/verify?token=` puts a credential in a URL; keep it internal and make sure request logging (IMPL-26) scrubs query strings.
- Structured JSON logging, correlation IDs, and the remaining health/readiness work are Phase 4 (IMPL-25, IMPL-26). The basic `/health` and `/ready` endpoints already exist.
