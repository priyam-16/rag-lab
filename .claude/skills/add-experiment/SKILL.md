---
name: add-experiment
description: Add a new benchmark experiment (a config that changes ONE setting, e.g. retriever, chunker, parser, model) and run it. Use when asked to try or compare a RAG technique.
---

# Add an experiment

An experiment = one YAML in `configs/` that differs from its parent in exactly ONE setting.
That is what keeps comparisons honest.

1. Pick the parent (usually `configs/default.yaml` or the current best).
2. Copy it to `configs/<short_name>.yaml`. Change:
   - `name:` → `<short_name>`
   - the ONE setting under test
   - `vector_store.collection:` → a new name **only if** parsing, chunking or embedding changed
     (anything that changes what is stored needs its own index)
3. If the setting needs code that doesn't exist yet, use the `add-component` skill first.
4. Re-index if the collection changed: `uv run raglab ingest --config configs/<short_name>.yaml`
5. Smoke-check: `uv run raglab ask "What is the output floor under Basel III?" --config configs/<short_name>.yaml`
6. Evaluate (once the eval harness exists): see the `run-eval` skill.
7. Record in `docs/LEARNING.md`: one table row (config, metric deltas vs parent, latency, cost) + 2 lines on why.

Do not change two settings in one experiment. If tempted, make two experiments.
