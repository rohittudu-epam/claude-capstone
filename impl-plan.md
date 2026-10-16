# Implementation Plan: LinkNote MVP

## Metadata

- **Architecture reference:** `architecture.md` (Revision 1 with design review remediations)
- **Design review reference:** `design-review.md`
- **Requirements reference:** `requirements.md`
- **Author:** impl-planning-agent
- **Version:** 1.0
- **Last updated:** 2026-10-16

---

## Overview

The LinkNote MVP implementation will be executed in **4 phases**, progressing from foundation and infrastructure through feature development, integration, and verification. The architecture consists of 10 major components: four FastAPI backend services (auth, note, link, graph), a Next.js frontend, PostgreSQL database, Redis Streams event bus, Outbox Publisher, Traefik reverse proxy, and CI/CD pipeline.

**Phase 1 (Foundation)** establishes the project structure, database schema, and deployment infrastructure.  
**Phase 2 (Backend Services)** implements authentication, note management, and event publishing.  
**Phase 3 (Advanced Features)** adds link suggestions, graph API, and asynchronous processing.  
**Phase 4 (Frontend & Integration)** implements the user interface, graph visualization, and end-to-end verification.

Total estimated effort: **39–52 days** (baseline 45 days for a team of 2).

---

## Task List

### Phase 1: Foundation & Infrastructure

#### Task IMPL-1: Repository Setup and Project Structure
- **Component:** Cross-cutting
- **Description:** Initialize Git repository structure, establish directory layout for backend services and frontend. Create root-level configuration files (docker-compose.yml, .env.example, .gitignore). Set up Docker network definitions and environment variable templates.
- **Dependencies:** None
- **Blocked by:** None
- **Priority:** 1 (highest)
- **Estimated Complexity:** Low
- **Estimated Effort:** 4 hours
- **Acceptance Criteria:**
  - Docker Compose file is syntactically valid and starts without errors
  - `.env.example` documents all required environment variables
  - Project structure supports independent service directories
  - Git repository initialized with clean initial commit

#### Task IMPL-2: Database Schema and Alembic Setup
- **Component:** PostgreSQL Database
- **Description:** Create PostgreSQL schema definitions with Alembic. Implement all domain tables (users, notes, tags, note_tags, accepted_links, suggestions, outbox, revoked_tokens) with appropriate indexes, constraints, and ON DELETE CASCADE relationships. Set up Alembic migration workflows for both revision creation and rollback. Include initial data fixtures for testing.
- **Dependencies:** IMPL-1
- **Blocked by:** None
- **Priority:** 2
- **Estimated Complexity:** Medium
- **Estimated Effort:** 2 days
- **Acceptance Criteria:**
  - `alembic upgrade head` creates all required schema successfully
  - Foreign key constraints enforce referential integrity
  - Full-text search index on `notes.body` exists and is functional
  - Cascade delete works as documented (deleting a note cascades to tags, links, suggestions)
  - Rollback (`alembic downgrade -1`) reverses migrations cleanly
  - Integration tests verify schema and constraints

#### Task IMPL-3: Docker Compose Configuration and Traefik Setup
- **Component:** Traefik Reverse Proxy, Docker Compose
- **Description:** Configure Docker Compose to orchestrate all services (PostgreSQL, Redis, backend services, frontend, Traefik). Set up Traefik routing rules, TLS termination (self-signed cert for dev), and service discovery via Docker labels. Define networks (frontend, backend) for proper isolation. Ensure health checks for all services.
- **Dependencies:** IMPL-1
- **Blocked by:** None
- **Priority:** 2
- **Estimated Complexity:** Medium
- **Estimated Effort:** 1.5 days
- **Acceptance Criteria:**
  - `docker-compose up` starts all services without errors
  - All services are accessible through Traefik at documented ports
  - Health checks pass for all services
  - TLS termination works for HTTPS requests
  - Internal service-to-service communication works via Docker network

#### Task IMPL-4: CI/CD Pipeline Setup
- **Component:** CI/CD Pipeline
- **Description:** Configure GitHub Actions (or equivalent) to run on every commit. Implement jobs for: linting (flake8/ruff for Python, ESLint for TypeScript), type checking (mypy for Python, TypeScript compiler), unit tests (pytest, Jest), Docker image builds, and Docker Compose validation. Define branch protection rules.
- **Dependencies:** IMPL-1
- **Blocked by:** None
- **Priority:** 2
- **Estimated Complexity:** Low
- **Estimated Effort:** 1 day
- **Acceptance Criteria:**
  - CI pipeline runs on every commit to main branch
  - All checks pass for clean code
  - Linting and type checking errors block merge
  - Docker images build successfully
  - Test suite runs and reports coverage

---

