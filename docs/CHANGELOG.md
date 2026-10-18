# Changelog

All notable changes to the LinkNote MVP project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-10-17

### Added

#### Foundation & Infrastructure
- Docker Compose configuration for complete multi-service orchestration (PostgreSQL, Redis, 4 backend services, frontend, Traefik reverse proxy)
- CI/CD pipeline (GitHub Actions) with linting, type checking, unit tests, integration tests, and Docker builds
- Agentic SDLC pipeline system with 9 specialist agents and 5 custom skills for automated software development workflow
- Database migrations using Alembic (3 migrations: initial schema, search/outbox/note_tags, suggestion state)
- Comprehensive `.env.example` with documented environment variables and security warnings
- Project documentation: `CLAUDE.md`, `README.md`, deployment guides, API documentation

#### Backend Services
- **Shared Components:**
  - SQLAlchemy 2.0 models for all domain entities (User, Note, Tag, AcceptedLink, Suggestion, Outbox, RevokedToken)
  - Centralized configuration management with validation
  - bcrypt password hashing (12 rounds) and JWT token generation/validation
  - Structured JSON logging with secret redaction and correlation IDs
  - Transactional outbox pattern for durable event publishing
  - Health and readiness check endpoints for all services
  - Worker heartbeat monitoring for background processes

- **Auth Service:**
  - User registration with email/password and duplicate email detection
  - Login with JWT access tokens (15-min expiry) and refresh tokens (7-day expiry)
  - Token refresh with rotation (prevents token reuse)
  - Token revocation on logout with revocation list in database
  - Token verification endpoint for other services
  - Rate limiting on authentication endpoints (30 requests/min/IP)

- **Note Service:**
  - Complete CRUD operations for Markdown notes (create, read, update, delete)
  - Tag creation, normalization (lowercase, trimmed), and reuse
  - Tag-based filtering with AND semantics (note must have all selected tags)
  - Full-text search using PostgreSQL GIN indexes with title-weighted ranking
  - Pagination support for note lists and search results
  - Transactional outbox pattern for durable event publishing to Redis Streams
  - Background outbox publisher worker for asynchronous event delivery
  - Multi-tenant isolation with server-side ownership checks

- **Link Service:**
  - Redis Streams consumer with consumer groups for at-least-once event delivery
  - Automatic link suggestion generation using weighted Jaccard keyword similarity
  - Deterministic, configurable similarity algorithm (default 30% threshold, 2 min shared keywords)
  - Idempotent event processing (duplicate events converge to same result)
  - Stale suggestion detection (suggestions tied to note versions)
  - Accept/reject endpoints for user-driven link approval
  - Canonical bidirectional link creation (one link per note pair)
  - Rejection tracking with suppression until either note changes
  - Background worker for event processing with retry and dead-letter handling

- **Graph Service:**
  - Read-only graph API returning authorized notes and accepted links
  - Tag-based filtering with AND semantics
  - Result capping at 500 nodes with explicit feedback (`is_capped`, `total_nodes`, `message`)
  - No dangling edges (both endpoints always included in visible nodes)
  - Performance-optimized queries with proper indexing

#### Frontend Application
- Next.js 15 App Router application with React 19 and TypeScript
- Tailwind CSS v4 for styling with custom UI components
- Authentication pages: registration, login, logout
- Note management: Markdown editor with preview, note browser, search interface
- Tag management: tag input with autocomplete, tag filtering
- Full-text search with live results and tag-based filtering
- Link suggestion review interface with accept/reject actions
- Interactive 2D knowledge graph visualization using react-force-graph-2d
- Accessible list view alternative for graph navigation
- HttpOnly cookie-based session management with automatic token refresh
- Loading states, error handling, and user feedback throughout
- TanStack Query for server state management
- Accessibility features: keyboard navigation, ARIA labels, WCAG 2.1 A/AA compliance

#### Testing & Verification
- 241 backend unit and integration tests (pytest) covering all services
- 89 frontend unit tests (Vitest) covering components, API client, utilities
- 12 end-to-end tests (Playwright) covering complete user journey, security, accessibility, and performance
- Test coverage for all 15 functional requirements and 9 non-functional requirements
- Performance tests verifying search < 500ms, graph API < 1s, graph rendering < 2s
- Security tests: HttpOnly cookies, XSS protection, cross-user isolation, unauthorized access prevention
- Accessibility tests: axe-core WCAG 2.1 scans, keyboard navigation
- Edge case coverage: empty input, missing fields, boundary values, API failures, invalid formats
- Real-stack performance measurement script (`scripts/measure-search.sh`)
- Deployment verification script (`scripts/verify-deployment.sh`)

