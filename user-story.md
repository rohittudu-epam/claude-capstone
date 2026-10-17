# LinkNote MVP User Stories

**Source:** Atlassian Wiki - LinkNote MVP Scope Summary

## Section 1 — MVP Scope Summary

LinkNote is a privacy-friendly personal knowledge management application that helps users create Markdown notes and discover meaningful relationships between them through automatically generated, user-approved link suggestions. The MVP will cover the complete workflow: local development and deployment setup, authentication, note and tag management, full-text search, asynchronous link discovery, bidirectional links, and interactive knowledge graph visualization.

## Section 2 — User Stories (14 Total)

### US-01: Establish a Reproducible Development and Deployment Foundation

**As a** developer, **I want** a reproducible local environment for LinkNote, **So that** all services can be developed, tested, and run consistently.

**Description:** Create the repository foundation and containerized development environment for the frontend, backend services, PostgreSQL, Redis, and reverse proxy.

**Acceptance Criteria:**
- Docker Compose starts the configured MVP services and their required infrastructure dependencies
- A clean checkout can install dependencies, apply the documented setup process, and start the application
- Configuration is read from environment variables; `.env.example` documents required settings
- CI executes the configured backend and frontend linting, type checks, and baseline automated tests
- Service startup failures produce actionable diagnostics

**Priority:** High | **Estimated Effort:** 4 days

---

### US-02: Establish Domain Persistence and Database Migrations

**As a** LinkNote service, **I want** persistent, consistently migrated domain data, **So that** notes, users, tags, and links remain reliable across restarts and deployments.

**Description:** Implement SQLAlchemy 2.0 models and Alembic migrations for the core domain using PostgreSQL.

**Acceptance Criteria:**
- Database migrations create required user, note, tag, note-tag association, accepted-link, and suggestion structures
- Primary keys, foreign keys, uniqueness constraints, and timestamps enforce documented data-integrity rules
- Accepted links cannot be duplicated for the same logical pair
- A fresh database can be initialized from migrations; existing databases can be upgraded through the migration chain
- Automated integration tests verify persistence, constraint enforcement, and migration behavior

**Priority:** High | **Estimated Effort:** 3 days | **Dependencies:** US-01

---

### US-03: Register, Authenticate, and Maintain User Sessions

**As a** personal knowledge base user, **I want** to register and sign in securely, **So that** my notes and knowledge graph are accessible only to me.

**Description:** Implement registration, login, access-token issuance, and refresh-token handling in `auth-service`.

**Acceptance Criteria:**
- A user can register with a valid email address and password; duplicate email registration is rejected
- Valid credentials produce documented JWT-based authentication response; invalid credentials produce a generic error
- Expired or invalid access tokens are rejected; refresh tokens follow configured rotation, expiry, and revocation policy
- Passwords are stored using appropriate password-hashing algorithm, never as plaintext
- Protected service endpoints reject unauthenticated requests and cannot expose another user's resources

**Priority:** High | **Estimated Effort:** 4 days | **Dependencies:** US-01, US-02

---

### US-04: Create, Read, Update, and Delete Markdown Notes

**As an** authenticated user, **I want** to create and manage Markdown notes, **So that** I can capture and maintain my personal knowledge.

**Description:** Implement core note-management workflow in `note-service` with title, Markdown body, owner, timestamps, and stable identifier.

**Acceptance Criteria:**
- An authenticated user can create a note with valid title and Markdown body and retrieve the persisted note
- The owner can update the note; its update timestamp changes when content changes
- The owner can delete a note; subsequent retrieval does not return it
- Invalid payloads and attempts to access/modify another user's notes return documented errors
- Successful note creation, updates, and deletion produce domain events for downstream link processing

**Priority:** High | **Estimated Effort:** 4 days | **Dependencies:** US-01, US-02, US-03

---

### US-05: Organize Notes with Tags

**As an** authenticated user, **I want** to assign tags to my notes, **So that** I can categorize and filter my knowledge.

**Description:** Extend note-management workflow with tag creation/reuse and note-tag associations scoped to the owning user.