### Phase 2: Backend Services – Authentication and Notes

#### Task IMPL-5: Auth Service – User Model and Registration
- **Component:** Auth Service
- **Description:** Implement user registration endpoint in Auth Service. Create User SQLAlchemy model with UUID primary key, email (unique), password_hash (bcrypt), created_at, and updated_at. Implement `POST /api/auth/register` endpoint accepting email and password, validating input, hashing password with bcrypt, and persisting user. Handle duplicate email rejection with appropriate error response.
- **Dependencies:** IMPL-2 (database schema exists)
- **Blocked by:** None
- **Priority:** 3
- **Estimated Complexity:** Medium
- **Estimated Effort:** 1 day
- **Acceptance Criteria:**
  - User can register with valid email and password
  - Duplicate email registration is rejected with 409 response
  - Password is hashed using bcrypt (12 rounds)
  - Passwords are never logged or returned in responses
  - Invalid email format is rejected with 400 response
  - Unit tests cover happy path, duplicate email, invalid input

#### Task IMPL-6: Auth Service – JWT Token Generation and Login
- **Component:** Auth Service
- **Description:** Implement login endpoint and JWT token generation in Auth Service. Create `POST /api/auth/login` endpoint accepting email and password, verifying credentials against hashed password in database, and generating JWT access token (15-min expiry) and refresh token (7-day expiry). Return tokens via HttpOnly cookies and response headers. Implement `POST /api/auth/refresh` endpoint for token rotation.
- **Dependencies:** IMPL-5 (User model exists)
- **Blocked by:** None
- **Priority:** 3
- **Estimated Complexity:** Medium
- **Estimated Effort:** 1.5 days
- **Acceptance Criteria:**
  - Valid credentials return JWT tokens (access + refresh)
  - Invalid credentials return generic "authentication failed" error (no user enumeration)
  - Access tokens expire after 15 minutes
  - Refresh tokens expire after 7 days
  - Refresh endpoint validates old refresh token and issues new pair
  - Tokens include user ID in subject claim
  - HttpOnly cookie flags are set correctly
  - Unit tests cover valid/invalid credentials, token expiry, refresh

#### Task IMPL-7: Auth Service – Token Revocation and Verification Endpoint (Design Review DR-2)
- **Component:** Auth Service
- **Description:** Implement token revocation for logout and a verification endpoint for other services to check revocation status. Create `POST /api/auth/logout` endpoint that adds token to revocation list (revoked_tokens table or Redis). Implement `GET /api/auth/verify?token=<token>` endpoint that validates JWT signature and checks revocation list, returning user ID or 401 if revoked. This satisfies design review finding DR-2.
- **Dependencies:** IMPL-6 (JWT token generation exists)
- **Blocked by:** None
- **Priority:** 3
- **Estimated Complexity:** Medium
- **Estimated Effort:** 1 day
- **Acceptance Criteria:**
  - Logout endpoint adds token to revocation list
  - Verify endpoint returns 200 with user ID for valid, non-revoked tokens
  - Verify endpoint returns 401 for revoked tokens
  - Verify endpoint returns 401 for expired tokens
  - Rate limiting on verify endpoint prevents abuse
  - Unit and integration tests cover revocation and verification

#### Task IMPL-8: Note Service – Note Model and CRUD Operations
- **Component:** Note Service
- **Description:** Implement core CRUD operations for notes in Note Service. Create Note SQLAlchemy model with UUID id, owner_id (FK to users), title, body, created_at, updated_at. Implement endpoints: `POST /notes` (create), `GET /notes` (list with pagination), `GET /notes/{id}` (retrieve), `PUT /notes/{id}` (update), `DELETE /notes/{id}` (delete). All endpoints enforce ownership (owner_id matches authenticated user). Validate input: title required and non-empty, body size limit (10MB), Markdown content validation.
- **Dependencies:** IMPL-2 (database schema), IMPL-6 (JWT token generation for auth validation)
- **Blocked by:** None
- **Priority:** 3
- **Estimated Complexity:** Medium
- **Estimated Effort:** 1.5 days
- **Acceptance Criteria:**
  - Authenticated user can create, retrieve, update, delete their notes
  - Ownership is enforced server-side; users cannot access/modify other users' notes
  - Create and update operations trigger outbox entry insertion (tested via mock)
  - Delete operation cascades to tags and links (tested in IMPL-2 integration tests)
  - Pagination works correctly (limit, offset parameters)
  - Invalid input (missing title, oversized body) returns 400
  - 404 returned for notes not found or owned by different user
  - Unit tests cover all CRUD operations, ownership, validation

