# Architecture Document: LinkNote MVP

## Architectural Drivers

The following requirements have the greatest influence on architectural decisions:

1. **Privacy and Data Isolation (NFR-4):** Each user's data must be strictly isolated; no cross-user data exposure is acceptable.
2. **Asynchronous Link Analysis (FR-8, FR-9):** Link suggestion processing must not block user-facing operations; Redis Streams enable reliable, scalable event-driven processing.
3. **Multi-Service Composition (FR-1 to FR-15):** The system comprises independent backend services (auth, note, link, graph) plus a frontend, deployed together in Docker Compose.
4. **Performance Targets (NFR-1):** Full-text search must complete in <500ms and graph API in <1s; these shape database indexing and query design.
5. **Single-Machine Deployment (NFR-6):** Docker Compose deployment via Traefik reverse proxy simplifies initial launch while remaining stateless for horizontal scaling.
6. **Deterministic Link Suggestions (FR-9):** Keyword-based similarity with idempotent processing prevents duplicate suggestions and ensures reproducible analysis.

---

## System Overview

LinkNote MVP is a containerized, microservices-based personal knowledge management system. Users authenticate via email/password, create and organize Markdown notes with tags, and discover relationships between notes through automatically generated link suggestions. The backend comprises four independent FastAPI services (auth, note, link, graph) sharing a PostgreSQL database and communicating through both synchronous REST APIs and asynchronous Redis Streams. The frontend (Next.js 15) consumes these APIs, providing note management, search, suggestion review, and an interactive 2D knowledge graph visualization. All services run on private container networks behind a Traefik reverse proxy, with PostgreSQL and Redis persisted in Docker volumes. The system enforces strict multi-tenant isolation at every layer: database queries, API responses, and background processing scope data exclusively to the authenticated user.

---

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Client / Browser                            │
└────────────────────────────┬────────────────────────────────────────┘
                             │ HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Traefik Reverse Proxy                            │
