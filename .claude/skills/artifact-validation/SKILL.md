---
name: artifact-validation
description: Validates that required SDLC artifacts exist and contain expected content sections
version: 2.0.0
invocation: model
related_agents:
  - sdlc-orchestrator
related_scripts:
  - .claude/scripts/validate-artifacts.sh
---

# Artifact Validation

## When to Use

Use this skill when the orchestrator needs to validate that a stage's output artifacts are complete before advancing to the next stage. It can be applied manually by the orchestrator or automated via `.claude/scripts/validate-artifacts.sh`.

## Validation Procedure

### For Each Required Artifact

1. **Existence check:** Verify the file exists at the expected path.
2. **Non-empty check:** Verify the file has content (more than whitespace).
3. **Structure check:** Verify the file contains the expected sections for its type.
4. **Content check:** Verify required entries (e.g., at least one FR-N, at least 2 components) are present.
5. **Record result:** Log PASS or FAIL with specific details for each check.

### Expected Content by Artifact Type

#### requirements.md
- [ ] Contains "Functional Requirements" section with at least one FR-N entry
- [ ] Contains "Non-Functional Requirements" section with at least one NFR-N entry
- [ ] Contains "Acceptance Criteria" for each requirement
- [ ] Contains "Assumptions" section
- [ ] Contains "Out of Scope" section

#### architecture.md
- [ ] Contains "Components" section with at least 2 components
- [ ] Contains "Technology Choices" section
- [ ] Contains "Data Flow" section
- [ ] Contains requirements traceability mapping (FR-N → Component)

#### design-review.md
- [ ] Contains "Review Summary" with an assessment verdict
- [ ] Contains "Review Findings" with at least one finding
- [ ] Contains "Requirements Coverage Assessment"
- [ ] Every functional requirement has a coverage assessment

#### impl-plan.md
- [ ] Contains "Task List" with at least one IMPL-N task
- [ ] Contains "Execution Order"
- [ ] Each task has "Dependencies" and "Acceptance Criteria"
- [ ] Dependencies are acyclic (no circular dependencies)

#### code-review.md
- [ ] Contains findings for all 7 review areas
- [ ] Contains "Review Summary" with overall assessment
- [ ] No unresolved Critical findings
- [ ] No unresolved High findings (or documented justification)

#### verification-report.md
- [ ] Contains "Test Summary" with counts
- [ ] Contains "Test Execution Output"
- [ ] Contains verdict (PASS/FAIL)
- [ ] Contains "Content Quality Check"

#### pr-description.md
- [ ] Contains "Summary" section
- [ ] Contains "Changes Made" section
- [ ] Contains "Test Evidence" section
- [ ] Contains "Known Limitations" section
- [ ] Contains "Reviewer Checklist" section

#### CHANGELOG.md
- [ ] Contains "Added" section
- [ ] Contains "Changed" section
- [ ] Contains "Fixed" section

### Reporting

Return a validation result:

- **PASS:** All checks satisfied.
- **FAIL:** List the specific checks that failed, grouped by artifact.

### Automated Validation

The validation can also be run via the shell script:

```bash
bash .claude/scripts/validate-artifacts.sh
```

Exit code 0 = all required artifacts present and non-empty. Exit code 1 = one or more required artifacts missing or invalid.