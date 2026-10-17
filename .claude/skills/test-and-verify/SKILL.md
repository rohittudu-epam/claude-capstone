---
name: test-and-verify
description: Reusable procedure for generating test cases from requirements, running tests, and evaluating results
version: 2.0.0
invocation: model
related_agents:
  - verification-agent
---

# Test and Verify Procedure

## When to Use

Use this skill when generating and executing tests for the implemented code. Used by the Verification Agent (Stage 7).

## Test Generation Procedure

### 1. Derive Test Cases from Requirements

For each functional requirement in `requirements.md`:

- **Happy path test:** Verify the requirement works correctly with valid input.
- **Edge case tests:**
  - Empty input / no data
  - Missing required fields
  - Not Found / 404 responses
  - Boundary values (minimum, maximum)
- **Error case tests:**
  - API failure / timeout
  - Invalid input format
  - Permission denied
  - Network unavailable (if applicable)

### 2. Test Structure

Organize tests by component:

```
tests/
  unit/
    [component-name].test.[ext]
  integration/
    [scenario-name].test.[ext]
```

### 3. Test Naming Convention

Use descriptive test names:
- `"should return [expected] when [condition]"`
- `"should throw [error] when [invalid condition]"`
- `"should handle [edge case] gracefully"`

### 4. Execution

Run the full test suite and capture output including:
- Total test count
- Pass/fail counts
- Individual test results
- Error messages for failures
- Execution time

Use `.claude/scripts/run-tests.sh` for automated test detection and execution:

```bash
bash .claude/scripts/run-tests.sh
```

### 5. Evaluation

- **All pass:** Verification succeeds.
- **Any fail:** Attempt to fix (max 3 fix-and-rerun cycles), then report remaining failures.
- **No tests run:** Verification fails — test infrastructure must be set up.

### 6. Coverage Expectations

- Happy path covered for every functional requirement.
- At least 3 edge cases tested (empty input, missing fields, error conditions).
- Error cases covered for API failures, invalid input, and missing files.