#!/usr/bin/env bash
# Verifies a running LinkNote stack after `docker compose up -d`.
#   1. every container is running and healthy (workers prove liveness through their heartbeat)
#   2. each API service answers /ready, i.e. its database (and Redis) dependencies are reachable
#   3. the proxy routes every public API prefix and the services enforce authentication
# Usage: scripts/verify-deployment.sh [base-url]      (default http://localhost)
# Exit status is 0 only if every check passed.
set -u
BASE="${1:-http://localhost}"
cd "$(dirname "$0")/.."
failures=0

pass() { printf 'PASS  %s\n' "$1"; }
fail() { printf 'FAIL  %s\n' "$1"; failures=$((failures + 1)); }

echo "== containers"
for service in postgres redis traefik migrate auth-service note-service link-service graph-service outbox-publisher link-worker; do
  id=$(docker compose ps -a -q "$service" 2>/dev/null)
  if [ -z "$id" ]; then fail "$service: container not found"; continue; fi
  state=$(docker inspect --format '{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}-{{end}}|{{.State.ExitCode}}' "$id")
  status=${state%%|*}; rest=${state#*|}; health=${rest%%|*}; exitcode=${rest#*|}
  if [ "$service" = "migrate" ]; then
    [ "$status" = "exited" ] && [ "$exitcode" = "0" ] && pass "migrate: completed successfully" || fail "migrate: $status (exit $exitcode); see: docker compose logs migrate"
  elif [ "$status" = "running" ] && { [ "$health" = "healthy" ] || [ "$health" = "-" ]; }; then
    pass "$service: running${health:+ ($health)}"
  else
    fail "$service: $status/$health; see: docker compose logs $service"
  fi
done

echo "== dependency readiness (/ready)"
for service in auth-service note-service link-service graph-service; do
  body=$(docker compose exec -T "$service" curl -sS -w ' [%{http_code}]' http://localhost:8000/ready 2>&1)
  case "$body" in
    *"[200]") pass "$service: $body" ;;
    *) fail "$service: $body" ;;
  esac
done

echo "== routing and authentication through the proxy ($BASE)"
for path in /api/auth/verify /api/notes /api/tags /api/suggestions /api/links /api/graph; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "$BASE$path")
  [ "$code" = "401" ] && pass "$path -> 401 (routed, authentication enforced)" || fail "$path -> $code (expected 401)"
done

echo
if [ "$failures" -eq 0 ]; then echo "All checks passed."; else echo "$failures check(s) failed."; fi
[ "$failures" -eq 0 ]
