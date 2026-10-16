# Requirements Document: LinkNote MVP

## User Story

LinkNote is a privacy-friendly personal knowledge management application that helps users create Markdown notes and discover meaningful relationships between them through automatically generated, user-approved link suggestions. The MVP covers the complete workflow: local development and deployment setup, authentication, note and tag management, full-text search, asynchronous link discovery, bidirectional links, and interactive knowledge graph visualization.

---

## Functional Requirements

### FR-1: Reproducible Development Environment
- **Description:** The system must provide a Docker Compose configuration that starts all MVP services (auth-service, note-service, link-service, graph-service, frontend, PostgreSQL, Redis, reverse proxy) and their dependencies with a single command.
- **Acceptance Criteria:**
  - Docker Compose starts all services successfully on a clean checkout
  - Configuration is read from environment variables; `.env.example` documents all required settings without including real credentials
  - CI pipeline executes linting, type checks, and baseline tests for both backend and frontend
  - Service startup failures produce actionable error messages, not silent failures
  - All services are accessible through the configured reverse proxy (Traefik)

### FR-2: Database Persistence with SQLAlchemy 2.0 and Alembic
- **Description:** The system must establish a PostgreSQL database with SQLAlchemy 2.0 models and Alembic migrations for all domain entities (users, notes, tags, note-tag associations, accepted links, and suggestions).
- **Acceptance Criteria:**
  - Database migrations create required schema for all domain entities with appropriate constraints
  - Primary keys, foreign keys, uniqueness constraints, and timestamps enforce documented data-integrity rules
  - Accepted links cannot be duplicated for the same logical note pair regardless of insertion order
  - A fresh database can be initialized from migrations; existing databases can be upgraded through the migration chain
  - Automated integration tests verify persistence, constraint enforcement, and migration behavior

### FR-3: User Registration and Authentication
- **Description:** The system must provide secure user registration, login, and session management through the auth-service using email/password credentials and JWT tokens.
- **Acceptance Criteria:**
  - A user can register with a valid email address and password; duplicate email addresses are rejected
  - Valid credentials produce a JWT-based authentication response with access and refresh tokens
  - Invalid credentials produce a generic authentication error without disclosing whether the email exists
  - Access tokens expire after a configured duration (proposed: 15 minutes)
  - Refresh tokens support token rotation; invalid or expired refresh tokens are rejected
  - Passwords are hashed using a modern algorithm (bcrypt or equivalent); plaintext passwords are never stored or logged
  - All authentication endpoints implement rate limiting to prevent brute-force attacks

### FR-4: User Session Authorization
- **Description:** The system must enforce server-side authorization such that protected endpoints only expose resources owned by the authenticated user.
- **Acceptance Criteria:**
  - All protected service endpoints require a valid access token in the request header
  - Resources are scoped to the owning user; no endpoint exposes another user's notes, tags, links, or suggestions
  - Expired or invalid tokens are rejected with a clear error response
  - Attempted access to unauthorized resources returns an appropriate error without leaking the existence of other resources

### FR-5: Note Creation, Reading, Updating, and Deletion
- **Description:** The system must provide CRUD operations for Markdown notes through the note-service, scoped to the authenticated user.
- **Acceptance Criteria:**
  - An authenticated user can create a note with a title and Markdown body
  - Created notes are assigned a stable UUID identifier, owner ID, created_at, and updated_at timestamps
  - The note owner can retrieve, update, and delete notes
  - Updates change the updated_at timestamp; the created_at timestamp remains unchanged
  - Deletion permanently removes the note and cascades dependent records (accepted links and pending suggestions referencing that note)
  - Invalid payloads (missing title, oversized body, malformed Markdown) are rejected with documented errors
  - Successful note creation, update, and deletion produce domain events for downstream link processing
  - Only the note owner can modify or delete that note

### FR-6: Note Tagging and Organization
- **Description:** The system must allow authenticated users to organize notes with tags, including tag creation, reuse, and filtering.
- **Acceptance Criteria:**
  - A user can assign zero or more tags to a note during creation or update
  - Tags are normalized (case-insensitive, whitespace-trimmed) to prevent duplicate tags for the same user
  - Reusing an existing normalized tag does not create a duplicate tag
  - A user can retrieve all tags associated with a note
  - A user can retrieve all notes associated with one or more tags (AND logic: note must have all selected tags)
  - A user cannot access another user's tags or view another user's categorized notes
  - Removing a tag association updates the note without deleting the note or affecting other tags
  - Tag normalization follows a consistent, documented policy (e.g., lowercase, trim, replace multiple spaces with single space)

