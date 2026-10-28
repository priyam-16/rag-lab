# api/ notes (loaded only when working in this folder)

- FastAPI app in `main.py`; run with `uv run raglab serve --reload`, docs at /docs.
- Request/response bodies are Pydantic models; keep them backwards compatible (the web UI depends on them).
- Provider/config errors surface as HTTP 502 with the error type; validation errors stay 422.
- CORS origins come from `CORS_ORIGINS` (comma-separated); never use "*" in prod.
- The pipeline is built once per process (`lru_cache`); don't construct it per request.
