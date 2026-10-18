#!/usr/bin/env bash
# Validates that all expected SDLC artifacts exist and have content
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0

check_file() {
  local file="$1"
  local required="$2"  # "required" or "optional"
  local description="$3"
  
  if [ -f "$file" ]; then
    if [ -s "$file" ]; then
      echo -e "${GREEN}✅ PASS${NC} $file — $description"
      PASS=$((PASS+1))
    else
      echo -e "${RED}❌ FAIL${NC} $file — exists but is empty"
      FAIL=$((FAIL+1))
    fi
  elif [ "$required" = "required" ]; then
    echo -e "${RED}❌ FAIL${NC} $file — missing (required)"
    FAIL=$((FAIL+1))
  else
    echo -e "${YELLOW}⚠️  WARN${NC} $file — missing (optional)"
    WARN=$((WARN+1))
  fi
}

check_section() {
  local file="$1"
  local section="$2"
  
  if [ -f "$file" ] && grep -qi "$section" "$file"; then
    echo -e "${GREEN}  ✓${NC} Contains '$section'"
  else
    echo -e "${RED}  ✗${NC} Missing '$section'"
    FAIL=$((FAIL+1))
  fi
}

echo "========================================="
echo "  SDLC Artifact Validation"
echo "========================================="
echo ""

echo "--- Stage 1: Requirements ---"
check_file "docs/requirements.md" "required" "Requirements document"
if [ -f "docs/requirements.md" ]; then
  check_section "docs/requirements.md" "Functional Requirements"
  check_section "docs/requirements.md" "Non-Functional Requirements"
fi

echo ""
echo "--- Stage 2: Architecture ---"
check_file "docs/architecture.md" "required" "Architecture document"
if [ -f "docs/architecture.md" ]; then
  check_section "docs/architecture.md" "Components"
  check_section "docs/architecture.md" "Technology Choices"
  check_section "docs/architecture.md" "Data Flow"
fi

echo ""
echo "--- Stage 3: Design Review ---"
check_file "docs/design-review.md" "required" "Design review document"
if [ -f "docs/design-review.md" ]; then
  check_section "docs/design-review.md" "Review Summary"
  check_section "docs/design-review.md" "Review Findings"
fi

echo ""
echo "--- Stage 4: Implementation Plan ---"
check_file "docs/impl-plan.md" "required" "Implementation plan"
if [ -f "docs/impl-plan.md" ]; then
  check_section "docs/impl-plan.md" "Task List"
  check_section "docs/impl-plan.md" "Execution Order"
fi

echo ""
echo "--- Stage 5: Implementation ---"
if [ -d "src" ] || [ -d "lib" ] || [ -d "app" ]; then
  echo -e "${GREEN}✅ PASS${NC} Source directory exists"
  PASS=$((PASS+1))
else
  echo -e "${YELLOW}⚠️  WARN${NC} No standard source directory (src/, lib/, app/) found"
  WARN=$((WARN+1))
fi

echo ""
echo "--- Stage 6: Code Review ---"
check_file "docs/code-review.md" "required" "Code review report"
if [ -f "docs/code-review.md" ]; then
  check_section "docs/code-review.md" "Correctness"
  check_section "docs/code-review.md" "Security"
  check_section "docs/code-review.md" "Error Handling"
  check_section "docs/code-review.md" "Test Coverage"
  check_section "docs/code-review.md" "Code Clarity"
  check_section "docs/code-review.md" "DRY Principle"
  check_section "docs/code-review.md" "Dependency Safety"
fi

echo ""
echo "--- Stage 7: Verification ---"
check_file "docs/verification-report.md" "required" "Verification report"
if [ -f "docs/verification-report.md" ]; then
  check_section "docs/verification-report.md" "Test Summary"
  check_section "docs/verification-report.md" "Test Execution Output"
fi
if [ -d "tests" ] || [ -d "test" ] || [ -d "__tests__" ]; then
  echo -e "${GREEN}✅ PASS${NC} Test directory exists"
  PASS=$((PASS+1))
else
  echo -e "${RED}❌ FAIL${NC} No test directory found"
  FAIL=$((FAIL+1))
fi

echo ""
echo "--- Stage 8: PR ---"
check_file "docs/pr-description.md" "required" "PR description"
if [ -f "docs/pr-description.md" ]; then
  check_section "docs/pr-description.md" "Summary"
  check_section "docs/pr-description.md" "Changes Made"
  check_section "docs/pr-description.md" "Test Evidence"
  check_section "docs/pr-description.md" "Known Limitations"
  check_section "docs/pr-description.md" "Reviewer Checklist"
fi
check_file "docs/CHANGELOG.md" "required" "Changelog"

echo ""
echo "========================================="
echo -e "  Results: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC}, ${YELLOW}${WARN} warnings${NC}"
echo "========================================="

if [ "$FAIL" -gt 0 ]; then
  exit 1
else
  exit 0
fi
