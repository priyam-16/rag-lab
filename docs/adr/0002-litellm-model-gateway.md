# 0002 — All model calls go through LiteLLM

- Status: accepted
- Date: 2026-10-22

## Context
We compare Claude, GPT, open models on Groq and local models. Clients (esp. banks) may only be
allowed on-prem or specific approved endpoints.

## Options considered
1. Each provider's own SDK — native features; N integrations, N response formats.
2. LiteLLM — one interface and response shape, built-in cost table; one more dependency,
   occasionally lags new provider features.

## Decision
Use LiteLLM for completions and hosted embeddings. Model = a config string (`groq/...`, `anthropic/...`).

## Consequences
+ Switching or adding a model is a config change; cost per answer comes for free.
+ Vendor-neutral by design: an on-prem endpoint is just another model string.
− Cost table can be missing for new/free models (we record `cost=None`, not 0).