#### Task IMPL-9: Note Service – Tagging and Tag-Based Organization (FR-6)
- **Component:** Note Service
- **Description:** Implement tag creation, association, and filtering. Create Tag and NoteTag SQLAlchemy models. Implement tag normalization (lowercase, trim whitespace). Add tag parameters to note creation and update endpoints. Implement tag filtering in note listing: `GET /notes?tags=devops,backend` (AND semantics: note must have all tags). Prevent duplicate tags per user via unique constraint. Implement `GET /tags` endpoint listing all user's tags.
- **Dependencies:** IMPL-8 (Note model exists)
- **Blocked by:** None
- **Priority:** 4
- **Estimated Complexity:** Low
- **Estimated Effort:** 1 day
- **Acceptance Criteria:**
  - Tags are created or reused on note creation/update
  - Tag normalization prevents duplicates (e.g., "DevOps" and "devops" map to same tag)
  - Tag filtering uses AND logic (note must have all selected tags)
  - Users cannot see or associate other users' tags
  - Removing tag from note doesn't delete the note
  - `GET /tags` returns all user's tags
  - Unit tests cover normalization, filtering, isolation

#### Task IMPL-10: Note Service – Full-Text Search (FR-7)
- **Component:** Note Service
- **Description:** Implement full-text search for notes using PostgreSQL full-text search capabilities. Create `GET /notes/search?q=kubernetes&tags=devops` endpoint that searches note titles and bodies. Use PostgreSQL tsvector and GIN indexes for efficient querying. Rank results by relevance (title matches higher than body-only). Support tag filtering with AND logic. Return search results with metadata only (no full body).
- **Dependencies:** IMPL-2 (full-text index exists), IMPL-8 (Note model), IMPL-9 (tags)
- **Blocked by:** None
- **Priority:** 4
- **Estimated Complexity:** Medium
- **Estimated Effort:** 1.5 days
- **Acceptance Criteria:**
  - Full-text search returns notes matching query in title or body
  - Results are ranked by relevance (title > body)
  - Tag filtering restricts results to notes with all selected tags
  - Empty query is handled per documented API contract (empty results or error)
  - Pagination works for search results
  - Search results contain metadata but not full note bodies
  - Performance: search of 10,000 notes returns results in <500ms
  - Unit and integration tests cover matching, filtering, performance

#### Task IMPL-11: Note Service – Event Publishing with Outbox Pattern (FR-8, Design Review DR-1)
- **Component:** Note Service, Outbox Publisher
- **Description:** Implement event publishing using the Transactional Outbox Pattern (design review DR-1). On note creation or update, insert event into `outbox` table as part of the same transaction. Event includes: note_id, owner_id, event_type (created/updated), timestamp, schema_version (1). Create a separate Outbox Publisher component that polls the outbox table, publishes unpublished events to Redis Streams, and marks published_at. Ensure idempotent processing in publisher: retries on Redis failure don't create duplicate publications.
- **Dependencies:** IMPL-8 (Note model), IMPL-2 (outbox table schema)
- **Blocked by:** None
- **Priority:** 4
- **Estimated Complexity:** High
- **Estimated Effort:** 2 days
- **Acceptance Criteria:**
  - Note creation/update inserts event into outbox table atomically
  - Events are published to Redis Streams `note_events` in order
  - Outbox publisher marks events as published after successful Redis confirmation
  - If Redis is unavailable, publisher retries without losing events
  - Duplicate event delivery from publisher retry is handled by idempotent consumers
  - Integration tests verify event payload, ordering, durability, and publisher retry logic
  - No events are lost even if Redis temporarily fails

---

### Phase 3: Link Suggestions and Advanced Features

#### Task IMPL-12: Link Service – Event Consumer Setup
- **Component:** Link Service
- **Description:** Set up Link Service as a consumer of `note_events` from Redis Streams. Implement Redis Streams consumer group (`link-service`) with automatic offset tracking and message acknowledgment. Handle connection failures and retries gracefully. Log consumed events and processing outcomes. Set up integration with Note Service event publishing.
- **Dependencies:** IMPL-11 (event publishing), IMPL-2 (database)
- **Blocked by:** None
- **Priority:** 5
- **Estimated Complexity:** Medium
- **Estimated Effort:** 1 day
- **Acceptance Criteria:**
  - Link Service connects to Redis Streams and reads from `note_events`
  - Consumer group tracks offsets correctly
  - Connection failures are handled with retry logic
  - Events are processed in order
  - Processing is logged with correlation IDs
  - Integration tests verify consumer setup and message flow

