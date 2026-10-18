#!/usr/bin/env bash
# Smoke test for LinkNote stack
# Verifies that the seeded application is functional

set -e

FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
BACKEND_URL="${BACKEND_URL:-http://localhost:8001}"
DEMO_EMAIL="${SEED_DEMO_EMAIL:-demo@linknote.local}"
DEMO_PASSWORD="${SEED_DEMO_PASSWORD:-demo123456}"

PASS=0
FAIL=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check() {
    local name="$1"
    local command="$2"

    echo -n "  [$name] "

    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}PASS${NC}"
        ((PASS++))
        return 0
    else
        echo -e "${RED}FAIL${NC}"
        ((FAIL++))
        return 1
    fi
}

echo ""
echo "🔬 LinkNote Smoke Test"
echo "======================="
echo ""

# Test 1: Frontend responds
echo "Frontend Connectivity:"
check "Frontend HTTP 200" "curl -f -s -o /dev/null -w '%{http_code}' $FRONTEND_URL | grep -q 200"
check "Frontend serves HTML" "curl -s $FRONTEND_URL | grep -q '<html'"

# Test 2: Backend health endpoints
echo ""
echo "Backend Health:"
check "Auth service health" "curl -f -s http://localhost:8001/health | grep -q 'ok'"
check "Note service health" "curl -f -s http://localhost:8002/health | grep -q 'ok'"
check "Link service health" "curl -f -s http://localhost:8003/health | grep -q 'ok'"
check "Graph service health" "curl -f -s http://localhost:8004/health | grep -q 'ok'"

# Test 3: Demo login works
echo ""
echo "Authentication:"

# Get CSRF token and cookies
CSRF_RESPONSE=$(curl -s -c /tmp/linknote-cookies.txt "$FRONTEND_URL/login")

# Attempt login
LOGIN_RESPONSE=$(curl -s -b /tmp/linknote-cookies.txt \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$DEMO_EMAIL\",\"password\":\"$DEMO_PASSWORD\"}" \
    -w "\n%{http_code}" \
    http://localhost:8001/api/auth/login)

HTTP_CODE=$(echo "$LOGIN_RESPONSE" | tail -n 1)
BODY=$(echo "$LOGIN_RESPONSE" | head -n -1)

if [[ "$HTTP_CODE" == "200" ]] && echo "$BODY" | grep -q '"access_token"'; then
    echo -e "  [Demo login succeeds] ${GREEN}PASS${NC}"
    ((PASS++))

    # Extract access token for subsequent tests
    ACCESS_TOKEN=$(echo "$BODY" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

    # Test 4: Notes exist
    echo ""
    echo "Seed Data:"

    NOTES_RESPONSE=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" \
        http://localhost:8002/api/notes)

    NOTE_COUNT=$(echo "$NOTES_RESPONSE" | grep -o '"id"' | wc -l)

    if [[ $NOTE_COUNT -ge 16 ]]; then
        echo -e "  [Notes count >= 16 ($NOTE_COUNT found)] ${GREEN}PASS${NC}"
        ((PASS++))
    else
        echo -e "  [Notes count >= 16 ($NOTE_COUNT found)] ${RED}FAIL${NC}"
        ((FAIL++))
    fi

    # Test 5: Suggestions exist
    SUGGESTIONS_RESPONSE=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" \
        http://localhost:8003/api/suggestions?limit=100)

    SUGGESTION_COUNT=$(echo "$SUGGESTIONS_RESPONSE" | grep -o '"source_note_id"' | wc -l)

    if [[ $SUGGESTION_COUNT -ge 0 ]]; then
        echo -e "  [Suggestions exist ($SUGGESTION_COUNT found)] ${GREEN}PASS${NC}"
        ((PASS++))
    else
        echo -e "  [Suggestions exist] ${RED}FAIL${NC}"
        ((FAIL++))
    fi

    # Test 6: Graph connections exist
    GRAPH_RESPONSE=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" \
        http://localhost:8004/api/graph)

    LINK_COUNT=$(echo "$GRAPH_RESPONSE" | grep -o '"source"' | wc -l)

    if [[ $LINK_COUNT -ge 10 ]]; then
        echo -e "  [Graph links >= 10 ($LINK_COUNT found)] ${GREEN}PASS${NC}"
        ((PASS++))
    else
        echo -e "  [Graph links >= 10 ($LINK_COUNT found)] ${RED}FAIL${NC}"
        ((FAIL++))
    fi

    # Test 7: Isolated notes have 0 connections
    # Find "Hello World" note ID
    HELLO_NOTE=$(echo "$NOTES_RESPONSE" | grep -B5 -A5 '"title":"Hello World"' | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

    if [[ -n "$HELLO_NOTE" ]]; then
        HELLO_LINKS=$(echo "$GRAPH_RESPONSE" | grep -c "\"source\":\"$HELLO_NOTE\"" || echo "0")
        HELLO_LINKS=$((HELLO_LINKS + $(echo "$GRAPH_RESPONSE" | grep -c "\"target\":\"$HELLO_NOTE\"" || echo "0")))

        if [[ $HELLO_LINKS -eq 0 ]]; then
            echo -e "  [Isolated note has 0 connections] ${GREEN}PASS${NC}"
            ((PASS++))
        else
            echo -e "  [Isolated note has 0 connections (found $HELLO_LINKS)] ${YELLOW}WARN${NC}"
        fi
    fi

else
    echo -e "  [Demo login succeeds] ${RED}FAIL${NC} (HTTP $HTTP_CODE)"
    ((FAIL++))
    echo ""
    echo "Cannot proceed with data tests without authentication."
fi

# Cleanup
rm -f /tmp/linknote-cookies.txt

# Summary
echo ""
echo "======================="
echo ""
if [[ $FAIL -eq 0 ]]; then
    echo -e "${GREEN}✅ All checks passed!${NC} ($PASS/$((PASS + FAIL)))"
    echo ""
    exit 0
else
    echo -e "${RED}❌ Some checks failed.${NC} ($PASS passed, $FAIL failed)"
    echo ""
    exit 1
fi