**Acceptance Criteria:**
- A user can assign one or more tags when creating or updating a note
- Reusing an existing normalized tag for the same user does not create a duplicate tag
- A user can retrieve tags associated with a note and filter notes by selected tags
- A user cannot associate another user's tags or retrieve another user's categorized notes
- Removing a tag association updates the persisted relationship without deleting the note

**Priority:** High | **Estimated Effort:** 2 days | **Dependencies:** US-02, US-03, US-04

---

### US-06: Search Notes by Text and Metadata

**As an** authenticated user, **I want** to search my notes by their content, titles, and tags, **So that** I can quickly find relevant knowledge.

**Description:** Provide full-text search for notes using PostgreSQL capabilities.

**Acceptance Criteria:**
- A user can search for text contained in note titles or bodies and receive matching notes
- Search results are restricted to the authenticated user's notes and respect selected tag filters
- Empty queries and malformed search parameters are handled according to documented API contract
- Search results contain sufficient metadata to identify a note without exposing its full body
- Automated integration tests verify matching behavior, tag filtering, and cross-user isolation

**Priority:** High | **Estimated Effort:** 3 days | **Dependencies:** US-02, US-03, US-04, US-05

---

### US-07: Publish Note Change Events Reliably

**As a** background link-analysis service, **I want** to receive note creation and update events, **So that** link suggestions can be generated without delaying the user's note workflow.

**Description:** Connect note mutations to asynchronous processing through Redis Streams.

**Acceptance Criteria:**
- A successful note creation or update produces an event containing note ID, owner ID, event type, and relevant version/timestamp
- Events are published only for successfully persisted changes
- A Redis outage or publication failure is observable and does not silently lose an event
- The consumer can retry failed processing and safely handle duplicate event delivery
- Integration tests verify event payloads, failure handling, and duplicate-event behavior

**Priority:** High | **Estimated Effort:** 3 days | **Dependencies:** US-01, US-02, US-04

---

### US-08: Generate Automatic Link Suggestions

**As an** authenticated user, **I want** LinkNote to suggest related notes automatically, **So that** I can discover connections I might otherwise miss.

**Description:** Implement background analysis in `link-service` using note titles, normalized keywords, and simple similarity score.

**Acceptance Criteria:**
- A successfully processed note generates candidate suggestions from eligible notes belonging to the same user
- The analyzer compares note titles and relevant text using documented, deterministic keyword-based scoring method
- The service excludes the source note, already accepted links, deleted notes, and candidates violating ownership rules
- Suggestions include enough metadata and a score/explanation to help users evaluate the proposed relationship
- Failed analysis can be retried; repeated processing does not create duplicate pending suggestions

**Priority:** High | **Estimated Effort:** 4 days | **Dependencies:** US-02, US-03, US-07

---

### US-09: Accept or Reject Link Suggestions

**As an** authenticated user, **I want** to accept or reject suggested relationships between my notes, **So that** the knowledge graph reflects my judgment rather than automatic assumptions.

**Description:** Expose suggestion review actions through `link-service`.

**Acceptance Criteria:**
- A user can retrieve pending suggestions for their notes and accept or reject an individual suggestion
- Accepting a valid suggestion creates one canonical accepted link and makes the relationship visible from both notes
- Repeated acceptance requests do not create duplicate relationships; stale suggestions are rejected per documented policy
- Rejecting a suggestion does not create an accepted link and removes it from the pending list
- All actions enforce ownership of the source and target notes and return documented responses for invalid operations

**Priority:** High | **Estimated Effort:** 3 days | **Dependencies:** US-02, US-03, US-08

---

### US-10: Provide a Consistent Knowledge Graph API

**As a** frontend client, **I want** a graph API that returns authorized notes and accepted relationships, **So that** the interface can visualize the user's knowledge without coordinating database access across services.

**Description:** Implement `graph-service` as a read-oriented aggregation layer for graph visualization.

**Acceptance Criteria:**
- An authenticated request returns graph nodes and accepted edges belonging to the current user
- Each edge references valid nodes included in the response; each accepted relationship is represented consistently
- Tag filters restrict the graph according to documented rule
- Missing dependencies, invalid filters, and unauthorized requests produce documented errors without leaking data
- Automated integration tests validate graph integrity, tag filtering, and ownership isolation