### FR-7: Full-Text Note Search
- **Description:** The system must provide full-text search for notes using PostgreSQL capabilities, scoped to the authenticated user.
- **Acceptance Criteria:**
  - A user can search for text contained in note titles or bodies and receive matching notes
  - Search results are restricted to the authenticated user's notes
  - Search results respect selected tag filters (AND semantics)
  - Empty or malformed search parameters are handled according to a documented API contract
  - Search results include note ID, title, owner ID, and update timestamp; full note bodies are not returned in search results
  - Full-text search results are ordered by relevance (title matches ranked higher than body-only matches)
  - Automated integration tests verify matching behavior, tag filtering, and cross-user isolation

### FR-8: Asynchronous Event Publishing for Note Changes
- **Description:** The system must publish domain events when notes are created or updated, using Redis Streams for reliable, retryable asynchronous processing.
- **Acceptance Criteria:**
  - A successful note creation or update produces an event containing the note ID, owner ID, event type (created/updated), and relevant version/timestamp
  - Events are published only after the note is successfully persisted (no events for rejected operations)
  - Redis unavailability or publication failure is observable; the system does not silently lose an event while reporting success to the user
  - Events follow a versioned, documented contract that can be extended without breaking existing consumers
  - Consumers can retry failed processing and safely handle duplicate event delivery (at-least-once semantics)
  - Integration tests verify event payloads, failure modes, and duplicate-delivery handling
  - Event payloads do not include note bodies to minimize data exposure in logs

### FR-9: Automatic Link Suggestions
- **Description:** The system must analyze notes asynchronously in link-service and generate deterministic, keyword-based link suggestions for eligible notes owned by the same user.
- **Acceptance Criteria:**
  - A successfully processed note generates candidate suggestions from eligible notes using a deterministic keyword/title similarity algorithm
  - Candidate selection excludes: the source note, already accepted links, deleted notes, notes of different owners, and stale suggestions
  - Suggestions include note IDs, titles, and a computed similarity score or explanation
  - Suggestions are stored separately from accepted links and flagged for user review
  - Failed suggestion analysis can be retried without creating duplicate pending suggestions
  - Processing is idempotent: duplicate event delivery does not result in duplicate suggestions
  - When a note changes, its pending suggestions are re-evaluated; rejected suggestions remain suppressed until either endpoint note changes
  - The similarity threshold is configurable and established through representative test data (proposed starting point: keyword overlap > 30%)

### FR-10: Link Suggestion Review and Acceptance
- **Description:** The system must allow users to accept or reject pending suggestions, creating canonical bidirectional links.
- **Acceptance Criteria:**
  - A user can retrieve pending suggestions for their notes
  - A user can accept a suggestion, which creates one canonical accepted link visible from both note directions
  - A user can reject a suggestion, which removes it from the pending review list without creating an accepted link
  - Repeated acceptance of the same suggestion does not create duplicate relationships
  - All acceptance/rejection actions enforce ownership of both source and target notes
  - Stale or invalid suggestions are rejected with a documented error response
  - Attempted operations on another user's suggestions return an appropriate error without leaking data

### FR-11: Knowledge Graph API
- **Description:** The system must provide a read-oriented graph API through graph-service that returns authorized notes and accepted relationships.
- **Acceptance Criteria:**
  - An authenticated request returns a graph object containing nodes and edges belonging to the current user
  - Each node represents a note (ID, title, owner ID, created_at, updated_at)
  - Each edge represents an accepted link (source note ID, target note ID)
  - Every edge references valid nodes included in the response (no dangling edges)
  - Tag filters restrict the graph using AND semantics (note must have all selected tags); edges are included only when both endpoints are visible
  - Missing service dependencies, invalid filters, and unauthorized requests produce documented errors without leaking other users' data
  - The graph size is capped at 500 visible nodes; requests exceeding this limit receive a documented response indicating the limit was reached
  - Automated integration tests validate graph integrity, tag filtering, and ownership isolation