│  (Route, TLS termination, service discovery, rate limiting)         │
└──┬──────────────────┬──────────────────┬──────────────────┬─────────┘
   │ /                │ /api/auth        │ /api/note        │ /api/*
   │                  │ /api/graph       │ /api/link        │
   ▼                  ▼                  ▼                  ▼
┌──────────┐      ┌────────────┐    ┌──────────┐      ┌────────────┐
│ Frontend │      │Auth Service│    │Note Svc  │      │Link Svc    │
│(Next.js) │      │ (FastAPI)  │    │(FastAPI) │      │ (FastAPI)  │
└────┬─────┘      └─────┬──────┘    └────┬─────┘      └─────┬──────┘
     │                   │                │                  │
     │                   │ JWT token      │                  │
     │                   │ validation     │                  │
     │                   ▼                ▼                  ▼
     │            ┌─────────────────────────────────────────────┐
     │            │       PostgreSQL (shared database)          │
     │            │  - users, notes, tags, links, suggestions  │
     └────────────┤                                             │
                  └─────────────────────────────────────────────┘
                                      ▲
                    ┌─────────────────┴──────────────────┐
                    │                                    │
                    ▼                                    ▼
            ┌──────────────┐                    ┌──────────────┐
            │ Graph Service│                    │ Note Events  │
            │  (read-only) │                    │ Consumer     │
            └──────────────┘                    │  (Link Svc)  │
                                                └──────┬───────┘
                                                       │
                                                       ▼
                                                ┌─────────────────┐
                                                │  Redis Streams  │
                                                │ (event bus)     │
                                                └─────────────────┘
                                                       ▲
                                                       │
                                                  (publishes)
                                                       │
                                                ┌──────────────┐
                                                │ Note Service │
                                                │(event source)│
                                                └──────────────┘
```

---

## Components

### Component: Traefik Reverse Proxy

- **Responsibility:** Route incoming HTTP/HTTPS requests to backend services and frontend based on URL paths; terminate TLS connections; provide service discovery; apply rate limiting and middleware policies.
- **Technology:** Traefik (v2.x or later), configured via Docker labels.
- **Interfaces:**
  - Exposes ports 80 (HTTP) and 443 (HTTPS) to external clients.
  - Routes requests to backend services and frontend via internal Docker network.
  - Integrates with Docker API for automatic service discovery.
- **Dependencies:** Docker daemon (for service discovery).
- **Configuration:** Routing rules, TLS certificate management, rate limiting policies.

### Component: Frontend (Next.js 15 Application)

- **Responsibility:** Provide user interface for authentication, note management, search, link suggestion review, and knowledge graph visualization. Enforce authentication state, render forms with validation feedback, handle loading/error states, and communicate with backend APIs.
- **Technology:** Next.js 15 (App Router), TypeScript, Tailwind CSS, shadcn/ui, react-force-graph-2d for graph visualization.
- **Interfaces:**
  - Exposes static and dynamic routes via HTTP (served through Traefik).
  - Consumes REST APIs from auth-service, note-service, link-service, and graph-service.
  - Stores access tokens in HttpOnly cookies; refresh tokens in secure storage.
- **Dependencies:** All backend services (auth, note, link, graph).
- **Key Features:**
  - Authentication flow: registration, login, logout, session refresh.
  - Note editor: create, edit, delete notes with Markdown preview.
  - Search interface: full-text search with tag filtering.
  - Suggestion review: view, accept, reject pending link suggestions.
  - Graph visualization: interactive 2D force-directed graph with tag filtering.

### Component: Auth Service (FastAPI)

- **Responsibility:** Handle user registration, login, JWT token issuance and validation, refresh token rotation, and session management. Ensure all operations enforce email uniqueness, password hashing, and token security policies.
- **Technology:** FastAPI (Python), SQLAlchemy 2.0 ORM, bcrypt for password hashing, PyJWT for token management.
- **Interfaces:**
  - REST API endpoints:
    - `POST /register` — user registration (email, password).
    - `POST /login` — login (email, password) → access token + refresh token.
    - `POST /refresh` — refresh token rotation.
    - `POST /logout` — token revocation.
    - `GET /verify` — token validation (used by other services).
  - Writes to PostgreSQL `users` table (user registration, password updates).
  - Reads from PostgreSQL `users` table (login verification).
- **Dependencies:** PostgreSQL, JWT signing key (from environment).
- **Security:** Bcrypt password hashing (12 rounds), short-lived access tokens (15 minutes), refresh token rotation, HttpOnly cookie storage enforced by frontend.
- **Error Handling:** Invalid credentials return generic "authentication failed" errors. Invalid tokens return 401 Unauthorized. Rate limiting prevents brute-force attacks.

### Component: Note Service (FastAPI)

- **Responsibility:** Provide CRUD operations for notes and tags scoped to the authenticated user. Enforce note ownership, validate Markdown content, manage note-tag associations, and publish domain events for downstream link analysis.
- **Technology:** FastAPI (Python), SQLAlchemy 2.0 ORM, Pydantic v2 for request validation.
- **Interfaces:**
  - REST API endpoints:
    - `POST /notes` — create note (title, body, tags).
    - `GET /notes` — list user's notes (with pagination).
    - `GET /notes/{id}` — retrieve single note.
    - `PUT /notes/{id}` — update note (title, body, tags).
    - `DELETE /notes/{id}` — delete note.
    - `GET /notes/search` — full-text search (query, tags filter).
  - Publishes to Redis Streams: `note.created` and `note.updated` events (note ID, owner ID, event type, timestamp).
  - Reads from PostgreSQL: `notes`, `tags`, `note_tags` tables.
  - Writes to PostgreSQL: create, update, delete note records; tag associations; timestamps.
- **Dependencies:** PostgreSQL, Redis (for event publishing), Auth Service (for token validation).
- **Data Integrity:** Notes scoped to owner; tag normalization (lowercase, trimmed); uniqueness constraints on note-tag pairs; cascading deletes for associated tags and links.
- **Error Handling:** 401 for unauthenticated requests, 403 for unauthorized access to other users' notes, 400 for invalid input, 404 for not found, 500 for server errors.

### Component: Link Service (FastAPI)

- **Responsibility:** Consume note events from Redis Streams, analyze notes to generate link suggestions using keyword-based similarity, store suggestions, and provide endpoints for users to accept/reject suggestions, creating canonical accepted links.
- **Technology:** FastAPI (Python), SQLAlchemy 2.0 ORM, Redis Streams consumer groups, keyword similarity algorithm (deterministic, configurable threshold).
- **Interfaces:**
  - REST API endpoints:
    - `GET /suggestions` — list pending suggestions for user's notes.
    - `POST /suggestions/{id}/accept` — accept a suggestion, create accepted link.
    - `POST /suggestions/{id}/reject` — reject a suggestion, remove from pending.
    - `GET /accepted-links` — list accepted links for user's notes.
  - Consumes from Redis Streams: `note.created` and `note.updated` events.
  - Reads from PostgreSQL: `notes`, `suggestions`, `accepted_links` tables.
  - Writes to PostgreSQL: create pending suggestions, update accepted links, remove rejected suggestions.
- **Dependencies:** PostgreSQL, Redis (for event consumption), Note Service (indirectly via events).
- **Core Algorithm:**
  - Triggered by note creation/update events.
  - Analyze note title and body against all eligible notes owned by the same user.
  - Compute keyword overlap score; filter candidates by configurable threshold (proposed: 30%).
  - Exclude: source note, deleted notes, already accepted links, candidates of different owners.
  - Store as pending suggestion; on duplicate or re-evaluation, update existing suggestion (no duplicates).
  - Rejection suppresses relationship until either note changes.
- **Error Handling:** Gracefully handle missing notes, invalid events, Redis unavailability (log and retry). Accept/reject operations validate ownership and return 404 for stale suggestions.

### Component: Graph Service (FastAPI)

- **Responsibility:** Provide a read-only aggregation API returning nodes (notes) and edges (accepted links) scoped to the authenticated user, with tag-based filtering.
- **Technology:** FastAPI (Python), SQLAlchemy 2.0 ORM for queries.
- **Interfaces:**
  - REST API endpoint:
    - `GET /graph` — retrieve graph (optional query params: tags filter, limit).
  - Reads from PostgreSQL: `notes`, `tags`, `note_tags`, `accepted_links` tables.
  - Response format: `{ nodes: [{id, title, created_at, updated_at, tags}], edges: [{source_id, target_id}] }`.
- **Dependencies:** PostgreSQL, Auth Service (for token validation).
- **Graph Filtering:**
  - Tags filter uses AND logic: return only notes containing ALL selected tags.
  - Edges included only if both source and target nodes are visible after filtering.
  - Cap result at 500 visible nodes; return indicator if limit reached.
- **Error Handling:** 401 for unauthenticated, 400 for invalid filters, 200 with capped results for large graphs.

### Component: PostgreSQL Database (Shared)

- **Responsibility:** Persist all domain entities (users, notes, tags, links, suggestions) with ACID guarantees, enforce referential integrity, and support efficient full-text search and graph queries.
- **Technology:** PostgreSQL 13+, with service-specific schemas (proposed: `auth`, `notes`, `links` to maintain logical isolation).
- **Schema:**
  - `auth.users`: id (UUID), email (unique), password_hash, created_at, updated_at.
  - `notes.notes`: id (UUID), owner_id (FK to users), title, body, created_at, updated_at.
  - `notes.tags`: id (UUID), owner_id (FK to users), name (normalized), created_at.
  - `notes.note_tags`: note_id (FK), tag_id (FK), owner_id (FK to users) — unique (note_id, tag_id).
  - `links.accepted_links`: id (UUID), source_note_id (FK), target_note_id (FK), owner_id (FK), created_at — unique (source, target) canonicalized.
  - `links.suggestions`: id (UUID), source_note_id (FK), target_note_id (FK), owner_id (FK), score, status (pending/accepted/rejected), created_at, updated_at.
- **Indexes:**
  - Full-text search index on `notes.body` (tsvector).
  - Indexes on (owner_id, created_at) for efficient per-user queries.
  - Indexes on foreign keys for join performance.
- **Constraints:**
  - Foreign keys enforce referential integrity.
  - Check constraints ensure non-null owners for multi-tenant isolation.
  - Unique constraints prevent duplicate tags per user, duplicate links per pair.
- **Transactions:** Multi-row updates use explicit transactions to maintain consistency (e.g., deleting a note and cascading links).
- **Dependencies:** Alembic migrations (defined in each service).

### Component: Redis Streams (Event Bus)

- **Responsibility:** Provide reliable, ordered message passing from Note Service (event source) to Link Service (event consumer) using Redis Streams consumer groups, enabling asynchronous link analysis without blocking note CRUD.
- **Technology:** Redis 5.0+ with Streams, consumer groups for at-least-once delivery semantics.
- **Streams:**
  - `note_events`: entries with payload `{ event_type: "created" | "updated", note_id, owner_id, version, timestamp }`.
- **Consumer Group:** `link-service` consumes from `note_events` with automatic offset tracking.
- **Guarantees:** At-least-once delivery; consumers must be idempotent to handle duplicates (same event delivered multiple times if processing fails).
- **Retention:** Automatic trimming to recent entries (configurable, proposed: last 1000 entries or 7 days).
- **Error Handling:** Consumer tracks processing failures; failed events remain in stream for retry. Alerts/logs trigger on persistent failures.
- **Dependencies:** Note Service (publishes), Link Service (consumes).

### Component: CI/CD Pipeline

- **Responsibility:** Automate linting, type checking, testing, and deployment verification triggered by git commits.
- **Technology:** GitHub Actions (or equivalent CI system).
- **Jobs:**
  - Linting: flake8 or ruff for Python; ESLint for TypeScript/JavaScript.
  - Type checking: mypy for Python backend; TypeScript compiler for frontend.
  - Unit and integration tests: pytest for backend; Jest/Vitest for frontend.
  - Docker build: verify all service images build successfully.
  - Docker Compose validation: ensure compose file is syntactically correct and services start.
- **Triggers:** Push to main branch, pull requests, manual trigger.
- **Dependencies:** Git repository, test dependencies (pytest, Jest, etc.), Docker.

---

## Data Flow

### Authentication Flow

1. User submits email and password via frontend login form.
2. Frontend sends `POST /api/auth/login` to Auth Service.
3. Auth Service queries PostgreSQL for user; validates password against bcrypt hash.
4. If valid: Auth Service generates JWT access token (15-min expiry) and refresh token, returns both via HttpOnly cookie and response header.
5. Frontend stores access token in HttpOnly cookie; refresh token in secure storage (e.g., sessionStorage with CSRF protection).
6. Subsequent API requests include access token in `Authorization: Bearer <token>` header.
7. Backend services validate token with Auth Service (JWT verification or `/verify` endpoint).

### Note Creation and Link Discovery

1. Authenticated user creates a note via frontend: `POST /api/notes` with title, body, tags.
2. Note Service receives request, validates ownership (via JWT), persists note to PostgreSQL.
3. Note Service publishes `note.created` event to Redis Streams with note ID, owner ID, timestamp.
4. Link Service consumer group picks up the event from Redis Streams.
5. Link Service analyzes the note: computes keyword similarity against all eligible notes owned by the same user.
6. Link Service stores pending suggestions in PostgreSQL `suggestions` table (one per candidate pair).
7. User reviews pending suggestions via frontend: `GET /api/suggestions`.
8. User accepts or rejects a suggestion: `POST /api/suggestions/{id}/accept` or `POST /api/suggestions/{id}/reject`.
9. Link Service creates accepted link in `accepted_links` table or removes suggestion from pending.
10. Graph API includes accepted link in subsequent `GET /graph` responses.

### Search and Graph Visualization

1. User searches for notes via frontend: `GET /api/notes/search?q=kubernetes&tags=devops`.
2. Note Service queries PostgreSQL using full-text search on note body and title, filtered by user and tags.
3. Note Service returns matching notes (metadata only, not full bodies).
4. User views knowledge graph: frontend requests `GET /api/graph?tags=devops`.
5. Graph Service retrieves notes and links scoped to user and tag filters from PostgreSQL.
6. Graph API applies AND semantics (note must have all tags) and caps result at 500 nodes.
7. Frontend renders force-directed graph using react-force-graph-2d.
8. User clicks a node to open the note or filters by additional tags, triggering new graph API call.

---

## Technology Choices

| Technology | Purpose | Rationale |
|-----------|---------|-----------|
| **FastAPI** | Backend API framework | Type-safe, automatic OpenAPI docs, async support for high concurrency, excellent for microservices. |
| **SQLAlchemy 2.0** | ORM for database access | Powerful ORM with support for complex queries, migrations via Alembic, multi-tenant isolation patterns. |
| **PostgreSQL 13+** | Primary database | ACID compliance, full-text search support, JSON operators, reliable for data-critical applications. Shared schema per service for logical isolation. |
| **Redis Streams** | Event bus | Ordered, durable message passing with consumer groups; better than Pub/Sub for reliable asynchronous processing. |
| **Next.js 15 (App Router)** | Frontend framework | SSR/SSG support, excellent TypeScript support, built-in API routes, modern component patterns. |
| **TypeScript** | Frontend language | Static typing reduces bugs, better IDE support, improved maintainability. |
| **Tailwind CSS** | Styling | Utility-first CSS, rapid prototyping, consistent design tokens, small final bundle. |
| **shadcn/ui** | UI component library | Customizable, copy-paste components, works well with Tailwind, accessible defaults. |
| **react-force-graph-2d** | Graph visualization | Lightweight, WebGL-accelerated 2D force-directed graph; performant for up to 500+ nodes. |
| **Docker & Docker Compose** | Containerization & orchestration | Reproducible environments, multi-service orchestration, easy local development, simple single-machine deployment. |
| **Traefik** | Reverse proxy | Service discovery, automatic routing, TLS termination, middleware support. Integrates natively with Docker. |
| **Alembic** | Database migrations | Version-controlled schema changes, rollback support, paired with SQLAlchemy. |
| **bcrypt** | Password hashing | Industry-standard, configurable work factor, resistant to timing attacks. |
| **PyJWT** | JWT token handling | Pure Python JWT implementation, signature verification, claims validation. |
| **pytest** | Python testing | Comprehensive testing framework, fixtures, parametrization, plugin ecosystem. |
| **Jest/Vitest** | Frontend testing | Component testing, snapshot testing, excellent TypeScript support. |

---

## Security Architecture

### Secrets Management
- Environment variables (`.env` file, loaded by Docker Compose; never committed).
- Traefik TLS certificates stored securely; renewal automated (Let's Encrypt or self-signed for development).
- JWT signing keys stored in environment variables, rotated periodically.
- Database credentials in environment variables, not hardcoded.

### Input Validation
- Frontend validates user input (form validation, character limits) for UX.
- **Server-side validation is authoritative:**
  - Pydantic schemas on FastAPI endpoints validate all request payloads.
  - Markdown body size limits enforced (proposed: 10MB max).
  - Tag normalization applied consistently (lowercase, trimmed).
  - Email format validated; uniqueness checked in database.
- SQL injection prevented by using parameterized queries (SQLAlchemy ORM).
- XSS prevented by rendering escaped content in frontend templates.

### Trust Boundaries
1. **Boundary 1: Internet ↔ Traefik** — TLS encryption required; no plaintext credentials over HTTP.
2. **Boundary 2: Traefik ↔ Backend Services** — Internal Docker network (no TLS needed); all services trust Traefik's routing.
3. **Boundary 3: Backend Services ↔ Database** — Internal network; database credentials from environment.
4. **Boundary 4: Frontend ↔ User** — Tokens stored in HttpOnly cookies; CSRF tokens for state-changing operations (if applicable).
5. **Authorization Boundary: Per-Request** — Every API endpoint extracts user ID from JWT token; all database queries filter by that user ID.

### Data Protection
- Passwords hashed with bcrypt; never stored or logged in plaintext.
- Tokens never logged; use request correlation IDs for debugging.
- Note content not included in event payloads; only note IDs and metadata.
- GraphQL/REST response filtering ensures no data leakage (ownership checks before returning entities).

---

## Error Handling Strategy

### Error Propagation
- **Frontend:** HTTP errors (4xx, 5xx) from backend APIs are caught, a user-friendly error message is displayed, and the user is prompted to retry or navigate elsewhere.
- **Backend:** Exceptions in service handlers are caught, logged with correlation IDs, and returned as structured JSON errors with appropriate HTTP status codes.
- **Database:** Constraint violations (e.g., duplicate email, foreign key errors) are caught, logged, and returned as 400 or 409 errors with a message.
- **Redis:** Unavailability or timeout errors are logged; event publishing failures are retried (backoff strategy) and surfaced as warnings.

### Retry Policies
- **HTTP requests (frontend → backend):** Client-side retry for 5xx errors with exponential backoff (max 3 retries).
- **Redis Streams consumption (Link Service):** Automatic retry with offset tracking; failed events remain in stream for manual recovery if needed.
- **Database transactions:** Automatic retry for transient connection failures (SQLAlchemy connection pool retry).
- **Event publishing (Note Service → Redis):** On Redis unavailability, note creation fails (user receives error); event is not lost.

### User-Facing Error Behavior
- Invalid input (400): Display specific validation error (e.g., "Email must be valid").
- Unauthorized (401): Redirect to login page; refresh token if stale.
- Forbidden (403): Display "You don't have access to this resource."
- Not found (404): Display "Note not found" or similar.
- Server error (500): Display "Something went wrong; please try again later" with correlation ID.
- Service unavailable (503): Display "Service is temporarily unavailable; please try again soon."

---

## Deployment Model

### Development
- **Setup:** Run `docker-compose up` in project root; services start on private network.
- **Access:** Frontend accessible at `http://localhost`; backend APIs at `http://localhost/api/*`.
- **Database:** PostgreSQL and Redis run in containers with local volumes for persistence.
- **Configuration:** `.env.local` (development overrides; not committed).

### Production (Single Machine)
- **Setup:** Same Docker Compose on production server; update `.env` with production values (secrets, domain, TLS config).
- **Access:** All traffic goes through Traefik on ports 80/443; TLS certificates from Let's Encrypt or self-signed.
- **Database:** PostgreSQL and Redis persisted to external volumes (NFS or block storage for availability).
- **Monitoring:** Health check endpoints (`/health`, `/ready`) enable uptime monitoring.
- **Backup:** PostgreSQL backups triggered by external tools (e.g., pg_dump via cron); backup retention policy defined separately.
- **Scaling:** To scale horizontally (future), stateless services can run multiple replicas behind load balancer; database becomes a shared resource.

### Deployment Verification
1. All services report healthy status on `/health` endpoints.
2. Database migrations complete successfully.
3. Redis Streams consumer group created and ready to process events.
4. Frontend loads without 5xx errors.
5. End-to-end test (login → create note → view graph) succeeds.

---

## Assumptions

1. **Shared PostgreSQL Database:** All services share one PostgreSQL instance with separate schemas; no separate data replication.
2. **Synchronous Auth Verification:** Other services validate tokens with Auth Service synchronously (either JWT verification or `/verify` endpoint); no token caching or async revocation.
3. **Idempotent Event Processing:** Link Service consumers are idempotent; duplicate event delivery does not result in duplicate suggestions or links.
4. **Tag Normalization:** Tags are normalized consistently across the system (lowercase, whitespace trimmed); no multilingual or non-ASCII tag support assumed for MVP.
5. **User Isolation:** Multi-tenant isolation is enforced strictly by the application; database-level row-level security (RLS) is not used.
6. **Redis Availability:** Redis Streams are available in-cluster; Redis is not replicated or highly available in MVP (single instance in container).
7. **Graph Size:** Interactive graph visualization assumes up to 500 visible nodes; larger graphs are capped with indication to user.
8. **Timeouts:** Network timeouts, database connection pooling, and client-side request timeouts are configured but not explicitly specified in this document.

---

## Risks

1. **Single Point of Failure (Redis, PostgreSQL):** Both Redis and PostgreSQL run in single containers; no redundancy. Mitigation: External persistent volumes, regular backups, documented recovery procedure.

2. **Database Performance at Scale:** Full-text search performance may degrade with millions of notes; no sharding or partitioning. Mitigation: Proper indexing, query optimization, monitoring of query plans. Future: consider read replicas or partitioning.

3. **Event Loss in Transit:** If a note is created but Redis publication fails, the event is lost and link suggestions won't be generated. Mitigation: Transactional outbox pattern could be added (store event durably before publishing), but adds complexity. MVP: Accept this risk and monitor for failures.

4. **Cross-Service Authorization:** If Auth Service is compromised, all services are compromised (no defense in depth). Mitigation: Strict auth-service code review, rate limiting on `/verify`, token rotation policies.

5. **Suggestion Quality:** Simple keyword matching may produce poor suggestions. Mitigation: Configurable threshold, user feedback loop, future: embeddings if needed.

6. **Graph Rendering Performance:** Large graphs (500+ nodes) may be slow in browser. Mitigation: Capping at 500 nodes, lazy loading, WebGL acceleration, monitoring browser performance.

7. **Concurrent Updates to Notes:** If a note is updated multiple times rapidly, link suggestions may be re-evaluated multiple times. Mitigation: Configurable re-evaluation window, deduplication in consumer.

8. **Data Retention and Compliance:** No explicit retention policies, audit logs, or GDPR-specific features (e.g., right to be forgotten). Mitigation: Define retention policies, implement account deletion cascade, document compliance scope.

---

## Requirements Traceability

| Requirement | Component | Rationale |
|-------------|-----------|-----------|
| FR-1: Reproducible Dev Environment | CI/CD, Docker Compose | Docker Compose + Traefik provide reproducible local setup. |
| FR-2: Database Persistence | PostgreSQL, Alembic | PostgreSQL with migrations ensures consistent persistence. |
| FR-3: User Registration & Auth | Auth Service | Dedicated service handles registration, login, JWT tokens. |
| FR-4: Session Authorization | Auth Service + all backend services | Auth Service validates tokens; all services check ownership. |
| FR-5: Note CRUD | Note Service, PostgreSQL | Note Service handles note operations, PostgreSQL persists. |
| FR-6: Note Tagging | Note Service, PostgreSQL | Note Service manages tags; normalization enforced in code. |
| FR-7: Full-Text Search | Note Service, PostgreSQL | PostgreSQL full-text search indexes; Note Service queries. |
| FR-8: Event Publishing | Note Service, Redis Streams | Note Service publishes to Streams on note changes. |
| FR-9: Link Suggestions | Link Service, Redis Streams, PostgreSQL | Link Service consumes events, analyzes, stores suggestions. |
| FR-10: Accept/Reject Links | Link Service, PostgreSQL | Link Service provides endpoints; PostgreSQL stores decisions. |
| FR-11: Graph API | Graph Service, PostgreSQL | Graph Service aggregates and filters graph data. |
| FR-12: Notes UI | Frontend (Next.js) | Frontend provides note editor, list, search interface. |
| FR-13: Suggestion Review UI | Frontend (Next.js) | Frontend provides suggestion review component. |
| FR-14: Graph Visualization | Frontend (Next.js, react-force-graph-2d) | Frontend renders 2D graph from Graph API. |
| FR-15: E2E Verification | CI/CD, health endpoints | CI/CD runs E2E tests; services expose health endpoints. |

---

## Architecture Quality Assessment

| Criterion | Status | Evidence |
|-----------|--------|----------|
| **Component Isolation** | ✓ | Each service owns its domain; REST APIs define clear boundaries. |
| **Scalability** | ✓ | Stateless services, horizontal scaling via replicas; database and Redis are shared bottlenecks. |
| **Maintainability** | ✓ | Clear component responsibilities, documented interfaces, consistent technology choices. |
| **Security** | ✓ | JWT-based auth, encrypted passwords, server-side authorization, secrets in env vars. |
| **Resilience** | ⚠ | Single Redis and PostgreSQL instances (no HA); error handling and retry policies documented. |
| **Observability** | ✓ | Structured logging, correlation IDs, health endpoints, documented error scenarios. |

---