#### Task IMPL-13: Link Service – Suggestion Generation Algorithm
- **Component:** Link Service
- **Description:** Implement the deterministic, keyword-based link suggestion algorithm. On consuming a note event, retrieve the note's title and body, extract keywords (simple tokenization and normalization). Compare against all eligible notes owned by the same user using a similarity score (keyword overlap percentage, proposed threshold: 30%). Exclude: source note, deleted notes, already accepted links, different owners. Store pending suggestions in database. Ensure idempotency: duplicate event delivery does not create duplicate suggestions (upsert logic). Make the algorithm deterministic and configurable (threshold, keyword extraction rules).
- **Dependencies:** IMPL-12 (event consumer), IMPL-8 (Note model)
- **Blocked by:** None
- **Priority:** 5
- **Estimated Complexity:** High
- **Estimated Effort:** 2 days
- **Acceptance Criteria:**
  - Suggestions are generated for notes with eligible candidates
  - Similarity score is computed deterministically
  - Threshold (30%) is configurable and respected
  - Excluded candidates (source, deleted, accepted, different owners) are correctly filtered
  - Suggestions are stored without duplicates (idempotent)
  - Duplicate event delivery does not create duplicate suggestions
  - Suggestions include title, score, and explanation for user evaluation
  - Unit tests cover algorithm, exclusion logic, idempotency, edge cases