### FR-12: Core Notes and Search User Interface
- **Description:** The system must provide a Next.js-based frontend experience for authenticated users to create, edit, browse, and search notes.
- **Acceptance Criteria:**
  - Unauthenticated users are redirected to a login/registration page
  - Authenticated users can create a new note with a title and Markdown body
  - The note editor supports Markdown input and displays a rendered preview or live Markdown view
  - Authenticated users can view a list of all their notes
  - Authenticated users can search notes by text, with results updated as the search query changes
  - Authenticated users can filter the note list by one or more tags (AND semantics)
  - Authenticated users can edit and delete notes they own
  - Forms display validation feedback for invalid input
  - The interface distinguishes loading, empty, success, and service-error states
  - Expired sessions are detected and the user is redirected to login
  - Access tokens are stored securely (HttpOnly cookies preferred) and never exposed to JavaScript code or logs

### FR-13: Link Suggestion Review Interface
- **Description:** The system must provide a frontend component for users to review pending suggestions and accept or reject them.
- **Acceptance Criteria:**
  - A user can navigate to a "Suggestions" page or modal displaying pending link suggestions
  - Each suggestion displays the source note title, candidate note title, and similarity explanation
  - A user can accept a suggestion, which updates the UI and reflects the newly accepted link in subsequent graph data
  - A user can reject a suggestion, which removes it from the pending list
  - Accepting/rejecting does not require a full page reload
  - The interface handles stale suggestions (already rejected or accepted), duplicate actions, and service failures with clear feedback
  - Sensitive data from other users is never displayed

### FR-14: Knowledge Graph Visualization
- **Description:** The system must render an interactive 2D force-directed graph of notes and accepted relationships using react-force-graph-2d.
- **Acceptance Criteria:**
  - The graph displays notes as nodes and accepted relationships as edges
  - Node labels display note titles; nodes are sized or colored based on available metadata
  - Selecting a node opens the corresponding note in the main notes interface (without leaving the graph view)
  - Selecting a tag filter updates the visible graph according to the backend graph API, showing only notes with all selected tags
  - Edges are displayed only when both endpoint nodes are visible
  - Empty graphs, loading states, API failures, and invalid graph data are handled without crashing
  - Keyboard navigation and focus management enable usable interaction for accessibility (or an equivalent accessible note-list alternative)
  - Graph rendering completes within 2 seconds for up to 500 visible nodes on standard reference hardware

### FR-15: End-to-End Integration and Quality Verification
- **Description:** The system must include automated tests, health checks, and operational documentation to validate the complete MVP.
- **Acceptance Criteria:**
  - Unit and integration tests cover critical domain rules: authorization, note ownership, tag normalization, link deduplication, event handling, and suggestion idempotency
  - An end-to-end test exercises the main user journey: register, login, create notes, receive suggestions, accept a link, and view the graph
  - All services expose `/health` and `/ready` endpoints that distinguish application availability from dependency readiness
  - Logs are structured (JSON format preferred) and contain event IDs, request correlation IDs, and meaningful context without including passwords, tokens, or unnecessary note bodies
  - Documented deployment procedure covers: environment variable configuration, database migration execution, startup verification, and recovery expectations
  - A README describes how to build, run, test, and deploy the application

---

## Non-Functional Requirements

### NFR-1: Performance Targets
- **Description:** The system must meet provisional performance targets validated through representative load testing.
- **Acceptance Criteria:**
  - Full-text search: p95 response time below 500 ms for a dataset of 10,000 notes per user under agreed test load
  - Graph API: p95 response time below 1 second for a graph containing up to 500 visible nodes
  - Graph rendering: Initial rendering within 2 seconds for up to 500 nodes in a web browser on standard reference hardware
  - Background link analysis must not block note creation or updates
  - These targets are provisional and must be validated with representative test data before claiming performance compliance

### NFR-2: Scalability
- **Description:** The system must be designed to support up to 10,000 notes per user without architectural changes.
- **Acceptance Criteria:**
  - Database schema and queries are optimized for efficient full-text search and graph traversal at this scale
  - Backend services are stateless and can be horizontally scaled behind a load balancer
  - Redis Streams support high-throughput event publishing and asynchronous processing
  - The graph API caps visible results at 500 nodes and communicates when limits are reached
  - Design assumptions and potential bottlenecks are documented

