# Pull Request: Fix Ruff Target Version

## PR Details

**Title:** fix: correct ruff target-version from py314 to py312

**Base Branch:** main  
**Head Branch:** fix/ruff-target-version

**Branch URL:** https://github.com/rohittudu-epam/claude-capstone/compare/main...fix/ruff-target-version

---

## Summary

Fixes CI failure caused by invalid Python version in ruff configuration.

## Problem

The backend CI was failing with a confusing ruff format error. The root cause was `backend/ruff.toml` specifying `target-version = "py314"`, but Python 3.14 does not exist yet (latest stable is Python 3.13). This caused ruff to behave incorrectly and suggest invalid Python 2 syntax transformations.

## Changes Made

- **backend/ruff.toml**: Changed `target-version` from `"py314"` to `"py312"` (stable Python version)

## Test Evidence

✅ Tested locally with `ruff format --check` - all files now pass  
✅ The exception handling syntax in `auth-service/auth_service/routes.py` is correctly validated

## Impact

- Fixes all backend format check failures in CI
- Ensures ruff uses correct Python syntax rules
- No functional code changes, only configuration fix

## Reviewer Checklist

- [ ] Verify `backend/ruff.toml` has `target-version = "py312"`
- [ ] Confirm CI passes (backend format check should succeed)
- [ ] Check that no other ruff configuration files exist

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
