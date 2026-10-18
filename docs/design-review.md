# Design Review Document: LinkNote MVP

## Review Summary

**Overall Assessment: ✓ APPROVED WITH CHANGES**

The architecture presents a well-structured microservices design that addresses all functional requirements, provides clear component boundaries, and implements appropriate security controls. The design is pragmatic for an MVP, emphasizing simplicity and Docker-based deployment. 

**Review outcome:** 5 findings identified and addressed (0 Critical, 2 High accepted with remediations, 2 Medium accepted, 1 Informational for guidance). All Critical and High findings have been incorporated into remediated `docs/architecture.md`.

---

## Review Findings

### Finding DR-1: Event Publishing Failure – Silent Data Loss Risk

- **Severity:** High
- **Category:** Error Handling & Data Consistency
- **Description:** If Redis becomes unavailable or Redis Streams publication fails after a note is persisted to PostgreSQL, the event is never published. Link Service has no way to know the note exists, so link suggestions are never generated. The system doesn't lose the note but silently loses the link-discovery opportunity. This violates FR-8 acceptance criteria: "A Redis outage or publication failure is observable and does not silently lose an event."
- **Recommendation:** Implement one of:
  1. **Transactional Outbox Pattern:** Store the event durably in PostgreSQL as part of the same transaction that persists the note. A separate outbox reader publishes events to Redis asynchronously. Guarantees no event is lost.
  2. **Synchronous Publication with Retry:** Make event publication synchronous and critical; fail note creation if Redis is unavailable. User receives error; note is not persisted.
  3. **Async Verification:** Periodically scan notes for "missing" link analysis and reprocess them (simpler but less performant).
- **Decision:** ACCEPTED — **Implement Transactional Outbox Pattern in Note Service.** Add an `outbox` table to PostgreSQL (`note_id`, `event_type`, `payload`, `created_at`, `published_at`). On note creation/update, insert the event into `outbox` in the same transaction. A background task (e.g., Link Service or separate worker) reads unpublished outbox entries, publishes to Redis, and marks them as published. This guarantees durability and observability. Update docs/architecture.md to document outbox pattern.

---

### Finding DR-2: Refresh Token Revocation – Eventual Consistency Gap

- **Severity:** High
- **Category:** Security & Authorization
- **Description:** When a user logs out or revokes a session, the refresh token is marked revoked in Auth Service. However, other services validate only the access token (via JWT signature verification), not querying Auth Service for revocation status. A stolen refresh token could be used indefinitely (beyond the short-lived access token) if an attacker doesn't need an access token refresh. Requirements FR-3 and FR-4 specify revocation, but the architecture does not fully enforce it.
- **Recommendation:** 
  1. Add an optional `/api/auth/verify?token=<token>` endpoint that checks token revocation status (return 401 if revoked).
  2. Require backend services to call this endpoint for security-sensitive operations (e.g., account deletion, password change).
  3. Or: implement distributed token revocation via a cache (Redis) that Auth Service updates on logout, and other services check (eventual consistency, acceptable for MVP).
- **Decision:** ACCEPTED — **Implement token revocation via Auth Service endpoint.** Auth Service maintains a revocation list (SQL table or Redis cache). On logout, token is added to revocation list. Other services optionally validate tokens against `/api/auth/verify` for sensitive operations. Update docs/architecture.md to clarify token lifecycle and revocation.

---

### Finding DR-3: Multi-Service Data Consistency – Cascading Deletes

- **Severity:** Medium
- **Category:** Data Consistency & Resilience
- **Description:** When a note is deleted, Note Service must cascade delete associated tags, accepted links, and pending suggestions. These records exist in the same PostgreSQL database, so a transactional delete is possible. However, if a cascade fails partway through (e.g., constraint violation), the note may be partially deleted, leaving orphaned records. Additionally, the Link Service may still have stale suggestion records if the note was deleted before suggestions were processed.
- **Recommendation:** 
  1. Use database constraints and transactional integrity (foreign keys with ON DELETE CASCADE).
  2. Add integration tests verifying cascade behavior under various failure scenarios.
  3. Consider adding a cleanup verification step during deployment.
- **Decision:** ACCEPTED — Rely on PostgreSQL transactional integrity with explicit ON DELETE CASCADE constraints. Add integration tests for cascade scenarios. Update docs/architecture.md to document cascade behavior and testing approach.

---

### Finding DR-4: Graph Capping and User Experience – Missing Feedback

