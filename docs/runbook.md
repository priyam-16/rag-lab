# Runbook

How to deploy, run, rerun and roll back RAG Lab. Written for whoever is on call.

## Deploy (once per release)
```bash
git fetch --tags && git checkout vX.Y.Z
uv sync --frozen --no-dev        # exact versions from uv.lock; fails if lock is stale
uv run --no-sync raglab --help   # smoke test: the launcher works
```
- Offline servers: point uv at the internal package mirror (`UV_INDEX_URL=...`) or deploy the
  Docker image instead (`docker build -f infra/Dockerfile -t raglab:X.Y.Z .`).
  Note: the Dockerfile has not been test-built in CI yet; build it once locally before relying on it.
- Keep the previous release folder until the new one is verified (fast rollback).

## Run
| Task | Command |
|---|---|
| Fetch documents | `raglab download --strict` |
| Rebuild the index | `raglab ingest --config configs/prod.yaml` |
| Ask (smoke test) | `raglab ask "What is the output floor under Basel III?" --config configs/prod.yaml` |
| Serve API | `raglab serve --host 0.0.0.0 --port 8000` (or the Docker image) |

Scheduler setup: `infra/jobs/README.md`.

## When something fails
| Symptom (stderr) | Likely cause | Action |
|---|---|---|
| `AuthenticationError` | Wrong/expired API key | Fix the secret in the vault; rerun |
| `NotFoundError ... model ... does not exist or you do not have access` | Model retired or not enabled for the account | Check provider's model list; update `generation.model` |
| `RateLimitError` | Provider quota | Rerun later; for evals lower concurrency / switch tier |
| `No usable PDFs in ...` | Download failed or wrong `raw_dir` | Check the download job's sysout; fix path |
| `skipping X: identical to Y` (warning) | Same PDF twice | Remove the duplicate file |
| `no extractable text ... needs OCR` (warning) | Scanned PDF | Needs an OCR parser (planned parsing rung) |
| Qdrant connection error | `QDRANT_URL` wrong or server down | Check the URL / server; rerun |
| Local mode `lock` error | Two processes on `data/qdrant` | Use a Qdrant server in prod; never local mode |

## Roll back
1. Point the scheduler / service back to the previous release folder (or previous image tag).
2. If the index changed shape (new embedding model), re-run INGEST on the old release.
3. Record what happened in `docs/CHANGELOG.md`.