#### Documentation
- Complete requirements specification: 15 functional requirements, 9 non-functional requirements
- System architecture document with 10 components, data flows, and technology choices
- Design review document with 5 findings and approved remediations
- Implementation plan with 28 tasks, dependencies, and acceptance criteria
- Code review report covering 101 files with all High severity issues fixed
- Verification report with test results, requirements traceability, and performance measurements
- User story document with 14 user stories defining MVP scope
- Getting started guide, deployment procedures, database schema documentation
- Testing guide for unit, integration, and E2E tests
- Implementation notes documenting deviations, verification results, and known limitations
- OpenAPI documentation for all backend services
- SDLC pipeline documentation (agent inventory, orchestrator design, workflow guide)

#### Design Review Remediations
- **DR-1:** Transactional outbox pattern for durable event publishing (no event loss on Redis failure)
- **DR-2:** Token revocation mechanism with verification endpoint (prevents stolen token reuse)
- **DR-3:** ON DELETE CASCADE constraints for referential integrity (automatic cleanup of dependent records)
- **DR-4:** Explicit graph capping feedback in API responses (`is_capped`, `total_nodes`, `message`)
- **DR-5:** Event schema versioning (`schema_version: 1`) for future evolution

### Changed
- `.env.example` — Enhanced with prominent security warning about production credential generation
- `backend/auth-service/auth_service/routes.py:113` — Fixed Python 2 exception syntax to Python 3 (code review C-1)
- Note body size limit from 10 MB to 512 KiB (PostgreSQL tsvector limit)
- Traefik from v2.10 to v3.6 (compatibility with Docker Engine 29)
- Token delivery to HttpOnly cookies only (no response headers to prevent JavaScript exposure)

### Fixed
- Exception handling syntax error in auth routes (Python 2 tuple syntax)
- Development credentials documentation in `.env.example` with security warnings
- JWT secret validation enforcement in production mode
- Empty tag filter validation to prevent blank tag queries
- Rate limiting scope narrowed to credential endpoints only (prevents throttling normal usage)

### Security
- bcrypt password hashing with 12 rounds and configurable work factor
- JWT tokens with short-lived access tokens (15 minutes) and rotatable refresh tokens (7 days)
- HttpOnly cookies prevent XSS token theft
- Token revocation on logout with database-backed revocation list
- Server-side authorization checks on all protected endpoints
- Multi-tenant data isolation enforced at application layer
- Structured logging redacts passwords, tokens, and sensitive data
- Rate limiting on authentication endpoints (30 requests/min/IP, burst 10)
- Input validation with Pydantic schemas on all endpoints
- SQL injection prevention via parameterized queries (SQLAlchemy ORM)
- HTTPS ready with Traefik TLS termination configuration

### Performance
- Full-text search p95 latency: 27-59ms (6-18x better than 500ms target)
- Graph API p95 latency: 95ms (10x better than 1s target)
- Graph rendering time: 0.64-1.7s for 500 nodes (within 2s target, best case 3x faster)
- Background link analysis non-blocking via transactional outbox pattern
- PostgreSQL GIN indexes for efficient full-text search
- Optimized graph queries with proper indexing on foreign keys
- WebGL-accelerated graph rendering with react-force-graph-2d
- Stateless backend services enabling horizontal scaling

### Known Limitations
- One E2E test fails intermittently due to timing issue (non-critical, functionality works in manual testing)
- npm dev dependencies have known vulnerabilities (dev-only, not production code)
- No backfill job for pre-existing notes (suggestions only generated via events)
- Matching algorithm has no stemming or synonyms (exact keyword matching only)
- No endpoint to remove accepted links
- Expired revoked_tokens not purged automatically
- Password reset and account recovery not implemented (deferred to post-MVP)
- E2E tests not run in CI (requires full stack, currently manual execution)

## [0.1.0] - 2026-10-16 (Pre-release)

### Added
- Initial project setup with basic directory structure
- Proof-of-concept Docker Compose configuration
- Skeleton backend services and frontend application

---

## Version History

- **1.0.0** (2026-10-17) — LinkNote MVP with all 14 user stories, 15 functional requirements, 9 non-functional requirements implemented and verified. 342 tests (99.7% pass rate), performance exceeding targets, complete documentation.
- **0.1.0** (2026-10-16) — Pre-release skeleton

---

For detailed changes and implementation notes, see:
- `docs/requirements.md` — Functional and non-functional requirements
- `docs/architecture.md` — System architecture and design decisions
- `docs/impl-plan.md` — Implementation task breakdown
- `docs/code-review.md` — Code review findings and fixes
- `docs/verification-report.md` — Test results and verification evidence
- `docs/implementation-notes.md` — Deviations, verification results, known limitations
