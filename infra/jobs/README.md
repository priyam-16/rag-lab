# Scheduler jobs (Control-M, cron, Airflow, Windows Task Scheduler)

The rule: **build once at deploy time, then jobs only run.** Never activate a venv and never
install packages inside a job.

## The command every job uses
```bash
/opt/raglab/.venv/bin/raglab <subcommand> --config /opt/raglab/configs/prod.yaml
```
- Full path to the launcher → always the right Python, no `activate`, no PATH surprises.
- Exit code `0` = OK, `1` = failed (full traceback in stderr), `130` = interrupted.
- Logs go to stdout/stderr with timestamps → captured in the job's sysout.

Conda equivalent (if the server standardises on conda):
```bash
/opt/conda/envs/raglab/bin/python -m raglab.cli ingest --config /opt/raglab/configs/prod.yaml
```

## Job chain
```
RAGLAB_DOWNLOAD ──► RAGLAB_INGEST ──► RAGLAB_EVAL ──► RAGLAB_PUBLISH
  daily 02:00        on OK             on OK           manual approval
  raglab download    raglab ingest     raglab evaluate (switch API to the
  --strict                             (spec 001)       new collection)
```
- One job per step: a failure at INGEST is rerun from INGEST, not from the start.
- Mark jobs as non-concurrent (one instance at a time): ingest recreates its collection.
- `download --strict` fails the job if any document needs a manual save, instead of
  silently indexing an incomplete corpus.

## Environment variables per job (from the vault / job definition, never a .env file)
| Variable | Needed by |
|---|---|
| `OPENAI_API_KEY` (or approved embedding endpoint key) | ingest, ask, evaluate |
| `GROQ_API_KEY` / `ANTHROPIC_API_KEY` (or approved LLM endpoint) | ask, evaluate |
| `QDRANT_URL`, `QDRANT_API_KEY` | ingest, ask, evaluate, serve |

## Example Control-M job (conceptual fields)
| Field | Value |
|---|---|
| Job name | `RAGLAB_INGEST` |
| Command | `/opt/raglab/.venv/bin/raglab ingest --config /opt/raglab/configs/prod.yaml` |
| Run as | service account `raglab` |
| In-condition | `RAGLAB_DOWNLOAD-ENDED-OK` |
| Out-condition | `RAGLAB_INGEST-ENDED-OK` |
| On failure | notify owner; rerun allowed (ingest is idempotent: it rebuilds the collection) |
| Max runs at once | 1 |