- **Severity:** Medium
- **Category:** Operability & User Experience
- **Description:** FR-14 and architecture specify a 500-node cap on visible graph size. The architecture says "communicate when the result is capped," but does not specify the exact mechanism or error response format. Frontend may not know how to signal to the user that results are filtered.
- **Recommendation:** Define a precise response structure when graph is capped, e.g.:
  ```json
  {
    "nodes": [...up to 500 nodes...],
    "edges": [...],
    "is_capped": true,
    "total_nodes": 1547,
    "message": "Graph limited to 500 visible nodes. Consider adding more tag filters to narrow results."
  }
  ```
  Document in Graph API contract.
- **Decision:** ACCEPTED — Add explicit `is_capped` and `total_nodes` fields to graph API response. Update docs/architecture.md API contract section. Implement in Graph Service during implementation.

---

### Finding DR-5: Backward Compatibility and Event Schema Evolution

- **Severity:** Informational
- **Category:** Maintainability & Scalability
- **Description:** As the system evolves, event schemas published to Redis Streams may change (e.g., new fields, renamed fields). Link Service consumers must handle multiple schema versions gracefully. The architecture specifies "versioned event contract," but does not define the versioning mechanism.
- **Recommendation:** Adopt semantic versioning for event schemas. Include a `schema_version` field in event payloads. Link Service consumers implement version-specific handlers or schema migration logic. Document the event versioning policy.
- **Decision:** ACCEPTED — Document event schema versioning in docs/architecture.md. Recommend including `schema_version: 1` in initial event payloads for future extensibility. Not required for MVP but good practice.

---

## Requirements Coverage Assessment

| Requirement | Covered? | Component | Notes |
|------------|----------|-----------|-------|
| FR-1: Dev Environment | ✓ Yes | Docker Compose, CI/CD | Compose config and CI pipeline defined. |
| FR-2: Database Persistence | ✓ Yes | PostgreSQL, Alembic | Schema and migrations defined. |
| FR-3: Registration & Auth | ✓ Yes | Auth Service | JWT, bcrypt, email uniqueness. |
| FR-4: Session Authorization | ✓ Yes | Auth Service + all services | Token validation; ownership checks on data access. |
| FR-5: Note CRUD | ✓ Yes | Note Service, PostgreSQL | CRUD endpoints and ownership scoping. |
| FR-6: Tagging | ✓ Yes | Note Service, PostgreSQL | Tag creation, normalization, association. |
| FR-7: Full-Text Search | ✓ Yes | Note Service, PostgreSQL | Full-text indexes and search queries. |
| FR-8: Event Publishing | ✓ Yes (with remediation) | Note Service, Redis Streams | Outbox pattern remediation ensures durability. |
| FR-9: Link Suggestions | ✓ Yes | Link Service, Redis Streams, PostgreSQL | Event consumption, suggestion generation, deduplication. |
| FR-10: Accept/Reject Links | ✓ Yes | Link Service, PostgreSQL | API endpoints and link creation. |
| FR-11: Graph API | ✓ Yes | Graph Service, PostgreSQL | Filtered graph retrieval with tag support. |
| FR-12: Notes UI | ✓ Yes | Frontend (Next.js) | Note editor, list, search interface. |
| FR-13: Suggestion Review UI | ✓ Yes | Frontend (Next.js) | Suggestion review component. |
| FR-14: Graph Visualization | ✓ Yes | Frontend + Graph Service | 2D graph rendering with capping. |
| FR-15: E2E Verification | ✓ Yes | CI/CD, Health endpoints | E2E tests and service health checks. |

**NFR Coverage:**
| NFR | Covered? | Notes |
|-----|----------|-------|
| NFR-1: Performance | ✓ Yes | Targets specified; monitoring via logging. |
| NFR-2: Scalability | ✓ Yes | Stateless services; database is shared bottleneck (acknowledged in risks). |
| NFR-3: Security | ✓ Yes (with remediation) | Auth, encryption, token management. Revocation pattern clarified. |
| NFR-4: Data Isolation | ✓ Yes | Application-level multi-tenancy with ownership checks. |
| NFR-5: Logging | ✓ Yes | Structured JSON logs; no sensitive data. |
| NFR-6: Deployment | ✓ Yes | Docker Compose on single machine. |
| NFR-7: Testability | ✓ Yes | Unit, integration, E2E test strategy. |
| NFR-8: Maintainability | ✓ Yes | Documentation, clear boundaries, consistent tech stack. |
| NFR-9: Accessibility | ✓ Yes | Keyboard nav, screen reader support, accessible note-list alternative to graph. |

**All requirements are covered.** ✓

---

## Agreed Design Decisions

- **DD-1: Transactional Outbox Pattern for Event Durability** — Note Service stores note change events in a durable outbox table (PostgreSQL) as part of the same transaction that persists the note. A separate publisher reads unpublished outbox entries and publishes to Redis Streams. This guarantees no event loss and satisfies FR-8 acceptance criteria.