**Priority:** High | **Estimated Effort:** 3 days | **Dependencies:** US-03, US-04, US-05, US-09

---

### US-11: Build the Core Notes and Search Interface

**As an** authenticated user, **I want** a clear interface for creating, editing, browsing, and searching notes, **So that** I can manage my knowledge without interacting directly with service APIs.

**Description:** Implement primary Next.js App Router experience for registration/sign-in, note lists, Markdown editor, tag controls, and full-text search.

**Acceptance Criteria:**
- An authenticated user can create, view, edit, and delete notes through the interface
- The editor supports Markdown input and displays a usable preview or rendered representation
- Search and tag filters update the visible note list according to backend results
- Forms display validation feedback; loading, empty, and service-error states are distinguishable
- Protected screens and note data are not exposed to unauthenticated users; interface handles expired sessions

**Priority:** High | **Estimated Effort:** 4 days | **Dependencies:** US-03, US-04, US-05, US-06

---

### US-12: Review Link Suggestions in the User Interface

**As an** authenticated user, **I want** to review suggested links and accept or reject them from the interface, **So that** I can control which relationships become part of my knowledge graph.

**Description:** Create a suggestion-review experience that presents related note titles and available similarity explanations.

**Acceptance Criteria:**
- A user can view pending link suggestions and navigate to relevant notes
- Each suggestion displays enough context to distinguish the candidate relationship
- Accepting a suggestion updates the interface and reflects newly accepted relationship in subsequent graph data
- Rejecting a suggestion removes it from the pending list without creating an accepted relationship
- Interface handles stale suggestions, duplicate actions, and service failures with clear feedback

**Priority:** High | **Estimated Effort:** 2 days | **Dependencies:** US-08, US-09, US-11

---

### US-13: Visualize and Filter the Knowledge Graph

**As an** authenticated user, **I want** an interactive graph of my notes and accepted links, **So that** I can explore relationships visually and open relevant notes.

**Description:** Integrate two-dimensional force-directed graph into the frontend using `react-force-graph-2d`.

**Acceptance Criteria:**
- The graph renders notes as nodes and accepted relationships as edges using data from `graph-service`
- Selecting a node opens the corresponding note in the notes interface
- Selecting a tag filter updates the displayed graph according to backend graph-filtering contract
- Empty graphs, loading states, API failures, and invalid graph data are handled without crashing the page
- Graph interactions have usable keyboard-accessible alternatives or equivalent accessible note-list view

**Priority:** High | **Estimated Effort:** 4 days | **Dependencies:** US-05, US-10, US-11

---

### US-14: Verify End-to-End Quality and Operational Readiness

**As a** project maintainer, **I want** automated verification, observable service health, and a repeatable deployment process, **So that** LinkNote can be released and operated with known limitations and recoverable failures.

**Description:** Complete the MVP's critical integration and operational checks with health/readiness endpoints, structured logging, production configuration, and documented deployment verification.

**Acceptance Criteria:**
- Automated unit and integration tests cover critical domain rules, service contracts, authorization, and event-processing failure cases
- End-to-end test exercises main journey: authenticate, create notes, obtain suggestions, accept a link, view graph
- Each deployed service exposes a health/readiness contract distinguishing application availability from required dependency readiness
- Logs contain useful structured event and error context while excluding passwords, tokens, and unnecessary private note content
- Documented deployment procedure covers configuration validation, database migrations, startup verification, and recovery/rollback expectations

**Priority:** High | **Estimated Effort:** 4 days | **Dependencies:** US-01 through US-13

---

## Implementation Sequence

**Phase 1 (Foundation):** US-01 → US-02 → US-03

**Phase 2 (Core Notes):** US-04 → US-05 → US-06 | In parallel: US-07 (after US-04, US-02)

**Phase 3 (Links & UI):** US-08 → US-09 → US-10 | In parallel: US-11, US-12, US-13

**Phase 4 (Verification):** US-14

---
