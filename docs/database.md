# Database

One PostgreSQL 15 database shared by all services. Schema changes are Alembic migrations in `backend/migrations/versions/`, applied by the one-shot `migrate` service on every `docker compose up`. SQLAlchemy models are in `backend/shared/models.py`; a test compares them with the migrated schema, so the two cannot drift silently.

## Tables

| Table | Purpose | Key constraints |
|---|---|---|
| `users` | Accounts | Unique email (the API trims and lower-cases it before storing, so uniqueness is effectively case-insensitive); bcrypt password hash |
| `notes` | Markdown notes | `owner_id` -> `users` (cascade); generated, title-weighted `search_vector` (tsvector) with a GIN index; index on `(owner_id, updated_at)` |
| `tags` | Per-user tag names | Unique `(owner_id, name)`; names are normalised to lower case |
| `note_tags` | Note <-> tag | Primary key `(note_id, tag_id)`; both cascade |
| `suggestions` | Candidate links, one row per unordered pair | `source_note_id < target_note_id` check; unique pair; `status` is `pending` or `rejected`; stores both notes' `updated_at` so stale rows can be detected; both notes cascade |
| `accepted_links` | Links the user accepted | `source_note_id < target_note_id` check; unique pair; both notes cascade |
| `outbox` | Note events waiting to reach Redis | `note_id` is deliberately not a foreign key, so a `deleted` event outlives its note; index on `(published_at, created_at)` |
| `revoked_tokens` | Logged-out or rotated JWT ids | Checked by every service on each request |

Deleting a user removes their notes, tags, suggestions, links and outbox rows. Deleting a note removes its tag assignments, suggestions and links.

## Why pairs are ordered

A link between A and B is stored once with the smaller id first (`canonical_pair` in `shared/links.py`), and the database enforces it. That makes "already linked" and "already suggested" a plain unique-key lookup in either direction.

## Migrations

```bash
docker compose run --rm migrate                       # apply (also runs on every `up`)
docker compose run --rm migrate alembic current       # show the applied revision
docker compose run --rm migrate alembic history       # list revisions
```

| Revision | Adds |
|---|---|
| 001 | Initial schema |
| 002 | Full-text search vector, outbox without a note foreign key, `(note_id, tag_id)` tag key, index clean-up |
| 003 | Suggestion state: status, note versions, rejection time |

Write a new revision in `backend/migrations/versions/` and run the backend tests; the model-versus-migration test fails if they differ. There are no automatic downgrades in deployment; restore from a backup instead (see [deployment.md](deployment.md)).

## Housekeeping that does not happen yet

- `revoked_tokens` rows are never purged after the tokens expire.
- Rejected `suggestions` rows remain until either note changes.
- Processed `outbox` rows are kept (marked with `published_at`).

None of these affect correctness; they grow slowly with use. Tracked in the "Known gaps" of [implementation-notes.md](implementation-notes.md).