- **DD-2: Token Revocation via Auth Service Verification** — Auth Service maintains a revocation list (SQL or cache-based). Other services can call Auth Service `/verify` endpoint to check revocation status for sensitive operations. This provides eventual-consistency revocation without requiring distributed state.

- **DD-3: ON DELETE CASCADE for Referential Integrity** — PostgreSQL foreign key constraints use ON DELETE CASCADE to automatically delete dependent records (e.g., tags, links, suggestions when a note is deleted). Transactional integrity ensures all-or-nothing cascade.

- **DD-4: Explicit Graph Capping Response** — Graph API returns `is_capped`, `total_nodes`, and a user-friendly message when results exceed 500 nodes. Frontend uses this to signal truncation to user.

- **DD-5: Semantic Event Versioning** — Events include a `schema_version` field (initial value: 1) to support future schema evolution without breaking existing consumers. Link Service consumers handle versioned events gracefully.

- **DD-6: Application-Level Multi-Tenancy** — All services enforce user ownership via server-side authorization checks; no database row-level security (RLS) is used. This is simpler to reason about and sufficient for MVP.

- **DD-7: Shared PostgreSQL Database with Service-Specific Schemas** — One PostgreSQL instance shared by all services, partitioned into logical schemas (`auth`, `notes`, `links`). Simpler than separate databases; each service owns its schema's write operations.

- **DD-8: Redis Streams Consumer Groups for At-Least-Once Processing** — Link Service uses Redis consumer groups to ensure at-least-once delivery of events. Idempotent processing prevents duplicate suggestions.

- **DD-9: Traefik for Single-Machine Deployment** — Traefik reverse proxy provides service discovery, routing, and TLS termination for local Docker Compose deployment. No Kubernetes required; horizontally scalable later.

- **DD-10: stateless Backend Services** — All FastAPI services are stateless (no in-memory session caches). This enables horizontal scaling and simplifies deployment.

---

## Risks Accepted

1. **Single Points of Failure (Redis, PostgreSQL):** Both services run in single containers; no replication or HA. Mitigation: External persistent volumes, backups, documented recovery. Future: replicas if needed.

2. **Performance Bottleneck at Shared Database:** As note count grows, PostgreSQL becomes the primary bottleneck. Mitigation: Query optimization, indexing, monitoring. Future: read replicas, sharding if scale demands it.

3. **Eventual Consistency in Token Revocation:** Revocation checks are eventual-consistent (polling `/verify` endpoint). A revoked token may be accepted briefly by a service. Mitigation: short token lifetime (15 min) limits exposure.

4. **Cascade Delete Atomicity Across Services:** If a cascade delete is interrupted mid-operation, partial deletion may occur. Mitigation: transactional database constraints, integration tests, monitoring for orphaned records.

5. **Outbox Publisher Failure:** If the outbox publisher crashes after publishing to Redis but before marking published_at, duplicate events may be published. Mitigation: idempotent consumers (Link Service), deduplication at consumer side.

---

## Action Items

- [ ] **Outbox Pattern Implementation:** During implementation phase, add `outbox` table to PostgreSQL and implement outbox publisher in Note Service.
- [ ] **Token Revocation Endpoint:** Implement Auth Service `/api/auth/verify?token=<token>` endpoint returning revocation status.
- [ ] **Graph API Response Contract:** Document precise response format when graph is capped; implement in Graph Service.
- [ ] **Event Schema Documentation:** Document initial event schema with `schema_version` field; publish to team.
- [ ] **Cascade Delete Integration Tests:** Write tests covering note deletion with cascading tags, links, and suggestions.
- [ ] **Database Indexing Plan:** Review full-text search index design; plan monitoring and optimization.
- [ ] **Outbox Publisher Deployment:** Plan deployment of outbox publisher (within Note Service or separate worker); document restart/failure recovery.

---

## Recommendations for Future Phases

1. **Phase 2 (Post-MVP):** Implement read replicas for PostgreSQL to improve search performance and enable geo-distributed reads.
2. **Phase 2:** Add Redis replication/Sentinel for HA event stream.
3. **Phase 2:** Implement API versioning and deprecation policy as services evolve.
4. **Phase 3:** Consider semantic embeddings for link suggestion quality improvement.
5. **Phase 3:** Add audit logging and compliance features (GDPR, data retention).
6. **Phase 4:** Implement distributed tracing (OpenTelemetry) for observability across services.

---

## Review Conclusion

The architecture is **well-designed for the LinkNote MVP scope**. It provides clear component boundaries, security-conscious defaults, and pragmatic technology choices. The two High-severity findings (event durability, token revocation) have been addressed with appropriate design patterns. All functional and non-functional requirements are covered. 

**Approval Status: ✓ APPROVED** with remediations incorporated into updated `docs/architecture.md`.

The design is ready to proceed to the implementation planning phase.

---
