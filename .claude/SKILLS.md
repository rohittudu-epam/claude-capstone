# Skill Catalog — .claude/skills

This file indexes all reusable skill procedures in the Agentic SDLC Pipeline. Each skill is defined in `.claude/skills/<name>/SKILL.md` with frontmatter metadata.

## Skill Index

| # | Skill | File | Invocation | Used By |
|---|-------|------|------------|---------|
| 1 | sdlc-workflow | `sdlc-workflow/SKILL.md` | user | sdlc-orchestrator, all agents |
| 2 | artifact-validation | `artifact-validation/SKILL.md` | model | sdlc-orchestrator |
| 3 | pr-assembly | `pr-assembly/SKILL.md` | model | pr-agent |
| 4 | structured-review | `structured-review/SKILL.md` | model | design-review-agent, review-agent |
| 5 | test-and-verify | `test-and-verify/SKILL.md` | model | verification-agent |

## Frontmatter Schema

Each skill definition file begins with YAML frontmatter:

```yaml
---
name: <skill-id>
description: <one-line description>
version: <semver>
invocation: <user | model>
related_agents:
  - <agent-name>
related_scripts:
  - <script-path>
---
```

- `invocation: user` — the skill is triggered by a direct user request.
- `invocation: model` — the skill is invoked by an agent/model during execution.

## Skill → Agent Mapping

| Skill | Primary Consumer(s) |
|-------|---------------------|
| sdlc-workflow | sdlc-orchestrator (pipeline entry point) |
| artifact-validation | sdlc-orchestrator (per-stage output validation) |
| structured-review | design-review-agent, review-agent (review procedure & severity definitions) |
| test-and-verify | verification-agent (test generation, execution, evaluation) |
| pr-assembly | pr-agent (PR description with 5 required sections) |

## Related Scripts

| Script | Purpose | Used By |
|--------|---------|---------|
| `.claude/scripts/run-tests.sh` | Detect project type and run the appropriate test suite | test-and-verify skill, verification-agent |
| `.claude/scripts/validate-artifacts.sh` | Validate that all expected SDLC artifacts exist and have content | artifact-validation skill, sdlc-orchestrator |