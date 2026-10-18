# .claude — Agentic SDLC Pipeline Configuration

This directory contains the agent definitions, skill procedures, scripts, and settings for the **Agentic SDLC Pipeline** — an 8-stage workflow from requirements through PR creation, orchestrated by Claude Code agents.

## Directory Structure

```
.claude/
├── agents/              # Specialist agent definitions (9 agents)
│   ├── orchestrator.md           # Central pipeline orchestrator (Stage controller)
│   ├── requirements-agent.md     # Stage 1: Requirements gathering
│   ├── architecture-agent.md     # Stage 2: Architecture design
│   ├── design-review-agent.md    # Stage 3: Design review
│   ├── impl-planning-agent.md    # Stage 4: Implementation planning
│   ├── implementation-agent.md   # Stage 5: Code implementation
│   ├── review-agent.md           # Stage 6: Code review
│   ├── verification-agent.md     # Stage 7: Test generation & execution
│   └── pr-agent.md               # Stage 8: Pull Request creation
├── skills/              # Reusable skill procedures (5 skills)
│   ├── sdlc-workflow/        # Full pipeline initiation
│   ├── artifact-validation/  # Artifact completeness validation
│   ├── pr-assembly/          # PR description assembly
│   ├── structured-review/    # Structured review procedure
│   └── test-and-verify/      # Test generation & verification
├── scripts/             # Shell scripts for automation
│   ├── run-tests.sh          # Detect project type & run tests
│   └── validate-artifacts.sh # Validate all SDLC artifacts
├── settings.json        # Project config, agent/skill directories, permissions
├── settings.local.json  # Local permissions override (e.g., external API domains)
└── README.md            # This file
```

## Pipeline Stages

| Stage | Agent | Output | Quality Gate |
|-------|-------|--------|--------------|
| 1 | requirements-agent | `docs/requirements.md` | User confirmation |
| 2 | architecture-agent | `docs/architecture.md` | Requirements coverage |
| 3 | design-review-agent | `docs/design-review.md` | Risks documented |
| 4 | impl-planning-agent | `docs/impl-plan.md` | Tasks cover all components |
| 5 | implementation-agent | Source files | Human approval, builds successfully |
| 6 | review-agent | `docs/code-review.md` | No critical unresolved findings |
| 7 | verification-agent | Tests, `docs/verification-report.md` | All tests pass |
| 8 | pr-agent | `docs/pr-description.md`, `docs/CHANGELOG.md` | All 5 required PR sections present |

## How to Use

### Full Pipeline

Invoke the **sdlc-workflow** skill or load the **sdlc-orchestrator** agent:

```
User: "Run the SDLC pipeline for this user story: [story]"
```

The orchestrator will:
1. Create `workflow-state.json` to track pipeline state.
2. Invoke each specialist agent in sequence.
3. Validate outputs after each stage (using the artifact-validation skill).
4. Enforce quality gates and human approvals.
5. Produce a completion report when finished.

### Individual Stage

You can also invoke any agent directly for a specific task:

```
User: "Use the architecture-agent to design the system based on docs/requirements.md"
```

## Configuration

- `settings.json` — defines agent/skill directories, the orchestrator entry point, and allowed/denied permissions.
- `settings.local.json` — local overrides (e.g., additional domains for WebFetch permissions).

## Version

All agents and skills are versioned `2.0.0`. Check the frontmatter of each file for its version.