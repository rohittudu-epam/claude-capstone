# Agent–Skill–Tool Mapping

## Skill Assignments

| Skill | Primary Users | Purpose |
|-------|--------------|---------|
| `sdlc-workflow` | User → Orchestrator | Entry point for full pipeline |
| `structured-review` | Design Review Agent, Code Review Agent | Reusable review methodology |
| `artifact-validation` | Orchestrator | Validates stage outputs before advancing |
| `test-and-verify` | Verification Agent | Test generation and execution procedure |
| `pr-assembly` | PR Agent | PR description assembly with 5 required sections |

## Tool Assignments

| Tool | Agents | Purpose |
|------|--------|---------|
| `Read` | All | Read project files |
| `Write` | All except Orchestrator (delegates) | Create new files |
| `Edit` | Design Review, Implementation, Code Review, Verification | Modify existing files |
| `Bash` | Implementation, Verification, PR, Review | Run commands (build, test, git, gh) |
| `TodoRead`/`TodoWrite` | Orchestrator | Track workflow tasks |

## Script Assignments

| Script | Used By | Purpose |
|--------|---------|---------|
| `.claude/scripts/validate-artifacts.sh` | Orchestrator, Verification Agent | Validate all pipeline artifacts exist and have required content |
| `.claude/scripts/run-tests.sh` | Verification Agent | Detect project type and run appropriate test suite |

## External Tool Dependencies

| Tool | Required By | Status | Installation |
|------|------------|--------|-------------|
| `git` | All agents (commit) | Expected available | Pre-installed |
| `gh` (GitHub CLI) | PR Agent | Optional | `brew install gh` or [cli.github.com](https://cli.github.com) |
| `npm` | Implementation, Verification (Node.js projects) | Conditional | Required for Node.js projects |
| `python`/`pip` | Implementation, Verification (Python projects) | Conditional | Required for Python projects |
| `go` | Implementation, Verification (Go projects) | Conditional | Required for Go projects |
