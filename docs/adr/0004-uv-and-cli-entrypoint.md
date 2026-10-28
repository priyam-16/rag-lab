# 0004 — uv for environments; a single `raglab` CLI as the entry point

- Status: accepted
- Date: 2026-10-28

## Context
The project must run identically on a Windows laptop, CI, a Docker image, and scheduler-driven
servers (Control-M), and serve as a template for office projects with locked-down machines.

## Options considered
1. pip + venv + requirements.txt + loose scripts — familiar; no lockfile; needs activation;
   scripts depend on the current folder and PATH.
2. conda — handles non-Python libraries (CUDA); slower; no exact lock by default; licensing
   constraints on the default channel for larger organisations.
3. uv + `uv.lock` + `[project.scripts]` launcher — fast, exact versions everywhere, no activation.

## Decision
uv with a committed lockfile; one `raglab` command with subcommands; tasks via poe (a pip package,
so no extra system tools are required). Schedulers call the launcher by absolute path.

## Consequences
+ Reproducible installs (`uv sync --frozen`), no activation, consistent exit codes and logs.
− Team must learn uv; conda remains the better choice for GPU-specific native stacks.