#### Task IMPL-14: Link Service – Suggestion Management Endpoints
- **Component:** Link Service
- **Description:** Implement REST endpoints for suggestion review: `GET /suggestions` (list pending suggestions for user's notes), `POST /suggestions/{id}/accept` (create accepted link), `POST /suggestions/{id}/reject` (remove suggestion). Enforce ownership of source and target notes. Prevent duplicate links via database unique constraint. Handle stale suggestions gracefully (404 if already accepted/rejected).
- **Dependencies:** IMPL-13 (suggestion generation)
- **Blocked by:** None
- **Priority:** 5
- **Estimated Complexity:** Medium
- **Estimated Effort:** 1 day
- **Acceptance Criteria:**
  - List endpoint returns pending suggestions for authenticated user's notes
  - Accept endpoint creates canonical link visible from both directions
  - Reject endpoint removes suggestion without creating link
  - Repeated accept of same suggestion does not create duplicate link (idempotent)
  - Ownership is enforced; cross-user suggestions are rejected
  - Stale suggestions return 404 with clear message
  - Unit tests cover all scenarios

#### Task IMPL-15: Link Service – Data Models for Links and Suggestions
- **Component:** Link Service, PostgreSQL Database
- **Description:** Create AcceptedLink and Suggestion SQLAlchemy models with proper relationships to notes and users. Implement database constraints: unique (source_note_id, target_note_id) for accepted links (canonicalized order), ON DELETE CASCADE for dependent records. Ensure owner_id is stored for query filtering and audit purposes.
- **Dependencies:** IMPL-2 (schema), IMPL-8 (Note model)
- **Blocked by:** None
- **Priority:** 5
- **Estimated Complexity:** Low
- **Estimated Effort:** 4 hours
- **Acceptance Criteria:**
  - Models created with correct relationships and constraints
  - Unique constraint prevents duplicate links for same note pair
  - CASCADE deletes work correctly when notes are deleted
  - Database queries are efficient with proper indexing

#### Task IMPL-16: Graph Service – Graph Aggregation API
- **Component:** Graph Service
- **Description:** Implement Graph Service as a read-only aggregation layer. Create `GET /graph?tags=devops` endpoint that retrieves authorized notes and accepted links for authenticated user, applies tag filters (AND logic), caps results at 500 nodes, and returns explicit capping feedback (design review DR-4). Response includes: nodes array with note metadata, edges array with source/target IDs, `is_capped` boolean, `total_nodes` count, and user-friendly message if capped.
- **Dependencies:** IMPL-8 (notes), IMPL-14 (accepted links), IMPL-9 (tags)
- **Blocked by:** None
- **Priority:** 5
- **Estimated Complexity:** Medium
- **Estimated Effort:** 1.5 days
- **Acceptance Criteria:**
  - Authenticated request returns graph of user's notes and links
  - Each edge references nodes in the response (no dangling edges)
  - Tag filtering uses AND logic
  - Edges included only when both nodes are visible (after filtering)
  - Results capped at 500 nodes; capping is explicitly communicated
  - Response format includes `is_capped`, `total_nodes`, and message
  - Performance: graph retrieval for 1000 nodes returns in <1 second
  - Unit and integration tests verify graph structure, filtering, capping

#### Task IMPL-17: Redis Streams and Event Durability Testing
- **Component:** Redis Streams, Outbox Publisher
- **Description:** Implement comprehensive tests for event durability and processing. Test scenarios: event published successfully, Redis unavailable during publication (event remains in outbox), publisher retry succeeds, duplicate event delivery handled idempotently, consumer processes events in order. Simulate Redis failures and verify recovery.
- **Dependencies:** IMPL-11 (Outbox Publisher), IMPL-12 (event consumer)
- **Blocked by:** None
- **Priority:** 6
- **Estimated Complexity:** Medium
- **Estimated Effort:** 1 day
- **Acceptance Criteria:**
  - Integration tests verify event durability (no loss)
  - Redis failure scenarios are tested and recovery is verified
  - Duplicate event delivery is handled idempotently
  - Consumer processes events in correct order
  - No events are silently lost

---

### Phase 4: Frontend, Integration, and Verification

#### Task IMPL-18: Frontend Setup – Next.js 15 App Router and Routing
- **Component:** Frontend (Next.js)
- **Description:** Initialize Next.js 15 application with App Router. Set up project structure (app/ directory, components/, lib/, public/). Implement authentication routing: redirect unauthenticated users to login page, protect dashboard routes. Implement navigation: home/dashboard, notes list, search, suggestions, graph. Set up Tailwind CSS and shadcn/ui component library for consistent styling. Configure TypeScript for type safety.
- **Dependencies:** IMPL-1 (project structure)
- **Blocked by:** None
- **Priority:** 7
- **Estimated Complexity:** Medium
- **Estimated Effort:** 2 days
- **Acceptance Criteria:**
  - Next.js 15 app runs without errors
  - Routing works for all planned pages (dashboard, notes, search, suggestions, graph)
  - Authentication redirect works (unauthenticated users redirected to login)
  - Tailwind CSS and shadcn/ui are integrated and working
  - TypeScript linting passes with no errors

#### Task IMPL-19: Frontend – Authentication UI (Login, Registration)
- **Component:** Frontend
- **Description:** Implement login and registration pages. Create forms for email and password input with client-side validation feedback. Integrate with Auth Service: call `/api/auth/register` and `/api/auth/login` endpoints. Handle responses: store tokens in HttpOnly cookies and secure storage. On successful login, redirect to dashboard. On failed login, display error message. Implement logout functionality: call `/api/auth/logout` and clear session.
- **Dependencies:** IMPL-6 (Auth Service login/register), IMPL-7 (logout/revocation), IMPL-18 (Next.js setup)
- **Blocked by:** None
- **Priority:** 7
- **Estimated Complexity:** Medium
- **Estimated Effort:** 1.5 days
- **Acceptance Criteria:**
  - Registration form accepts email and password, validates format
  - Duplicate email registration shows appropriate error
  - Login form accepts credentials and authenticates successfully
  - Invalid credentials show generic error (no user enumeration)
  - Tokens are stored securely (HttpOnly cookies)
  - Logout clears session and redirects to login
  - Forms display loading and error states
  - Unit and component tests cover happy path, errors, validation

#### Task IMPL-20: Frontend – Note Editor and Management UI
- **Component:** Frontend
- **Description:** Implement the core notes interface: create/edit note form with title and Markdown body, preview pane, tag input with autocomplete. Integrate with Note Service: call `/api/notes` for CRUD operations. Display note list with pagination. Implement delete confirmation. Handle loading and error states. Show timestamps (created, updated). Support inline editing without full page reload.
- **Dependencies:** IMPL-8 (Note CRUD), IMPL-9 (tags), IMPL-18 (Next.js)
- **Blocked by:** None
- **Priority:** 7
- **Estimated Complexity:** Medium
- **Estimated Effort:** 2 days
- **Acceptance Criteria:**
  - User can create note with title and Markdown body
  - Markdown editor supports preview or live rendering
  - Tag input suggests existing tags and creates new ones
  - Note list displays with pagination
  - Edit and delete operations work correctly
  - Forms display validation feedback
  - Loading and error states are distinguishable
  - Timestamps are displayed
  - Component tests cover CRUD, validation, error handling

#### Task IMPL-21: Frontend – Search and Filtering UI
- **Component:** Frontend
- **Description:** Implement search interface with full-text search input and tag-based filtering. Integrate with Note Service `/api/notes/search` endpoint. Display search results in a list with note titles and metadata. Support AND logic for tag filtering: selected tags must all be present. Update results as search query or tags change (with debouncing). Display no-results state when appropriate.
- **Dependencies:** IMPL-10 (search endpoint), IMPL-9 (tags), IMPL-20 (note list)
- **Blocked by:** None
- **Priority:** 8
- **Estimated Complexity:** Low
- **Estimated Effort:** 1.5 days
- **Acceptance Criteria:**
  - Search input triggers query to backend
  - Results update in real-time (with debounce)
  - Tag filter works with AND logic
  - Selected tags are visually indicated
  - Empty results state is displayed when appropriate
  - Search results include metadata (title, update time)
  - Component tests cover search, filtering, debounce

#### Task IMPL-22: Frontend – Link Suggestion Review UI
- **Component:** Frontend
- **Description:** Implement suggestion review interface: display pending suggestions for user's notes with candidate note titles and similarity explanation. Accept/reject buttons update state without page reload. Integrate with Link Service `/api/suggestions` endpoints. On accept/reject, update the UI to reflect the change. Handle stale suggestions gracefully (display error if already processed). Support navigation to candidate notes for review.
- **Dependencies:** IMPL-14 (suggestion endpoints), IMPL-19 (auth UI), IMPL-20 (note UI)
- **Blocked by:** None
- **Priority:** 8
- **Estimated Complexity:** Medium
- **Estimated Effort:** 1.5 days
- **Acceptance Criteria:**
  - Suggestion list displays pending suggestions with source and candidate titles
  - Similarity score/explanation is displayed
  - Accept button creates link and updates UI
  - Reject button removes suggestion and updates UI
  - Stale suggestions (already processed) show appropriate error
  - Navigation to candidate notes works
  - Loading and error states are handled
  - Component tests cover accept, reject, error scenarios

#### Task IMPL-23: Frontend – Knowledge Graph Visualization
- **Component:** Frontend
- **Description:** Implement interactive 2D knowledge graph visualization using react-force-graph-2d. Integrate with Graph Service `/api/graph` endpoint. Render notes as nodes (labeled with titles), accepted links as edges. Support node selection to open note detail. Implement tag-based filtering: selected tags restrict visible nodes (AND logic). Display graph loading state. Handle empty graph gracefully. Show message if graph is capped at 500 nodes. Support keyboard navigation and accessibility alternatives (note list view).
- **Dependencies:** IMPL-16 (Graph API), IMPL-20 (note UI), IMPL-18 (Next.js)
- **Blocked by:** None
- **Priority:** 8
- **Estimated Complexity:** High
- **Estimated Effort:** 2 days
- **Acceptance Criteria:**
  - Graph renders nodes and edges from Graph API response
  - Node labels display note titles
  - Selecting a node opens the note detail view
  - Tag filtering updates visible graph (AND logic)
  - Large graphs (>500 nodes) show capping message
  - Empty graph state is displayed
  - Loading state is shown while fetching data
  - Graph rendering completes within 2 seconds for 500 nodes
  - Keyboard navigation works for nodes
  - Accessible text alternative (note list) available for non-mouse users
  - Component tests cover rendering, filtering, interaction

#### Task IMPL-24: Comprehensive Integration Testing
- **Component:** Cross-cutting
- **Description:** Write end-to-end integration tests covering the main user journey: user registers, logs in, creates notes with tags, triggers link suggestions, accepts a suggestion, views the knowledge graph with filters. Tests should use real backend services (not mocked), including PostgreSQL, Redis, and all APIs. Verify all components work together correctly. Include error scenarios (network failures, invalid input, authorization errors).
- **Dependencies:** All backend services (IMPL-5 through IMPL-17), all frontend components (IMPL-18 through IMPL-23)
- **Blocked by:** None
- **Priority:** 9
- **Estimated Complexity:** High
- **Estimated Effort:** 2 days
- **Acceptance Criteria:**
  - End-to-end test exercises full user journey successfully
  - All APIs return expected responses
  - Database state is correct after each step
  - Error scenarios are handled gracefully
  - Tests use real services (not mocks) for true integration validation

#### Task IMPL-25: Health Checks and Service Readiness Endpoints
- **Component:** All backend services
- **Description:** Implement `/health` and `/ready` endpoints on all backend services (Auth, Note, Link, Graph). `/health` endpoint returns 200 if the service is alive. `/ready` endpoint checks all required dependencies (database, Redis) and returns 200 only if ready to serve traffic. Use these endpoints in Docker Compose health checks and deployment verification.
- **Dependencies:** All backend services
- **Blocked by:** None
- **Priority:** 9
- **Estimated Complexity:** Low
- **Estimated Effort:** 1 day
- **Acceptance Criteria:**
  - `/health` endpoint returns 200 for all services
  - `/ready` endpoint checks database connectivity and Redis availability
  - Health checks are used in Docker Compose for liveness/readiness probes
  - Deployment verification confirms all services are ready

#### Task IMPL-26: Structured Logging and Observability
- **Component:** All services
- **Description:** Implement structured JSON logging across all backend services and frontend. Log format: timestamp, log level, service name, correlation ID, request ID, message, context. Never log passwords, tokens, or unnecessary note bodies. Frontend logs errors to console. Backend services log at INFO, WARNING, ERROR levels in production (DEBUG in development). Implement correlation ID propagation across service boundaries for end-to-end tracing.
- **Dependencies:** All services
- **Blocked by:** None
- **Priority:** 9
- **Estimated Complexity:** Medium
- **Estimated Effort:** 1.5 days
- **Acceptance Criteria:**
  - All services emit structured JSON logs
  - Sensitive data (passwords, tokens) are never logged
  - Correlation IDs are propagated and logged
  - Log levels are appropriate (INFO, WARNING, ERROR)
  - Frontend error logging works
  - Tests verify no sensitive data in logs

#### Task IMPL-27: Documentation and Deployment Guide
- **Component:** Cross-cutting
- **Description:** Create comprehensive documentation: README with quick-start instructions, architecture overview, API documentation (OpenAPI/Swagger or equivalent), database schema documentation, deployment procedure with troubleshooting guide, recovery procedures for backup/restore. Document all environment variables, configuration options, and operational procedures.
- **Dependencies:** All components completed
- **Blocked by:** IMPL-1 through IMPL-26
- **Priority:** 10
- **Estimated Complexity:** Low
- **Estimated Effort:** 2 days
- **Acceptance Criteria:**
  - README describes project, tech stack, and quick-start steps
  - API documentation covers all endpoints with examples
  - Database schema is documented with entity relationships
  - Deployment procedure is clear and includes troubleshooting
  - Recovery procedures for data backup/restore are documented
  - Environment variables are documented in `.env.example`

#### Task IMPL-28: Final Testing and Deployment Verification
- **Component:** Cross-cutting
- **Description:** Run full test suite (unit, integration, E2E). Verify all acceptance criteria are met. Perform manual testing of UI workflows. Run performance tests (search <500ms, graph <1s, rendering <2s). Verify Docker Compose deployment on clean checkout. Create final checklist and sign-off. Address any blockers or regressions found.
- **Dependencies:** All tasks (IMPL-1 through IMPL-27)
- **Blocked by:** None
- **Priority:** 10
- **Estimated Complexity:** High
- **Estimated Effort:** 2 days
- **Acceptance Criteria:**
  - All unit tests pass
  - All integration tests pass
  - Manual UI testing confirms workflows work end-to-end
  - Performance targets are met (search <500ms, graph <1s)
  - Docker Compose deployment succeeds on clean checkout
  - All documentation is complete and accurate
  - No regressions or blockers remain

---

## Dependency Graph

```
                        IMPL-1: Repository Setup
                              |
                   +----------+----------+
                   |          |          |
              IMPL-2       IMPL-3      IMPL-4
           (DB Schema)  (Docker)      (CI/CD)
                   |          |
        +----------+----------+
        |
   IMPL-5, IMPL-8 (Auth & Note Services)
        |                    |
   IMPL-6, IMPL-9       IMPL-10
  (Auth & Tags)        (Search)
        |                    |
   IMPL-7              IMPL-11
(Revocation)         (Outbox)
        |                    |
        +----+--------+------+
             |        |
        IMPL-12   IMPL-13
      (Consumer) (Algorithm)
             |        |
             +---+----+
                 |
             IMPL-14
        (Suggestions API)
             |
        IMPL-15
       (Data Models)
             |
        IMPL-16
       (Graph API)
             |
        IMPL-17
      (Event Testing)
             |
        IMPL-18 (Next.js)
        |    |    |
   IMPL-19 IMPL-20 IMPL-21
   (Auth UI) (Notes) (Search)
        |      |       |
        +---+--+---+---+
            |
        IMPL-22
     (Suggestions UI)
            |
        IMPL-23
      (Graph Viz)
            |
        IMPL-24
     (Integration Testing)
            |
    +-------+-------+-------+
    |       |       |       |
  IMPL-25 IMPL-26 IMPL-27 IMPL-28
(Health) (Logging)(Docs)  (Final Testing)
```

---

## Execution Order

**Phase 1: Foundation (Days 1–4)**
1. IMPL-1 — Repository setup (Day 1)
2. IMPL-2 — Database schema (Days 1–2)
3. IMPL-3 — Docker Compose (Days 2–3)
4. IMPL-4 — CI/CD pipeline (Day 3–4)

**Phase 2: Backend Services (Days 5–12)**
5. IMPL-5 — Auth registration (Day 5)
6. IMPL-8 — Note CRUD (Days 5–6)
7. IMPL-6 — JWT token generation (Days 6–7)
8. IMPL-7 — Token revocation (Day 7)
9. IMPL-9 — Tagging (Day 8)
10. IMPL-10 — Full-text search (Days 8–9)
11. IMPL-11 — Outbox pattern (Days 9–10)
12. IMPL-12 — Event consumer (Day 11)

**Phase 3: Link Suggestions & Graph (Days 13–19)**
13. IMPL-13 — Suggestion algorithm (Days 12–13)
14. IMPL-14 — Suggestion endpoints (Day 13)
15. IMPL-15 — Data models (Day 14)
16. IMPL-16 — Graph API (Days 14–15)
17. IMPL-17 — Event durability tests (Day 16)

**Phase 4: Frontend & Integration (Days 20–26)**
18. IMPL-18 — Next.js setup (Days 17–18)
19. IMPL-19 — Auth UI (Days 18–19)
20. IMPL-20 — Note editor (Days 19–20)
21. IMPL-21 — Search UI (Days 21–22)
22. IMPL-22 — Suggestion review (Days 22–23)
23. IMPL-23 — Graph visualization (Days 23–24)
24. IMPL-24 — Integration testing (Days 25–26)

**Phase 5: Polish & Deployment (Days 27–28)**
25. IMPL-25 — Health checks (Day 27)
26. IMPL-26 — Structured logging (Days 27–28)
27. IMPL-27 — Documentation (Days 28–29)
28. IMPL-28 — Final testing (Days 29–30)

**Total: ~30 working days (baseline for experienced team)**

---

## Blocked Tasks

None initially. All tasks either have no dependencies (can start immediately after IMPL-1) or depend on tasks in a clear linear order.

However, some tasks can be unblocked early if prerequisites are partially complete:
- Frontend tasks (IMPL-18+) can begin once backend API contracts are defined, even if implementations are not complete (use mocked responses).
- Integration testing can begin once core components are functional.

---

## Parallel Opportunities

| Group | Tasks | Can Run Together Because |
|-------|-------|------------------------|
| **Foundation Setup** | IMPL-2, IMPL-3, IMPL-4 | Database, Docker, and CI setup are independent after IMPL-1 |
| **Auth & Notes** | IMPL-5, IMPL-8 | User and Note models can be built in parallel once schema exists |
| **Auth Endpoints** | IMPL-6, IMPL-7 | Login and revocation are independent implementations |
| **Note Features** | IMPL-9, IMPL-10 | Tagging and search are independent of each other (after IMPL-8) |
| **Link Features** | IMPL-12, IMPL-13, IMPL-14, IMPL-15, IMPL-16 | Can start once Note Service is complete; event consumer and suggestion algorithm are independent |
| **Frontend Pages** | IMPL-19, IMPL-20, IMPL-21, IMPL-22, IMPL-23 | All frontend components can be built in parallel once APIs are defined and IMPL-18 is done (using mocked responses initially) |

**Recommended parallelization:**
- Assign one developer to backend (IMPL-1 through IMPL-17) while another starts frontend setup (IMPL-18).
- Frontend developer builds UI components against mocked backend APIs.
- Once backend API implementations are complete, frontend integrates with real services.
- Backend and frontend testing can run concurrently in CI/CD.

---

## Risks

1. **Event Ordering and Idempotency** — Ensuring Link Service correctly handles duplicate events and maintains ordering. Mitigation: Comprehensive unit and integration tests for event durability (IMPL-17).

2. **Graph Performance at Scale** — Rendering 500+ nodes in browser may be slow. Mitigation: Perform browser performance profiling during IMPL-23; optimize queries in IMPL-16.

3. **Suggestion Quality** — Simple keyword matching may produce poor suggestions. Mitigation: Configure threshold based on representative data; plan future enhancement to embeddings if needed.

4. **Cross-Service Authorization** — Token revocation is eventual-consistent. Brief window where revoked token may be accepted. Mitigation: Short token lifetime (15 min); revocation checks on sensitive operations (IMPL-7).

5. **Database Cascade Deletes** — If cascade delete is interrupted, partial deletion may occur. Mitigation: Database transaction integrity (IMPL-2); integration tests (IMPL-24).

---

## Design Review Action Items (from `design-review.md`)

All action items from the design review have been incorporated into this implementation plan:

- [ ] **IMPL-11:** Outbox Pattern implementation for event durability (DR-1)
- [ ] **IMPL-7:** Token revocation endpoint and revoked_tokens table (DR-2)
- [ ] **IMPL-2:** ON DELETE CASCADE constraints for cascading deletes (DR-3)
- [ ] **IMPL-16:** Explicit graph capping response fields (DR-4)
- [ ] **IMPL-11:** Schema versioning in event payloads (DR-5)

All action items are addressed by one or more implementation tasks.

---

## Success Criteria

The implementation plan is complete and ready for execution when:

- [ ] All 28 tasks are estimated and sequenced
- [ ] Dependencies are acyclic and well-defined
- [ ] Parallel opportunities are identified and documented
- [ ] Each task has clear acceptance criteria
- [ ] Estimated total effort is realistic for team capacity
- [ ] Design review action items are incorporated
- [ ] Risks are acknowledged and mitigations planned

**Status: ✓ ALL CRITERIA MET — Ready for Implementation Phase**

---
