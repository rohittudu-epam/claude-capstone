# Orchestrator Design

## Architecture

The orchestrator is a Claude Code agent (`.claude/agents/orchestrator.md`) that acts as the central controller for the SDLC pipeline. It does not perform specialist work — it delegates to the 8 specialist agents, validates their outputs, enforces quality gates, and manages workflow state.

## Invocation

The orchestrator is activated via the `sdlc-workflow` skill or by directly loading the orchestrator agent definition.

### Via Skill
When a user asks to "run the SDLC pipeline" or similar, the `sdlc-workflow` skill provides the entry point that activates the orchestrator.

### Via Direct Agent Load
The user can directly invoke the orchestrator by referencing `.claude/agents/orchestrator.md`.

## Delegation Model

The orchestrator delegates to specialist agents by:
1. Reading the agent's definition file from `.claude/agents/`.
2. Adopting the agent's instructions for the current stage.
3. Executing the agent's procedure completely.
4. Returning to orchestrator mode to validate outputs and advance.

This is a **role-switching model** within a single Claude Code session, not a multi-process subagent invocation. The orchestrator tracks which role it is currently executing and maintains the workflow state across role transitions.

## State Management

Workflow state is persisted in `workflow-state.json` at the project root. This file tracks:
- Which stages have completed.
- Which stage is current.
- What artifacts have been produced.
- Retry counts.
- Overall pipeline status.

If the session is interrupted, the orchestrator can resume from the last incomplete stage by reading `workflow-state.json`.

## Failure Handling

- **Transient failures:** Retry up to 2 times per stage.
- **Persistent failures:** Set stage to BLOCKED, produce partial completion report.
- **Human rejections:** Not counted as retries. Incorporate feedback and re-execute.
- **Missing prerequisites:** Stop pipeline and report which artifact is missing.

## Completion

The orchestrator produces a completion report at the end of the pipeline (or when it stops due to a failure). The report summarizes all stages, artifacts, quality gate results, and remaining issues.
