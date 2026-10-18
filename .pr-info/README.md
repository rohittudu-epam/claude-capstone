# PR Documentation Directory

This directory contains Pull Request descriptions and related documentation for local reference only. These files are excluded from git commits via `.gitignore`.

## Purpose

When creating Pull Requests, the PR descriptions are saved here for:
- **Quick Reference** - Easy access to PR content without going to GitHub
- **Template Reuse** - Reference for future PR descriptions
- **Documentation** - Record of what each PR contains
- **Offline Access** - View PR details without internet connection

## Naming Convention

PR description files follow this pattern:
- `PR-<short-description>.md` - Main PR description file

Examples:
- `PR-fix-ruff-config.md`
- `PR-fix-type-annotations.md`
- `PR-update-readme.md`

## Usage for Claude Code

When creating a PR description, save it to `.pr-info/PR-<descriptive-name>.md` instead of the project root.

## Git Ignore

This entire directory is excluded from git via:
```gitignore
# PR documentation (local reference only)
.pr-info/
```

## Current Files

This directory contains PR descriptions for:
1. **PR-fix-ruff-config.md** - Ruff configuration Python version fix
2. **PR-fix-type-annotations.md** - Type annotation and ruff linting fixes
3. **PR-update-readme.md** - Comprehensive README documentation update

## Creating Pull Requests

To create a PR from these descriptions:

1. Navigate to the comparison URL in the PR file
2. Click "Create pull request"
3. Copy the title from the PR file
4. Copy the description from the PR file body
5. Submit the PR

All PR creation steps are documented in each individual PR file.
