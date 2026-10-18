# SDLC Workflow Specification

## Pipeline Overview

The Agentic SDLC pipeline executes 8 sequential stages, each handled by a specialist agent and coordinated by the central orchestrator.

## Execution Flow

```
┌─────────────────────────────────────────┐
│           USER PROVIDES STORY           │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│  STAGE 1: REQUIREMENTS                   │
│  Agent: requirements-agent               │
│  Gate: User approval                     │
│  Output: docs/requirements.md                 │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│  STAGE 2: ARCHITECTURE                   │
│  Agent: architecture-agent               │
│  Gate: Requirements coverage             │
│  Output: docs/architecture.md                 │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│  STAGE 3: DESIGN REVIEW                  │
│  Agent: design-review-agent              │
│  Gate: No unresolved Critical findings   │
│  Output: docs/design-review.md,              │
│          updated docs/architecture.md         │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│  STAGE 4: IMPLEMENTATION PLANNING        │
│  Agent: impl-planning-agent              │
│  Gate: All components have tasks         │
│  Output: docs/impl-plan.md                    │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│  STAGE 5: IMPLEMENTATION                 │
│  Agent: implementation-agent             │
│  Gate: Human approval + builds OK        │
│  Output: Source files                    │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│  STAGE 6: CODE REVIEW                    │
│  Agent: review-agent                     │
│  Gate: No unresolved Critical/High       │
│  Output: docs/code-review.md, fixes          │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│  STAGE 7: VERIFICATION                   │
│  Agent: verification-agent               │
│  Gate: All tests pass                    │
│  Output: Test files,                    │
│          docs/verification-report.md          │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│  STAGE 8: PULL REQUEST                   │
│  Agent: pr-agent                         │
│  Gate: All 5 PR sections present         │
│  Output: docs/pr-description.md,             │
│          docs/CHANGELOG.md, PR (if gh avail)  │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│           PIPELINE COMPLETE              │
│     Completion report generated          │
└──────────────────────────────────────────┘
```

## Quality Gates

| Stage | Gate | Criteria | Failure Action |
|-------|------|----------|---------------|
| 1 | User approval | User explicitly approves `docs/requirements.md` | Re-elicit with feedback |
| 2 | Requirements coverage | Every FR maps to a component | Add missing components |
| 3 | Design review | No unresolved Critical findings | Remediate and re-review |
| 4 | Task completeness | Every component has implementation tasks | Add missing tasks |
| 5 | Build success + Human approval | Code builds without errors, user approves approach | Fix build errors, incorporate user feedback |
| 6 | Review clearance | No unresolved Critical/High findings | Fix and re-review |
| 7 | Test passage | All tests pass (0 failures) | Fix bugs and re-run (max 3 cycles) |
| 8 | PR completeness | All 5 required sections present | Regenerate missing sections |

## Artifact Lifecycle

| Artifact | Created By | Read By | Modified By |
|----------|-----------|---------|-------------|
| `docs/requirements.md` | requirements-agent | architecture-agent, design-review-agent, implementation-agent, review-agent, verification-agent, pr-agent | requirements-agent (revisions) |
| `docs/architecture.md` | architecture-agent | design-review-agent, impl-planning-agent, implementation-agent, review-agent, pr-agent | design-review-agent (fixes) |
| `docs/design-review.md` | design-review-agent | impl-planning-agent, pr-agent | — |
| `docs/impl-plan.md` | impl-planning-agent | implementation-agent, pr-agent | — |
| Source files | implementation-agent | review-agent, verification-agent, pr-agent | review-agent (fixes), verification-agent (bug fixes) |
| `docs/code-review.md` | review-agent | verification-agent, pr-agent | — |
| Test files | verification-agent | pr-agent | — |
| `docs/verification-report.md` | verification-agent | pr-agent | — |
| `docs/pr-description.md` | pr-agent | — | — |
| `docs/CHANGELOG.md` | pr-agent | — | — |
| `workflow-state.json` | orchestrator | orchestrator | orchestrator |
