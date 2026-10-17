# Agent Catalog — .claude/agents

This file indexes all specialist agents in the Agentic SDLC Pipeline. Each agent is defined in `.claude/agents/<name>.md` with frontmatter metadata.

## Agent Index

| # | Agent | File | Stage | Primary Output |
|---|-------|------|-------|----------------|
| 1 | sdlc-orchestrator | `orchestrator.md` | Pipeline controller | `workflow-state.json`, completion report |
| 2 | requirements-agent | `requirements-agent.md` | Stage 1 | `requirements.md` |
| 3 | architecture-agent | `architecture-agent.md` | Stage 2 | `architecture.md` |
| 4 | design-review-agent | `design-review-agent.md` | Stage 3 | `design-review.md` |
| 5 | impl-planning-agent | `impl-planning-agent.md` | Stage 4 | `impl-plan.md` |
| 6 | implementation-agent | `implementation-agent.md` | Stage 5 | Source files |
| 7 | review-agent | `review-agent.md` | Stage 6 | `code-review.md` |
| 8 | verification-agent | `verification-agent.md` | Stage 7 | Test files, `verification-report.md` |
| 9 | pr-agent | `pr-agent.md` | Stage 8 | `pr-description.md`, `CHANGELOG.md` |

## Frontmatter Schema

Each agent definition file begins with YAML frontmatter:

```yaml
---
name: <agent-id>
description: <one-line description>
version: <semver>
tools:
  - <tool-name>
related_skills:
  - <skill-name>
---
```

## Agent → Skill Mapping

| Agent | Uses Skill(s) |
|-------|--------------|
| sdlc-orchestrator | sdlc-workflow, artifact-validation, structured-review, test-and-verify, pr-assembly |
| requirements-agent | sdlc-workflow |
| architecture-agent | sdlc-workflow |
| design-review-agent | structured-review, sdlc-workflow |
| impl-planning-agent | sdlc-workflow |
| implementation-agent | sdlc-workflow |
| review-agent | structured-review, sdlc-workflow |
| verification-agent | test-and-verify, sdlc-workflow |
| pr-agent | pr-assembly, sdlc-workflow |

## Entry / Exit Criteria

Every agent declares:
- **Entry Criteria** — conditions that must be true before the agent starts.
- **Exit Criteria / Acceptance Criteria** — conditions that must be true for the stage to complete.

The orchestrator validates exit criteria before advancing to the next stage.