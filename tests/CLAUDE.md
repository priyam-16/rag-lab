# tests/ notes (loaded only when working in this folder)

- `unit/`: offline and fast. Use `HashEmbedder`, `make_client(None, None, None)` (in-memory Qdrant),
  tiny `Page`/`Chunk` fixtures, and `monkeypatch` for LLM calls. No network, no API keys, ever.
- `integration/`: real providers; every test has `pytest.mark.integration` and skips if its key is missing.
- Name tests after behaviour: `test_<what>_<expected>`.
- Run: `uv run poe unit` (default) · `uv run poe integration` (explicit, costs a little).