### NFR-3: Security and Authentication
- **Description:** The system must implement industry-standard cryptographic practices for credentials, tokens, and session management.
- **Acceptance Criteria:**
  - Passwords are hashed using bcrypt or equivalent, with a configurable work factor (proposed: 12 rounds)
  - Access tokens are JWTs with a short lifespan (proposed: 15 minutes)
  - Refresh tokens are securely stored and support rotation; issued tokens must invalidate previous refresh tokens
  - All tokens include a subject claim and can be revoked
  - Token storage in the browser uses HttpOnly cookies to prevent XSS exfiltration
  - HTTPS is required for all production communication (enforced via reverse proxy configuration)
  - Password reset, account recovery, and token revocation procedures are defined before implementation

### NFR-4: Data Isolation and Privacy
- **Description:** The system must enforce strict multi-tenant isolation such that each user can access only their own data.
- **Acceptance Criteria:**
  - All queries, API responses, and background processing scope data to the authenticated user
  - No endpoint, service, or background job exposes another user's notes, tags, links, or suggestions
  - Authorization checks are enforced server-side, never assumed from client-side information
  - Deletion of a user account cascades deletion of all associated notes, tags, links, and suggestions
  - Data minimization principles are followed: unnecessary user data is not collected or retained

### NFR-5: Logging and Observability
- **Description:** The system must emit structured logs that enable troubleshooting without exposing sensitive data.
- **Acceptance Criteria:**
  - All services emit structured JSON logs at INFO, WARNING, and ERROR levels in normal operation
  - DEBUG logs are available in development environments but disabled or restricted in production
  - INFO logs include request completion metadata, event-processing outcomes, and important lifecycle transitions
  - WARNING logs capture recoverable failures, retry attempts, and degraded behavior
  - ERROR logs capture unrecoverable failures requiring investigation
  - Logs include request/event correlation IDs for tracing across service boundaries
  - Logs never include plaintext passwords, access tokens, refresh tokens, credentials, or unnecessary note bodies
  - Error responses return a correlation ID to the client for debugging

### NFR-6: Deployment and Operations
- **Description:** The system must be deployable on a single machine using Docker Compose with clear operational guidance.
- **Acceptance Criteria:**
  - Docker Compose configuration defines all services, networks, and dependencies
  - Traefik reverse proxy is configured to route requests to services and manage TLS termination
  - PostgreSQL and Redis run in containers with persistent volumes
  - All configuration is externalized as environment variables; no hardcoded secrets
  - A `.env.example` file documents all required environment variables with example values
  - A documented startup procedure covers: environment setup, database initialization, and verification
  - Health/readiness checks enable automated startup verification
  - A documented backup and recovery procedure is provided
  - Kubernetes and distributed orchestration are out of scope for the MVP

### NFR-7: Testability and Code Quality
- **Description:** The system must be designed for automated testing at unit, integration, and end-to-end levels.
- **Acceptance Criteria:**
  - Unit tests cover business logic in isolation with mocked dependencies
  - Integration tests use real PostgreSQL and Redis instances (test containers recommended)
  - End-to-end tests exercise the complete user journey through the API and UI
  - Test suites are automated in CI and prevent deployment of failing code
  - Code adheres to documented style guidelines; linting and type checking are enforced in CI
  - Test coverage for critical paths is documented; target minimum coverage is 70%

### NFR-8: Maintainability and Documentation
- **Description:** The system must be documented clearly enough for new contributors and operators to understand and extend it.
- **Acceptance Criteria:**
  - A README describes the project, technology stack, and quick-start instructions
  - Architecture documentation explains service boundaries, communication patterns, and key design decisions
  - API documentation (OpenAPI/Swagger or equivalent) covers all public endpoints
  - Database schema documentation explains entity relationships and constraints
  - Deployment documentation covers environment setup, CI/CD configuration, and operational procedures
  - Code follows consistent naming conventions and is reasonably self-documenting
  - Key dependencies, known limitations, and future enhancement areas are documented

### NFR-9: Accessibility
- **Description:** The frontend must be usable by people with disabilities.
- **Acceptance Criteria:**
  - Interactive components have keyboard navigation alternatives
  - Form fields have associated labels and error messages
  - Color is not the only means of conveying information (e.g., links, form validation)
  - Images and interactive elements have appropriate alt text or ARIA labels
  - The interface is tested with at least one screen reader (e.g., NVDA, JAWS)
  - The knowledge graph view includes an equivalent note-list alternative for users who cannot use mouse interaction

