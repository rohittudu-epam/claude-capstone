#!/usr/bin/env bash
# Measures search and graph latency through the proxy on a running stack with generated data.
# Creates a throwaway user with N notes straight in PostgreSQL (fast), times the public API, then deletes the user.
# Usage: scripts/measure-search.sh [notes=10000] [requests=100] [base-url=http://localhost]
# Run it on a stack whose performance you want to know about, not on a busy production system.
set -eu
N="${1:-10000}"; REQUESTS="${2:-100}"; BASE="${3:-http://localhost}"
cd "$(dirname "$0")/.."
DBUSER="${POSTGRES_USER:-linknote}"; DB="${POSTGRES_DB:-linknote}"
psql() { docker compose exec -T postgres psql -U "$DBUSER" -d "$DB" -tA "$@"; }
jar=$(mktemp); email="perf-$(date +%s)@example.com"
cleanup() { psql -c "delete from users where email = '$email'" >/dev/null; rm -f "$jar"; }
trap cleanup EXIT

curl -sf -c "$jar" -X POST "$BASE/api/auth/register" -H 'content-type: application/json' \
  -d "{\"email\":\"$email\",\"password\":\"perf-test-passphrase\"}" >/dev/null
curl -sf -c "$jar" -b "$jar" -X POST "$BASE/api/auth/login" -H 'content-type: application/json' \
  -d "{\"email\":\"$email\",\"password\":\"perf-test-passphrase\"}" >/dev/null
uid=$(psql -c "select id from users where email = '$email'")

# Varied vocabulary so the full-text index behaves like real notes: ~40 words drawn from a 2,000-word pool.
psql -c "
insert into notes (id, owner_id, title, body, created_at, updated_at)
select gen_random_uuid(), '$uid',
       'note ' || g || ' ' || 'w' || (random()*2000)::int || ' w' || (random()*2000)::int,
       (select string_agg('w' || (random()*2000)::int, ' ') from generate_series(1, 40) where g > 0),
       now() - (g || ' seconds')::interval, now() - (g || ' seconds')::interval
from generate_series(1, $N) g" >/dev/null
echo "created $N notes"

percentile() { sort -n | awk -v p="$1" '{a[NR]=$1} END {i=int(NR*p+0.9999); if (i<1) i=1; printf "%.0f ms", a[i]*1000}'; }
time_requests() {
  for i in $(seq 1 "$REQUESTS"); do
    curl -s -o /dev/null -w '%{time_total}\n' -b "$jar" "$1"
  done
}

report() { # label url: one run of N requests, both percentiles from the same samples
  local samples; samples=$(time_requests "$2")
  printf '  %-10s p50 %s   p95 %s\n' "$1" "$(printf '%s\n' "$samples" | percentile 0.5)" "$(printf '%s\n' "$samples" | percentile 0.95)"
}
echo "$REQUESTS requests each"
echo "search"
for term in w17 w1500 note; do report "q=$term" "$BASE/api/notes/search?q=$term&limit=20"; done
echo "graph (capped at GRAPH_MAX_NODES)"
report "all notes" "$BASE/api/graph"
echo "cleaned up user $email"
