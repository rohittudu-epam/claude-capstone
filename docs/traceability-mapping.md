# Traceability Mapping

## Source Document → Implementation

This mapping traces every responsibility from the source document (GitHub Copilot Capstone Project — Agentic SDLC) to its implementation in the Claude ecosystem.

### Step 1: Requirements

| Source Requirement | Implementation | File |
|-------------------|---------------|------|
| Read a new User Story from JIRA/Confluence/word document | Requirements Agent reads from file or inline text | `.claude/agents/requirements-agent.md` §1 |
| Let Copilot ask or clarify questions and let user respond | Requirements Agent conducts interactive clarification rounds (max 2) | `.claude/agents/requirements-agent.md` §2 |
| Capture final requirements in docs/requirements.md | Requirements Agent generates and writes `docs/requirements.md` | `.claude/agents/requirements-agent.md` §3 |
| Commit the file | Requirements Agent runs `git add` and `git commit` | `.claude/agents/requirements-agent.md` §5 |

### Step 2: Architecture

| Source Requirement | Implementation | File |
|-------------------|---------------|------|
| Ask for architecture recommendation based on docs/requirements.md | Architecture Agent reads `docs/requirements.md` and proposes design | `.claude/agents/architecture-agent.md` §1-2 |
| Document proposed architecture in docs/architecture.md | Architecture Agent writes `docs/architecture.md` | `.claude/agents/architecture-agent.md` §3 |
| Identify key components and their responsibilities | Architecture Agent includes Components section with responsibilities | `.claude/agents/architecture-agent.md` §2-3 |

### Step 3: Design Review

| Source Requirement | Implementation | File |
|-------------------|---------------|------|
| Share docs/architecture.md and identify risks and gaps | Design Review Agent evaluates across 9 dimensions | `.claude/agents/design-review-agent.md` §2 |
| Document review findings and agreed decisions in docs/design-review.md | Design Review Agent writes `docs/design-review.md` | `.claude/agents/design-review-agent.md` §3 |
| Update docs/architecture.md if issues found | Design Review Agent edits `docs/architecture.md` for Critical/High findings | `.claude/agents/design-review-agent.md` §4 |

### Step 4: Implementation Planning

| Source Requirement | Implementation | File |
|-------------------|---------------|------|
| Generate task breakdown from docs/architecture.md | Impl Planning Agent decomposes architecture into tasks | `.claude/agents/impl-planning-agent.md` §2 |
| Document plan in docs/impl-plan.md ordered by dependency | Impl Planning Agent writes `docs/impl-plan.md` with dependency ordering | `.claude/agents/impl-planning-agent.md` §3-4 |
| Identify blocked tasks | Impl Planning Agent includes Blocked Tasks table | `.claude/agents/impl-planning-agent.md` §3-4 |

### Step 5: Implementation

| Source Requirement | Implementation | File |
|-------------------|---------------|------|
| Implement changes suggested and approved by human in loop | Implementation Agent presents approach, waits for approval, then implements | `.claude/agents/implementation-agent.md` §2-3 |

### Step 6: Review

| Source Requirement | Implementation | File |
|-------------------|---------------|------|
| Correctness review | Code Review Agent §2 Area 1 | `.claude/agents/review-agent.md` |
| Security review | Code Review Agent §2 Area 2 | `.claude/agents/review-agent.md` |
| Error Handling review | Code Review Agent §2 Area 3 | `.claude/agents/review-agent.md` |
| Test Coverage review | Code Review Agent §2 Area 4 | `.claude/agents/review-agent.md` |
| Code Clarity review | Code Review Agent §2 Area 5 | `.claude/agents/review-agent.md` |
| DRY Principle review | Code Review Agent §2 Area 6 | `.claude/agents/review-agent.md` |
| Dependency Safety review | Code Review Agent §2 Area 7 | `.claude/agents/review-agent.md` |

### Step 7: Verify

| Source Requirement | Implementation | File |
|-------------------|---------------|------|
| Generate and run unit + integration tests | Verification Agent generates and executes both test types | `.claude/agents/verification-agent.md` §2-4 |
| Content quality check | Verification Agent §5 | `.claude/agents/verification-agent.md` |

### Step 8: PR

| Source Requirement | Implementation | File |
|-------------------|---------------|------|
| Summary — 2-3 sentence overview | PR Agent §2 Section 1 | `.claude/agents/pr-agent.md` |
| Changes Made — bulleted list of files | PR Agent §2 Section 2 | `.claude/agents/pr-agent.md` |
| Test Evidence — test output or CI link | PR Agent §2 Section 3 | `.claude/agents/pr-agent.md` |
| Known Limitations | PR Agent §2 Section 4 | `.claude/agents/pr-agent.md` |
| Reviewer Checklist | PR Agent §2 Section 5 | `.claude/agents/pr-agent.md` |
| Changelog entry | PR Agent §3 | `.claude/agents/pr-agent.md` |

### Orchestration (Inferred — not explicitly an agent in source but required for coordination)

| Responsibility | Implementation | File |
|---------------|---------------|------|
| Sequential stage execution | Orchestrator enforces strict ordering | `.claude/agents/orchestrator.md` |
| Quality gate enforcement | Orchestrator validates outputs before advancing | `.claude/agents/orchestrator.md` §Per-Stage |
| Failure handling and retry | Orchestrator retries up to 2 times, then BLOCKED | `.claude/agents/orchestrator.md` §Failure |
| Human approval gates | Orchestrator pauses for approval at stages 1 and 5 | `.claude/agents/orchestrator.md` §Per-Stage 5 |
| Completion reporting | Orchestrator generates summary report | `.claude/agents/orchestrator.md` §Completion |

## Coverage Assessment

| Source Step | Fully Covered | Notes |
|------------|:------------:|-------|
| Step 1: Requirements | ✅ | |
| Step 2: Architecture | ✅ | |
| Step 3: Design Review | ✅ | |
| Step 4: Implementation Planning | ✅ | |
| Step 5: Implementation | ✅ | Source doc lists "GitHub Copilot features to use" but the list is empty — no gap |
| Step 6: Review | ✅ | All 7 review areas covered |
| Step 7: Verify | ✅ | |
| Step 8: PR | ✅ | All 5 required sections covered |
| Orchestration | ✅ | Inferred — required for pipeline control |

**100% of source-documented responsibilities are traced to generated agents.**
