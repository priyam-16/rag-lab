# 0001 — Plain-Python core pipeline; frameworks only at the edges

- Status: accepted
- Date: 2026-10-22

## Context
The project's purpose is to benchmark RAG techniques and explain them in interviews and to
clients. Every stage must be swappable, measurable on its own, and readable.

## Options considered
1. LangChain / LlamaIndex as the backbone — fast to start; abstractions hide the steps we
   want to measure; harder to debug; version churn.
2. Plain Python classes per stage, chosen by YAML config — more code to write; every step visible.

## Decision
Plain Python for `src/raglab/`. LangGraph is used only for the agentic layer (loops/branching),
and a LangChain implementation is added as one benchmark arm for comparison.

## Consequences
+ Components are small, testable offline, and easy to explain.
+ "Framework vs hand-built" becomes a measured result rather than an opinion.
− We maintain glue code ourselves. Revisit if glue exceeds the value of visibility.
