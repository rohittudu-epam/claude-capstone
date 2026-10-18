# Branching Strategy

LinkNote uses **GitHub Flow**: one long-lived branch (`main`) and short-lived topic branches. It fits a small team, a single deployable unit (Docker Compose), and a CI pipeline that gates every merge.

## Branches

| Branch | Purpose | Lifetime | Protected |
|--------|---------|----------|-----------|
| `main` | Always releasable; CI green | Permanent | Yes |
| `feature/<scope>` | New functionality | Until merged | No |
| `fix/<scope>` | Bug fixes | Until merged | No |
| `docs/<scope>` | Documentation-only changes | Until merged | No |
| `chore/<scope>` | Tooling, CI, dependencies | Until merged | No |
| `hotfix/<scope>` | Urgent production fix, branched from the latest release tag | Until merged | No |

## Naming

- Lowercase, hyphen-separated: `feature/impl-8-note-crud`.
- Reference the implementation-plan task where one exists (`impl-N`), otherwise use a short descriptive scope.
- SDLC pipeline stage work: `feature/<scope>` for implementation, `docs/<artifact>` for stage artifacts such as `docs/requirements`.

## Workflow

1. Branch from an up-to-date `main`.
2. Commit small, logical units (see commit format below).
3. Push and open a pull request into `main`. Draft PRs are fine for early feedback.
4. CI must pass (backend lint/type/tests, frontend lint/type/tests, Compose validation and build).
5. At least one approving review; all review conversations resolved.
6. Squash-merge into `main`, then delete the topic branch.

Keep branches under about 3 days of work. Split large tasks (for example, IMPL-13) into several branches rather than letting one drift.

## Mapping to the Implementation Plan

| Phase | Tasks | Suggested branches |
|-------|-------|--------------------|
| 1 Foundation | IMPL-1 to IMPL-4 | `feature/phase-1-foundation` |
| 2 Backend services | IMPL-5 to IMPL-12 | One branch per task or closely related pair, e.g. `feature/impl-5-auth-registration`, `feature/impl-8-note-crud` |
| 3 Link suggestions and graph | IMPL-13 to IMPL-17 | One branch per task |
| 4 Frontend and integration | IMPL-18 to IMPL-28 | One branch per task |

Tasks that depend on an unmerged branch should wait for that merge, or branch from it explicitly and rebase onto `main` once it lands.

## Commit Messages

Conventional Commits:

```
<type>(<scope>): <summary in imperative mood>

<optional body explaining why>
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`, `perf`. Scope is optional and usually the service name (`auth`, `note`, `link`, `graph`, `frontend`).

Examples: `feat(note): add tag filtering to note listing`, `ci: validate compose file on pull requests`.

## Protection Rules for `main`

Configure these on the remote (they cannot be set from the repository):

- Require a pull request before merging, with 1 approval.
- Require status checks: `backend`, `frontend`, `compose` (from `.github/workflows/ci.yml`), with branches up to date.
- Require conversation resolution.
- Block force pushes and branch deletion.
- Restrict merge method to squash.

## Releases

- Tag releases on `main` with semantic versions: `v0.1.0` for the first MVP release.
- Hotfixes branch from the tag, merge to `main` via PR, and are re-tagged with a patch bump.
- `docs/CHANGELOG.md` is updated in the PR that precedes a release tag.

## Rules of Thumb

- Never commit directly to `main`.
- Never force-push a shared branch; rebase only your own unmerged topic branches.
- Never commit `.env` or secrets; only `.env.example`.
- Database migrations: one Alembic revision per branch, and rebase to resolve revision-chain conflicts before merge.
