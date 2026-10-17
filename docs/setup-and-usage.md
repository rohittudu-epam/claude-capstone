# Setup and Usage Guide

## Prerequisites

- **Claude Code** installed and configured.
- **Git** installed and repository initialized.
- **Language-specific tooling** for your project (Node.js/npm, Python/pip, Go, etc.).
- **GitHub CLI** (`gh`) — optional, used for automated PR creation.

## Setup

### 1. Clone or Initialize Repository

```bash
git init my-project
cd my-project
```

### 2. Copy the Agent Ecosystem

Ensure the following structure exists in your repository:

```
.claude/
├── agents/
│   ├── orchestrator.md
│   ├── requirements-agent.md
│   ├── architecture-agent.md
│   ├── design-review-agent.md
│   ├── impl-planning-agent.md
│   ├── implementation-agent.md
│   ├── review-agent.md
│   ├── verification-agent.md
│   └── pr-agent.md
├── skills/
│   ├── sdlc-workflow/SKILL.md
│   ├── structured-review/SKILL.md
│   ├── artifact-validation/SKILL.md
│   ├── test-and-verify/SKILL.md
│   └── pr-assembly/SKILL.md
├── scripts/
│   ├── validate-artifacts.sh
│   └── run-tests.sh
└── settings.json
```

### 3. Make Scripts Executable

```bash
chmod +x .claude/scripts/*.sh
```

### 4. Prepare Your User Story

Create a file with your user story, e.g., `user-story.md`:

```markdown
# User Story

As a [role], I want [capability] so that [benefit].

## Acceptance Criteria
- [Criterion 1]
- [Criterion 2]
```

## Usage

### Running the Full SDLC Pipeline

In Claude Code, use the SDLC workflow skill:

> "Run the full SDLC pipeline for the user story in user-story.md"

Or reference the orchestrator directly:

> "Load the orchestrator agent from .claude/agents/orchestrator.md and execute the SDLC pipeline for my user story."

### Running a Specific Stage

To run just one stage (e.g., if resuming):

> "Load the requirements agent from .claude/agents/requirements-agent.md and gather requirements from user-story.md"

### Resuming an Interrupted Pipeline

If the pipeline was interrupted:

> "Resume the SDLC pipeline from where it stopped. Check workflow-state.json for the current state."

### Validating Artifacts

Run the validation script to check all pipeline outputs:

```bash
.claude/scripts/validate-artifacts.sh
```

## Expected Outputs

After a complete pipeline run, your repository will contain:

| File | Description |
|------|-------------|
| `requirements.md` | Functional and non-functional requirements |
| `architecture.md` | System architecture with components and technology choices |
| `design-review.md` | Design review findings and decisions |
| `impl-plan.md` | Prioritized implementation task list |
| `src/` (or similar) | Implementation source code |
| `tests/` | Unit and integration tests |
| `code-review.md` | Code review findings across 7 areas |
| `verification-report.md` | Test results and quality assessment |
| `pr-description.md` | Complete PR description with all 5 sections |
| `CHANGELOG.md` | Project changelog |
| `workflow-state.json` | Pipeline execution state |

## Troubleshooting

| Issue | Solution |
|-------|---------|
| Agent file not found | Verify `.claude/agents/` directory exists with all agent files |
| Stage stuck on BLOCKED | Check `workflow-state.json` for the notes field explaining why |
| Tests not running | Ensure the appropriate test runner is installed for your project type |
| PR not created | Install GitHub CLI (`gh`) and authenticate with `gh auth login` |
| Git commit fails | Ensure git is initialized and you have write permissions |