---

## Assumptions

1. **Authentication Storage:** Refresh tokens are securely stored in the auth-service database (not in Redis) and support revocation. Session revocation is synchronous; no token-caching layer is assumed.

2. **Event Ordering:** Redis Streams provide ordered, reliable event delivery within a single service. Cross-service transactions are not implemented; event-driven eventual consistency is acceptable.

3. **Graph Filtering:** When tag filters are applied, a note is visible if it contains ALL selected tags (AND logic). Edges are displayed only when both endpoint nodes are visible after filtering.

4. **Note Deletion:** Deleting a note cascades deletion of associated tags, accepted links, and pending suggestions. This deletion is transactional if all records are in a single database; cross-service deletions use a retryable cleanup process.

5. **Suggestion Rejection:** Rejecting a suggestion suppresses that relationship until either endpoint note is modified. After a note changes, pending suggestions are re-evaluated, allowing previously rejected relationships to be reconsidered.

6. **Token Security:** Access and refresh tokens are cryptographically signed JWTs. The signing key is stored securely in environment variables or a secrets manager (not in source control).

7. **User Scalability:** The system is designed for small-to-medium user bases (pilot/beta release). No explicit concurrent-user capacity or multi-region deployment is targeted until performance load testing establishes requirements.

8. **Data Backups:** PostgreSQL data is persisted in a Docker volume or external storage. Backup procedures are manual or external to the application; no built-in backup service is included in the MVP.

---

## Out of Scope

1. **Offline Support:** Local editing, offline synchronization, and conflict resolution are not included.

2. **Multi-User Collaboration:** Shared note editing, comment threads, and collaborative graph building are not supported in the MVP.

3. **Advanced Authentication:** Single sign-on (SSO), social login, and multi-factor authentication are deferred.

4. **Bulk Operations:** Batch tagging, bulk note import, and bulk export are not included.

5. **Advanced Search:** Semantic search, embeddings, vector databases, and full-text fuzzy matching are out of scope.

6. **Graph Export:** Exporting the knowledge graph to JSON, image formats, or other external systems is deferred.

7. **3D Graph Visualization:** The 3D variant of react-force-graph is out of scope; the MVP uses 2D only.

8. **Public Subgraph Sharing:** Sharing portions of the knowledge graph publicly, with access control, is not included.

9. **Advanced Analytics:** Usage metrics, suggestion quality analytics, and performance dashboards are deferred.

10. **Kubernetes Deployment:** Distributed orchestration and multi-cluster deployment are out of scope.

11. **Recycle Bin / Soft Deletion:** Permanent deletion only; no recovery of deleted notes.

---

## Open Questions

1. **Password Reset and Account Recovery:** The exact procedures for password reset and account recovery are not yet defined. These should be specified before implementation begins.

2. **Token Revocation Latency:** How quickly must revoked tokens be invalidated across services? Real-time invalidation requires coordinated state; delayed invalidation (up to token expiry) is simpler but less secure.

3. **Suggestion Refresh Triggers:** Should pending suggestions be automatically refreshed at a scheduled interval, or only when a source or target note changes? (Proposed: refresh only on note changes.)

4. **Performance Test Environment:** The reference hardware and load-test assumptions for validating performance targets must be agreed before performance gates are enforced.

5. **Legal and Compliance:** GDPR, data retention, and jurisdiction-specific requirements have not been established. These should be determined based on intended launch geographies.

---

## Requirements Validation Summary

| Category                    | Coverage                                                                      |
| --------------------------- | ----------------------------------------------------------------------------- |
| Core Functionality          | Complete: CRUD, authentication, notes, tags, search, suggestions, graph      |
| Non-Functional Attributes   | Defined: performance, scalability, security, privacy, logging, deployment   |
| Integration & Quality       | Specified: testing, observability, end-to-end scenarios                     |
| Scope Boundaries            | Clear: explicit inclusions, exclusions, and deferred features                |
| Assumptions & Decisions     | Documented: proposed defaults, decision rationale, and unresolved questions  |

**Total Requirements:** 15 Functional + 9 Non-Functional = 24 documented requirements across 14 user stories.
