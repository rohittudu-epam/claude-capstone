---
name: sdlc-workflow
description: Initiates the full Agentic SDLC pipeline by activating the central orchestrator to execute all 8 stages from requirements through PR creation
version: 2.0.0
invocation: user
related_agents:
  - sdlc-orchestrator
  - requirements-agent
  - architecture-agent
  - design-review-agent
  - impl-planning-agent
  - implementation-agent
  - review-agent
  - verification-agent
  - pr-agent
---

# SDLC Workflow — Full Pipeline

## When to Use

Use this skill when the user wants to execute the complete Agentic SDLC pipeline for a user story — from requirements gathering through pull request creation.

## Entry Criteria

- A user story is available (as a file path, URL reference, or inline text).
- The repository is initialized with git.
- All 9 agent definition files exist in `.claude/agents/`.
- All 5 skill definitions exist in `.claude/skills/`.

## Prerequisites

- A user story must be available (as a file, URL reference, or inline text).
- The repository should be initialized with git.
- The `.claude/agents/` directory must contain the orchestrator and all specialist agent definitions.
- The `.claude/skills/` directory must contain all skill definitions referenced by the pipeline.

## Pipeline Overview

The pipeline executes 8 stages in strict sequential order. Each stage is owned by a specialist agent defined in `.claude/agents/`:

| Stage | Agent | Definition File | Primary Output | Quality Gate |
|-------|-------|----------------|----------------|--------------|
| 1 | requirements-agent | `.claude/agents/requirements-agent.md` | `docs/requirements.md` | User confirmation |
| 2 | architecture-agent | `.claude/agents/architecture-agent.md` | `docs/architecture.md` | Requirements coverage |
| 3 | design-review-agent | `.claude/agents/design-review-agent.md` | `docs/design-review.md` | Risks documented |
| 4 | impl-planning-agent | `.claude/agents/impl-planning-agent.md` | `docs/impl-plan.md` | Tasks cover all components |
| 5 | implementation-agent | `.claude/agents/implementation-agent.md` | Source files | Human approval, builds successfully |
| 6 | review-agent | `.claude/agents/review-agent.md` | `docs/code-review.md` | No critical unresolved findings |
| 7 | verification-agent | `.claude/agents/verification-agent.md` | Test files, `docs/verification-report.md` | All tests pass |
| 8 | pr-agent | `.claude/agents/pr-agent.md` | `docs/pr-description.md`, `docs/CHANGELOG.md` | All 5 required PR sections present |

## Modes of Execution

### Full Pipeline (default)

Execute all 8 stages in sequence through the orchestrator.

### Single Stage

Execute one specific stage only. Before doing so, verify that all prerequisite stages are `COMPLETED` in `workflow-state.json`. For example, to run Stage 3 (Design Review), Stages 1 and 2 must be complete.

## Steps

1. **Confirm the user story input.** Ask the user:
   - "Please provide the user story — as a file path, paste it here, or describe it."
   - Optionally ask: "Do you want to run the full pipeline, or a specific stage?"

2. **Activate the orchestrator.** Load and follow the instructions in `.claude/agents/orchestrator.md`.

3. **Execute the pipeline** through the orchestrator:
   - **Full pipeline:** The orchestrator invokes each specialist agent in sequence:
     - Stage 1: Requirements (`.claude/agents/requirements-agent.md`)
     - Stage 2: Architecture (`.claude/agents/architecture-agent.md`)
     - Stage 3: Design Review (`.claude/agents/design-review-agent.md`)
     - Stage 4: Implementation Planning (`.claude/agents/impl-planning-agent.md`)
     - Stage 5: Implementation (`.claude/agents/implementation-agent.md`)
     - Stage 6: Code Review (`.claude/agents/review-agent.md`)
     - Stage 7: Verification (`.claude/agents/verification-agent.md`)
     - Stage 8: PR Creation (`.claude/agents/pr-agent.md`)
   - **Single stage:** The orchestrator invokes only the requested stage after verifying prerequisites.

4. **Produce the completion report** as specified by the orchestrator.

## Pipeline Resumption

If a previous pipeline run was interrupted:

1. Check for `workflow-state.json` in the project root.
2. If it exists, read `current_stage` and `overall_status`.
3. If `overall_status` is `IN_PROGRESS` or a stage is `FAILED`/`BLOCKED`, resume from that stage using the orchestrator's resumption procedure.
4. Verify all prerequisite stages are `COMPLETED` before resuming.
5. Continue execution from the resumption point.

## Expected Outputs

- `docs/requirements.md`
- `docs/architecture.md`
- `docs/design-review.md`
- `docs/impl-plan.md`
- Source code files
- Test files
- `docs/code-review.md`
- `docs/verification-report.md`
- `docs/pr-description.md`
- `docs/CHANGELOG.md`
- `workflow-state.json`
- Completion report

## Notes

- The pipeline is sequential — each stage must complete before the next begins.
- Human approval is required at the requirements (Stage 1) and implementation (Stage 5) stages.
- The orchestrator will stop and report if any stage fails after retries (maximum 2 retries per stage).
- Use the `artifact-validation` skill to verify stage outputs before advancing.
- Use the `structured-review` skill for design and code review stages.
- Use the `test-and-verify` skill for the verification stage.
- Use the `pr-assembly` skill for the PR creation stage.
- Pipeline state is tracked in `workflow-state.json` in the project root.

## Troubleshooting

| Issue | Resolution |
|-------|-----------|
| `workflow-state.json` is missing | The orchestrator will create it with all stages set to `PENDING`. |
| A prior stage's output artifact is missing | Do not proceed. Re-run the missing stage or restore the artifact from git. |
| A stage fails after 2 retries | The stage is set to `BLOCKED`. Report the failure reason and request human intervention. |
| User is unavailable for approval | Set the stage to `AWAITING_APPROVAL` and wait. Do not count this against the retry limit. |
| Git commit fails | Report the error but do not block — the artifact is still valid. Note the failure in stage notes. |
| Resuming an interrupted pipeline | Read `workflow-state.json`, verify prerequisites, and resume from `current_stage`. |

## Invocation Examples

- "Run the SDLC pipeline for this user story: [story text]"
- "Run the full SDLC pipeline using the user story in docs/story.md"
- "Run only Stage 5 (Implementation) — Stages 1–4 are already complete"
- "Resume the interrupted SDLC pipeline from workflow-state.json"