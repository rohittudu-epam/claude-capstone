# Agent Inventory

## Overview

This ecosystem contains **1 orchestrator** and **8 specialist agents** implementing the full Agentic SDLC pipeline.

## Agents

| Agent ID | Name | SDLC Stage | Input Artifacts | Output Artifacts |
|----------|------|-----------|----------------|-----------------|
| `orchestrator` | SDLC Orchestrator | All | User story, all artifacts | `workflow-state.json`, completion report |
| `requirements-agent` | Requirements Analyst | 1 — Requirements | User story | `docs/requirements.md` |
| `architecture-agent` | Solutions Architect | 2 — Architecture | `docs/requirements.md` | `docs/architecture.md` |
| `design-review-agent` | Design Reviewer | 3 — Design Review | `docs/architecture.md`, `docs/requirements.md` | `docs/design-review.md`, updated `docs/architecture.md` |
| `impl-planning-agent` | Implementation Planner | 4 — Planning | `docs/architecture.md`, `docs/design-review.md` | `docs/impl-plan.md` |
| `implementation-agent` | Implementation Engineer | 5 — Implementation | `docs/impl-plan.md`, `docs/architecture.md`, `docs/requirements.md` | Source files |
| `review-agent` | Code Reviewer | 6 — Review | Source files, `docs/requirements.md`, `docs/architecture.md` | `docs/code-review.md`, fixes |
| `verification-agent` | Verification Engineer | 7 — Verification | Source files, `docs/requirements.md` | Test files, `docs/verification-report.md` |
| `pr-agent` | PR Engineer | 8 — Pull Request | All artifacts | `docs/pr-description.md`, `docs/CHANGELOG.md` |

## Dependency Chain

```
requirements-agent → architecture-agent → design-review-agent → impl-planning-agent → implementation-agent → review-agent → verification-agent → pr-agent
```

All stages are strictly sequential. Each stage requires its predecessor to complete successfully.

## Human Approval Gates

| Stage | Gate Description |
|-------|-----------------|
| 1 — Requirements | User must approve `docs/requirements.md` before proceeding |
| 5 — Implementation | User must approve the implementation approach before coding begins |
| 8 — PR (implicit) | PR must be reviewed and merged by a human |
