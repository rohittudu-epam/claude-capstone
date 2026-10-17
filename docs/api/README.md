# HTTP API

Everything is served under one origin through Traefik. Requests and responses are JSON.

| Prefix | Service | OpenAPI document |
|---|---|---|
| `/api/auth` | auth-service | [auth-service.json](auth-service.json) |
| `/api/notes`, `/api/tags` | note-service | [note-service.json](note-service.json) |
| `/api/suggestions`, `/api/links` | link-service | [link-service.json](link-service.json) |
| `/api/graph` | graph-service | [graph-service.json](graph-service.json) |

The OpenAPI files are generated from the code. Regenerate them after changing a route or schema:

```bash
python scripts/export-openapi.py
```

Open one in any OpenAPI viewer (for example paste it into <https://editor.swagger.io>). The `/health` and `/ready` endpoints in the documents are internal and not routed through the proxy. A table of endpoints with behaviour notes is in [implementation-notes.md](../implementation-notes.md#api-phases-2-3); `GET /api/auth/me` returns the signed-in user.

## Authentication

`POST /api/auth/login` sets two HttpOnly cookies: `access_token` (15 minutes, all paths) and `refresh_token` (7 days, only sent to `/api/auth`). Tokens are never in response bodies or headers. Browsers need no code for this; a script should keep a cookie jar. Non-browser clients can send `Authorization: Bearer <access token>` instead.

When an access token expires the API answers `401`. Call `POST /api/auth/refresh`; it rotates the refresh token (the old one stops working) and sets new cookies, and you retry the original request. If refresh also returns `401`, the user must sign in again.

## Conventions

| Topic | Behaviour |
|---|---|
| Validation errors | `400` with `{"detail": "Invalid request", "errors": [{"field", "message"}], "correlation_id"}`. The offending input is never echoed back. |
| Other errors | `{"detail": "...", "correlation_id": "..."}`; the same id is in the `X-Correlation-ID` response header. Send your own `X-Correlation-ID` to trace a request. |
| Someone else's resource | `404`, the same as a missing one |
| Lists | `limit` and `offset`; responses include the total |
| Tag filters | `tags=a,b` means notes having **all** the tags |
| Rate limit | `login`, `register` and `refresh`: 30 per minute per IP, burst 10, then `429` |
| Note size | Body at most 512 KiB (`NOTE_MAX_BODY_BYTES`) |
| Passwords | 8 to 128 characters and at most 72 bytes (a bcrypt limit) |

## Note events (internal)

Not an HTTP API, but part of the contract between services: the `note_events` Redis stream carries `event_id`, `schema_version` (1), `event_type` (`created`, `updated`, `deleted`), `note_id`, `owner_id`, `occurred_at` and an optional `correlation_id`. Events never contain note text.
