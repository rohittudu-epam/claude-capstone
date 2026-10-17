---
name: pr-assembly
description: Assembles a complete PR description with all 5 required sections from SDLC pipeline artifacts
version: 2.0.0
invocation: model
related_agents:
  - pr-agent
---

# PR Assembly Procedure

## When to Use

Use this skill when creating the final Pull Request description. Used by the PR Agent (Stage 8).

## Required PR Sections

Every PR description MUST contain these 5 sections. No section may be omitted.

### Section 1: Summary
- 2-3 sentences describing what was built and why.
- Reference the original user story or business motivation.
- Example: "This PR implements automated documentation sync that monitors repository changes and regenerates API documentation. It was built to address the user story requiring real-time documentation updates when code changes are merged."

### Section 2: Changes Made
- Bulleted list of every file added or modified.
- Each bullet must include the file path and a brief reason.
- Group by category if there are many files (docs, source, tests, config).

### Section 3: Test Evidence
- Paste the actual test output from the verification stage.
- Include pass/fail counts.
- Do NOT fabricate results — use real output from `verification-report.md`.
- If tests were not run, state this explicitly.

### Section 4: Known Limitations
- List anything that is out of scope or not implemented.
- List any "Not Found" items or unavailable integrations.
- List assumptions that could not be verified.
- If there are no limitations, state "None identified."

### Section 5: Reviewer Checklist
- A tick-list (using `- [ ]`) for the reviewer.
- Must include checks for:
  - Requirements completeness
  - Architecture adherence
  - Code review clearance
  - Test passage
  - Security (no secrets in code)
  - Error handling coverage
  - Changelog updated

## Assembly Steps

1. Read all pipeline artifacts.
2. Extract relevant content for each section.
3. Write `pr-description.md` with all 5 sections.
4. Write or update `CHANGELOG.md` following Keep a Changelog conventions.
5. Validate that no section is empty or missing (use the artifact-validation skill).
6. Commit all changes and create the PR (via `gh` CLI if available, otherwise provide manual instructions).