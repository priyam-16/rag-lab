---
name: release
description: Prepare and verify a release - tests, version bump, changelog note, tag, deploy checklist. Use when asked to ship, release, tag or deploy.
---

# Release checklist

1. `git status` clean; on `main`; `git pull` done.
2. `uv lock --check` (lockfile matches pyproject) and `uv run poe test` green.
3. Optional, costs a little: `uv run poe integration` (real API smoke tests).
4. Bump `version` in `pyproject.toml` (semver: breaking.feature.fix), then `uv lock`.
5. Add a short entry to `docs/CHANGELOG.md`: what changed, any config/ops impact.
6. Commit `Release vX.Y.Z`, tag `git tag vX.Y.Z`, push with tags (only when the owner asks).
7. Deploy: follow `docs/runbook.md` (build once with `uv sync --frozen --no-dev`, smoke test,
   then switch). Never install packages at job run time.
8. Post-deploy: `raglab ask` smoke question; check logs; confirm exit codes in the scheduler.
