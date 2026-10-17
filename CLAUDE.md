# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **Agentic SDLC Pipeline** — an 8-stage workflow automation system that orchestrates Claude Code agents to produce complete software projects from user stories. Each stage has a specialist agent responsible for that phase, coordinated by a central orchestrator.

The pipeline produces:
- Requirements specifications (`requirements.md`)
- System architecture (`architecture.md`)
- Design review and risk analysis (`design-review.md`)
- Implementation plan with task breakdown (`impl-plan.md`)
- Production source code
- Code review findings and fixes (`code-review.md`)
- Test suite and verification report (`verification-report.md`)
- Complete PR description with changelog (`pr-description.md`, `CHANGELOG.md`)

## Quick Start

To run a complete SDLC pipeline:

1. Create a user story file (e.g., `user-story.md`):
   ```markdown
   # User Story
   
   As a [role], I want [capability] so that [benefit].
   
   ## Acceptance Criteria
   - [Criterion 1]
   - [Criterion 2]
   ```

2. Initialize git if needed:
   ```bash
   git init
   ```

3. In Claude Code, invoke the pipeline:
   ```
   Run the full SDLC pipeline for the user story in user-story.md
   ```

## Architecture & Key Concepts

### Agent Ecosystem

The system delegates to 9 specialist agents (defined in `.claude/agents/`):

| Agent | Stage | Responsibility |
|-------|-------|-----------------|
| **orchestrator.md** | Meta | Central controller; delegates to stage agents, validates outputs, enforces quality gates, manages state |
| **requirements-agent.md** | 1 | Elicit and clarify requirements from user story |
| **architecture-agent.md** | 2 | Design system architecture addressing all requirements |
| **design-review-agent.md** | 3 | Review architecture for risks, gaps, improvement opportunities |
| **impl-planning-agent.md** | 4 | Decompose architecture into prioritized, dependency-ordered tasks |
| **implementation-agent.md** | 5 | Write production code following the implementation plan |
| **review-agent.md** | 6 | Review code across 7 areas (correctness, efficiency, reuse, etc.) and apply fixes |
| **verification-agent.md** | 7 | Generate and run tests; verify code quality |
| **pr-agent.md** | 8 | Assemble complete PR with all 5 required sections |

### Skills (in `.claude/skills/`)

Custom skills provide workflow automation and validation:

- **sdlc-workflow** — Entry point for running the full pipeline
- **structured-review** — Template for conducting multi-area code reviews
- **artifact-validation** — Validate generated artifacts for completeness and consistency
- **test-and-verify** — Generate and run unit/integration tests
- **pr-assembly** — Assemble final PR description with all sections

### State Management

Workflow execution state is persisted in `workflow-state.json` at the project root. The orchestrator reads/writes this file to:
- Track which stages have completed
- Identify the current stage
- List produced artifacts
- Track retry counts
- Support resume-from-interruption

If the session is interrupted, asking the orchestrator to resume will read `workflow-state.json` and continue from the last incomplete stage.

### Quality Gates

Each stage has a quality gate that must pass before advancing:

| Stage | Gate | Success Criteria |
|-------|------|------------------|
| 1 | User approval | User explicitly approves requirements |
| 2 | Requirements coverage | Every functional requirement maps to a component |
| 3 | Design review | No unresolved Critical findings |
| 4 | Task completeness | Every component has implementation tasks |
| 5 | Build success + approval | Code builds, user approves approach |
| 6 | Review clearance | No unresolved Critical/High findings |
| 7 | Test passage | All tests pass (0 failures) |
| 8 | PR completeness | All 5 required PR sections present |

## Common Development Tasks

### Running a Specific Stage

To run or resume a specific stage:

```
Load the [stage-name]-agent from .claude/agents/[stage-name]-agent.md and execute the [Stage Name] stage
```

For example:
```
Load the requirements-agent from .claude/agents/requirements-agent.md and execute the Requirements stage
```

### Resuming from Interruption

The orchestrator automatically checks `workflow-state.json` and resumes from the last incomplete stage:

```
Resume the SDLC pipeline from where it stopped. Check workflow-state.json for the current state.
```

### Validating Pipeline Artifacts

Run the validation script to check all generated artifacts:

```bash
.claude/scripts/validate-artifacts.sh
```

This verifies:
- All required files exist
- Artifacts have expected sections
- Cross-artifact references are consistent
- No missing dependencies

### Checking Workflow State

To see the current execution state:

```bash
cat workflow-state.json
```

This shows which stages completed, what artifacts were produced, and any retry counts.

## Testing & Verification

The `verification-agent` generates and runs tests during stage 7. Test framework depends on project type:

- **Node.js/JavaScript**: Jest, Mocha, Vitest
- **Python**: pytest
- **Go**: `go test`
- **Java**: Maven/Gradle + JUnit

All generated tests are placed in a `tests/` directory (or project-appropriate location) and are automatically run during verification. The verification-report.md documents all test results and coverage.

## Permissions Configuration

The project's `.claude/settings.json` pre-authorizes commands commonly needed:

- **Read/Write/Edit** — File operations
- **Bash(git *)** — Git operations
- **Bash(npm *, pip *, python *, pytest *, go *, gh *)** — Language tooling and GitHub CLI
- **Bash(cat *, ls *, mkdir *)** — Utility commands

Denied patterns include dangerous operations like `rm -rf /`, `sudo`, and piped shell commands from untrusted sources.

## Expected Outputs

After a complete pipeline run, the project contains:

| File | Description | Created By |
|------|-------------|-----------|
| `requirements.md` | Functional and non-functional requirements | requirements-agent |
| `architecture.md` | System design with components and tech stack | architecture-agent (updated by design-review-agent) |
| `design-review.md` | Risk analysis and design decisions | design-review-agent |
| `impl-plan.md` | Prioritized task breakdown | impl-planning-agent |
| `src/` (or similar) | Production source code | implementation-agent |
| `tests/` | Unit and integration test suite | verification-agent |
| `code-review.md` | Code review findings and fixes applied | review-agent |
| `verification-report.md` | Test results and quality metrics | verification-agent |
| `pr-description.md` | Complete PR description (5 sections) | pr-agent |
| `CHANGELOG.md` | Project changelog | pr-agent |
| `workflow-state.json` | Pipeline execution state (for resume) | orchestrator |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Agent file not found | Verify `.claude/agents/` contains all 9 agent `.md` files |
| Stage stuck on BLOCKED | Check `workflow-state.json` for notes explaining why; investigate the blocking artifact |
| Tests not running | Verify test framework installed for project type (jest, pytest, go test, etc.) |
| PR not created | Install GitHub CLI (`gh`) and authenticate with `gh auth login` |
| Git commit fails | Ensure git is initialized (`git init` if needed); check write permissions |
| workflow-state.json missing | Run orchestrator initialization; it will create and initialize the state file |
| Quality gate fails repeatedly | Read the gate's failure reason in `workflow-state.json` notes; may require manual intervention or architecture revision |

## Documentation References

- **Setup & Usage**: See `docs/setup-and-usage.md` for detailed setup instructions
- **Orchestrator Design**: See `docs/orchestrator-design.md` for how the orchestrator coordinates agents
- **SDLC Workflow**: See `docs/sdlc-workflow.md` for the full execution flow, quality gates, and artifact lifecycle
- **Agent Inventory**: See `docs/agent-inventory.md` for detailed agent specifications
- **Traceability**: See `docs/traceability-mapping.md` for requirement-to-component-to-code mapping
