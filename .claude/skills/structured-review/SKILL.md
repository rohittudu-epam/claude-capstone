---
name: structured-review
description: Reusable structured review procedure for evaluating technical artifacts against defined criteria
version: 2.0.0
invocation: model
related_agents:
  - design-review-agent
  - review-agent
---

# Structured Review Procedure

## When to Use

Use this skill when performing a structured review of any technical artifact (architecture document, code, design specification). This procedure is used by both the Design Review Agent and the Code Review Agent.

## Review Procedure

### 1. Define Review Scope

- Identify the artifact(s) under review.
- Identify the reference documents (requirements, architecture, standards).
- Identify the review dimensions applicable to the artifact type.

### 2. Systematic Evaluation

For each review dimension:

1. State the dimension and the question(s) being evaluated.
2. Examine the artifact against each question.
3. Record findings with:
   - **Severity:** Critical | High | Medium | Low | Informational
   - **Location:** File, section, or line reference.
   - **Description:** What was found.
   - **Recommendation:** What to change.
   - **Decision:** Accepted | Deferred | Rejected (with rationale)
4. If no issues found in a dimension, record "No issues found" to confirm it was reviewed.

### 3. Severity Definitions

| Severity | Definition | Action Required |
|----------|-----------|----------------|
| Critical | Blocks deployment, causes data loss or security breach | Must fix before proceeding |
| High | Significant defect or risk, likely to cause problems | Must fix or justify deferral |
| Medium | Quality issue, technical debt, or potential problem | Should fix |
| Low | Minor improvement opportunity | Fix when convenient |
| Informational | Observation or suggestion | No action required |

### 4. Generate Review Report

Structure the report with:

- Metadata (artifact under review, reference documents, reviewer, version)
- Summary assessment (Approved / Approved with Changes / Changes Required)
- Findings by review dimension (in tables with severity, location, description, recommendation, status)
- Critical issues requiring immediate action
- Recommendations for improvement
- Agreed decisions with rationale

### 5. Apply Fixes

For Critical and High severity findings:
- Apply the fix to the artifact.
- Verify the fix doesn't introduce new issues.
- Mark the finding as "Fixed" in the report.

For Medium findings: Fix if straightforward, otherwise mark as "Acknowledged".

### Review Finding Template

```
### Finding [ID]: [Title]
- **Severity:** Critical | High | Medium | Low | Informational
- **Category:** [Review dimension]
- **Location:** [File:section or line reference]
- **Description:** [What was found]
- **Recommendation:** [What to change]
- **Decision:** [Accepted / Deferred / Rejected — with rationale]
- **Status:** [Open / Fixed / Acknowledged]
```