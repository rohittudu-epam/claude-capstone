# Deployment, backup and troubleshooting

For a first run on a laptop, see [getting-started.md](getting-started.md). This page is for running LinkNote somewhere other people use it.

## Before you expose it

| Check | Why |
|---|---|
| `ENVIRONMENT=production` | Services refuse to start with the placeholder `JWT_SECRET_KEY` |
| `JWT_SECRET_KEY` is a fresh random value (`openssl rand -hex 32`) | It signs every session; changing it signs everyone out |
| `POSTGRES_PASSWORD` changed from the default | The default is public |
| `COOKIE_SECURE=true` and TLS in front | Cookies are the only session carrier; without HTTPS the browser will not send them (localhost excepted) |
| Postgres (5432), Redis (6379) and the Traefik dashboard (8080) stay bound to `127.0.0.1` | None of them has authentication you should rely on |
| Only ports 80 and 443 are reachable from outside | Backend services are on an internal network and must not be reached around the proxy |

**TLS is not configured in this repository.** Traefik listens on 443 but has no certificate resolver. Either terminate TLS in front of it (a cloud load balancer, or another proxy) or add a Traefik certificate resolver to `docker-compose.yml`. Doing neither means serving sessions over plain HTTP.

**Docker socket.** Traefik discovers services by reading `/var/run/docker.sock` (mounted read-only). Read-only still exposes container metadata to Traefik, and anyone who compromises Traefik can inspect the host's Docker. Put a socket proxy in front of it if that matters in your environment.

**Single instances.** Run exactly one `outbox-publisher` (it preserves event order). Scaling the API services or `link-worker` beyond one instance each has not been tested here. The design should allow it (the API services hold no state, and suggestions are rebuilt idempotently from database state), but verify before relying on it.

## Start, stop, update

```bash
docker compose up -d --build          # start or update; migrations run first
scripts/verify-deployment.sh          # health, readiness, routing, authentication
docker compose ps                     # state of every container
docker compose logs -f note-service   # follow one service (JSON lines)
docker compose down                   # stop; data is kept in volumes
```

Updating is `git pull` then `docker compose up -d --build`. The `migrate` service applies new migrations before the API services start. Take a backup first when a release contains a migration.

## Health and logs

- `GET /health` (alive) and `GET /ready` (database, plus Redis for the note and link services; 503 if a dependency is down) on each API service. They are used by Docker health checks and are not routed publicly.
- `outbox-publisher` and `link-worker` write a heartbeat file that their health checks read, so `docker compose ps` shows a stuck worker as unhealthy.
- Logs are JSON, one object per line, with `timestamp`, `level`, `service`, `message` and `correlation_id`. The correlation id is returned to clients as the `X-Correlation-ID` header (and in error bodies) and travels inside note events, so one request can be followed from the browser through the worker: `docker compose logs | grep <id>`.
- Passwords, tokens, cookies and database error text are never logged. Verified against live logs on 2026-10-17.
- `LOG_LEVEL` (default `INFO`) controls verbosity.

## Backup and restore

All state is in PostgreSQL. Redis only carries events that are already recorded in the database outbox.

**Back up** (a compressed, consistent snapshot; safe while running):

```bash
mkdir -p backups
docker compose exec -T postgres pg_dump -U "${POSTGRES_USER:-linknote}" -d "${POSTGRES_DB:-linknote}" \
  --format=custom > "backups/linknote-$(date +%Y%m%d-%H%M%S).dump"
```

Copy dumps off the machine; a backup on the same disk does not survive the disk.

**Check a backup** by restoring it into a scratch database (this procedure was run against the live stack: the restored database had the same row counts as the source):

```bash
docker compose exec -T postgres psql -U linknote -d postgres -c "CREATE DATABASE restore_check"
docker compose exec -T postgres pg_restore -U linknote -d restore_check --no-owner < backups/FILE.dump
docker compose exec -T postgres psql -U linknote -d restore_check -c "select count(*) from notes"
docker compose exec -T postgres psql -U linknote -d postgres -c "DROP DATABASE restore_check"
```

**Restore over the real database** (destroys current data; stop writers first):

```bash
docker compose stop auth-service note-service link-service graph-service outbox-publisher link-worker frontend
docker compose exec -T postgres psql -U linknote -d postgres -c "DROP DATABASE linknote" -c "CREATE DATABASE linknote"
docker compose exec -T postgres pg_restore -U linknote -d linknote --no-owner < backups/FILE.dump
docker compose up -d
scripts/verify-deployment.sh
```

(Use your own `POSTGRES_USER` and `POSTGRES_DB` if you changed them.)

**After a restore, or if Redis data is lost:** events already published are not replayed. Notes written before the loss keep their accepted links, but get new suggestions only when they are next edited (the "no backfill" gap in [implementation-notes.md](implementation-notes.md)). Unpublished outbox rows are re-sent automatically.

**Recovery objectives.** None are defined by the requirements. With nightly dumps, the worst case is losing a day. Run `pg_dump` more often, or use PostgreSQL WAL archiving, if that is too much.

## Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| `docker compose` says it cannot connect to the Docker API | Docker Desktop/daemon is not running. Start it and retry. |
| `JWT_SECRET_KEY must be set` | No `.env`. `cp .env.example .env` and set the secret. |
| A service exits at start, logs mention the JWT secret | `ENVIRONMENT=production` with the placeholder secret. Set a real one. |
| Every URL returns Traefik's `404 page not found` | Traefik found no containers. Traefik older than v3 cannot talk to Docker Engine 29; this repository pins v3.6. Check `docker compose logs traefik` and that the services are running. |
| Port 80 is already in use | Another web server owns it. Stop it, or change the `traefik` port mapping. |
| Sign-in appears to work but you are bounced back to the login page | The cookie was not stored: `COOKIE_SECURE=true` over plain HTTP on a host other than `localhost`. Use HTTPS, or set `COOKIE_SECURE=false` for a private test only. |
| `429 Too Many Requests` when signing in | Login, register and refresh are limited to 30 per minute per IP (burst 10). Wait a minute. Behind a shared proxy, all users share one IP unless Traefik is told to trust `X-Forwarded-For`. |
| `docker compose ps` shows `migrate` as exited | That is normal if it exited with code 0. If non-zero: `docker compose logs migrate`. |
| Suggestions never appear | Walk the chain: `docker compose logs outbox-publisher` (is "outbox events published" appearing?), `docker compose logs link-worker` ("note event processed"), `docker compose ps` (any unhealthy worker?). Notes need at least two shared keywords and a score of 0.30; short or unrelated notes correctly produce nothing. Notes written before the worker ran have no suggestions until edited. |
| `outbox-publisher` or `link-worker` unhealthy | The heartbeat file stopped updating, so the loop is stuck, usually because Postgres or Redis is unreachable. `docker compose logs <service>`, then `docker compose restart <service>`. Nothing is lost: events wait in the outbox. |
| `/ready` returns 503 | The response names which dependency failed. Check `docker compose ps postgres redis`. |
| Graph shows "most recently updated N of M" | You have more than `GRAPH_MAX_NODES` (500) notes. Filter by tag, or raise the limit and re-test render speed. |
| Frontend loads but every request fails | The frontend reaches the API through Traefik on the same origin. Opening the app on `localhost:3000` (dev server) without `API_PROXY_TARGET` has no backend. |
| Disk fills up | Postgres and Redis volumes grow; see the housekeeping notes in [database.md](database.md). `docker system df` shows image and build-cache usage. |

When reporting a problem, include the `X-Correlation-ID` from the failing response; it finds every log line for that request.
