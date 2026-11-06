# Interview bank

Questions from drills, each with a model answer **skeleton**, the technical specifics worth naming,
and why the answer scores well. Rule for specifics: **name → why → number or trade-off.**
Only say what you can explain in two sentences; prefer what you have built.

Revision method: read the skeleton, then answer out loud without looking. Week 6 = cold mock.

---

## Q1. Behavioral — idea to production in a regulated environment
> "Tell me about a time you took an ML/AI system from idea to production in a regulated environment.
> What was the hardest non-technical problem?"

**Skeleton (STAR):** constraint → your role → technical actions → the non-technical blocker and your
tactic → measurable result.

**Draft (ARIA — verify every fact; fill brackets with real numbers):**
- *Situation:* policies and documents scattered across SharePoint, Teams, shared drives; no approved
  enterprise LLM vendor, so cloud LLMs were not allowed.
- *Task:* led design of ARIA, a semantic search + Q&A assistant running entirely inside the bank.
- *Action (technical):* Llama 3 [size] on-prem in Cloudera ML; FastAPI wrappers for data access inside
  the firewall; embeddings [model] in [vector DB]; gold Q&A set of [N] questions for measurement.
- *Action (non-technical, the hard part):* getting risk, compliance and IT to agree to a pilot. Split the
  approval into low-risk phases (read-only, no customer data first, every answer cites its source) and
  shared the evaluation method with validation **before** results.
- *Result:* [pilot approved / users / time saved / next initiative].

**Why it works:** concrete constraint, "I" actions, a specific tactic for the human problem, a result.
A wrong specific is worse than none: leave out anything you can't confirm.

---

## Q2. Debugging — pilot 95% accuracy, live 80%
> "Your extraction pilot hit 95% on 50 files but 80% in the live pilot. What happened, what do you do?"

**Skeleton:** diagnose before fixing → break errors down by segment → fix the top causes → contain risk
meanwhile → prevent recurrence.

| Step | Specifics | Why |
|---|---|---|
| Diagnose | Error breakdown by document type, scan vs digital, field, source; **PSI / KS test** on document features (page count, text density, OCR confidence) pilot vs live | Shows the input distribution shifted (same idea as credit-model monitoring) |
| Scans | OCR: Tesseract → **PaddleOCR** or **Mistral OCR 4** | Plain text extraction returns nothing for scans |
| Tables/layouts | **Docling**, or document models like **LayoutLMv3** | Keeps values attached to their labels |
| Contain | **Confidence-based routing**: low-confidence fields → human review | Holds accuracy while you fix |
| Prevent | **Stratified random sampling** of real traffic for the test set; add failures as test cases | Pilot sample was hand-picked |

---

## Q3. RAG in production — confident but wrong answers
> "Users say the assistant sometimes gives confident but wrong answers. How do you debug it?"

**Skeleton:** collect 20–30 failures → for each: were the right passages retrieved? → retrieval fix or
generation fix → every failure becomes a test case gating releases.

| Failure | Specifics | Why |
|---|---|---|
| Misses exact terms | **BM25** + dense, fused with **Reciprocal Rank Fusion (RRF, k=60)** | Vectors are weak on IDs/acronyms ("Notice 637", "CET1") |
| Right passage ranked low | **Cross-encoder reranker** (bge-reranker-v2-m3, Cohere Rerank): retrieve 20–50 → rerank to 5 | Bi-encoder embeds query and passage separately; cross-encoder reads them together — more accurate, too slow for first stage |
| Chunk lacks context | **Contextual retrieval** or **parent–child chunks** | "The ratio is 72.5%" doesn't say which ratio |
| Model ignores context | Grounded prompt + mandatory citations + **NLI-based faithfulness check** | Catches unsupported claims |
| No answer exists | Unanswerable questions in the test set; measure refusal rate | Prevents confident guessing |
| Measurement | **RAGAS / DeepEval** metrics, traces in **Langfuse / Arize Phoenix** | Repeatable, comparable |

---

## Q4. System design — bank document Q&A
> "10,000 policy documents, data can't leave the bank, 2,000 employees, answers must be auditable."

**Skeleton:** constraints → ingestion → retrieval (with access control) → generation → audit →
evaluation → scale → rollout.

| Layer | Specifics | Why |
|---|---|---|
| Parsing | **Docling** (local) + OCR fallback | Nothing leaves the bank; tables survive |
| Embeddings | **bge-m3** or **e5-large**, self-hosted | Strong open models; bge-m3 does dense + sparse, helps hybrid |
| Vector DB | **Qdrant**, **HNSW** (M=16, ef≈128), **int8 scalar quantization**, payload filter on `access_groups` | Fast, ~4x less memory, permission filter applied *during* search |
| Retrieval | Hybrid (BM25 + dense, RRF) → cross-encoder rerank | Exact policy terms + meaning |
| LLM serving | **Llama 3.x / Qwen** on **vLLM** (continuous batching, PagedAttention); **AWQ/GPTQ 4-bit** if GPUs are tight | Several times higher throughput; 2–4x less GPU memory |
| Gateway | **LiteLLM**: routing, budgets, logging | Model-agnostic, cost control |
| Guardrails | **Presidio** (PII), **Llama Guard / NeMo Guardrails** (unsafe I/O, prompt injection) | Regulators ask about both |
| Audit | Append-only logs: user, question, retrieved chunk IDs, model version, answer | Any answer can be reconstructed |
| Scale | 2,000 users is modest: ~2 GPU nodes + replicated vector DB; real risk is document freshness | Honest about where risk lies |
| Rollout | One department → measure → expand | De-risks adoption |

---

## Q5. Client conflict — "live by Friday" at 70% accuracy
> "The sponsor wants it live by Friday for a board demo. Your eval shows 70% and you think it's unsafe."

**Skeleton:** separate the underlying need (credible board demo) from the request (production) →
offer an alternative (curated demo, clearly labelled pilot, eval + plan to close the gap) → if they
insist, escalate in writing to sponsor + risk owner with numbers.

**Specific to name:** "70% ± 6% (bootstrap 95% CI, 120 questions); target 90%; most errors are table
questions, fixable with layout-aware parsing in ~2 weeks." Precise numbers make the trade-off concrete.

---

## Q6. Risk committee — "how do we know it works and stays working?"
**Skeleton:** how we measured → what we found (with uncertainty) → judge reliability → failure modes →
ongoing monitoring → human accountability. Tie it to credit-model validation practice.

| Point | Specifics | Why |
|---|---|---|
| Uncertainty | **Bootstrap CIs**; **McNemar's test** comparing two systems on the same questions | Paired data needs a paired test |
| Judge reliability | **Cohen's kappa** vs human labels; **position-bias** (swap order) and **verbosity-bias** checks | An unchecked judge is opinion |
| Adversarial | Contradictory docs, irrelevant context, **prompt injection** (garak / promptfoo suites) | Shows how it fails |
| Monitoring | Weekly sampled human review; topic drift via embedding clusters; **PSI** on input features | Mirrors credit-model monitoring |
| Gate | CI regression eval blocks release if faithfulness drops > [x] pts | A gate, not a dashboard |

---

## Q7. Permissions — the "AI leaked the layoff list" scenario
> "An internal assistant over 5M files in Drive/Slack revealed a confidential layoff list and salaries
> to a junior employee. Why did it happen and how do you fix it?"
> (Source: FDE interview reel, Glue Info, 2026-11-06.)

**Why it happened:** documents were indexed without their access rights, so retrieval returned anything
semantically similar, regardless of who asked. Vector similarity knows nothing about permissions.
It is a **permissioned-retrieval** problem, not an accuracy problem.

**Skeleton:** deny by default → carry ACLs into the index → filter *during* search → re-check the top-k
→ keep permissions in sync → output guardrail as last line → audit → test it adversarially.

| Layer | Specifics | Why |
|---|---|---|
| Classification at ingestion | Sensitivity labels (e.g. HR-restricted, board-only); highest tiers **not indexed** in a general assistant at all | Least privilege: the safest leak is data that was never indexed |
| ACLs on every chunk | Copy the source document's `allowed_users` / `allowed_groups` into each chunk's payload (and into any derived summary) | Chunks inherit their parent's permissions |
| Resolve who the user is | Permission graph (Google **Zanzibar**-style: **OpenFGA**, **SpiceDB**) or cached group memberships from the identity provider | Group membership changes; resolve it once per request (~ms) |
| Filter during search | Vector DB **payload filter** (`access_groups ∈ user_groups`) applied inside the HNSW search (Qdrant / Weaviate / Elastic support this) | Post-filtering can leak via scores and returns too few results; pre/in-filtering never retrieves forbidden chunks |
| Re-check top-k | Verify the final 5–20 documents against the source system's live permissions | Cheap (20 checks, not 5M) and catches sync lag |
| Sync | **CDC / webhooks** from Drive, Slack, SharePoint → event stream (Kafka) → update payloads | Revocations propagate in seconds; measure and state the lag |
| Output guardrail | Deterministic detectors (Presidio, regex for salary/ID patterns, sensitivity labels on cited docs) block or redact | Last line of defence, not the primary control |
| Caches | **Semantic / response caches keyed by permission set** (or per user) | A shared cache can serve one user's answer to another — a common real leak |
| Audit + test | Log user, retrieved doc IDs, decision; adversarial tests: "user without access asks for restricted content" must return refusal | Proves the control works |

**Critique of the reel's answer:** right core idea (permission-aware retrieval, event-driven sync, output
guardrail), but two things to say differently in an interview:
1. **Don't repeat "1 ms" claims.** End-to-end revocation over CDC is realistically seconds; say there is a
   consistency window and how you close it (top-k re-check against the live source).
2. **"Just remove secret files" is not wrong — it's step one.** Data classification and excluding the most
   sensitive tiers from general-purpose indexes is standard least-privilege practice; ACL filtering
   handles everything else.

**Strong closing line:** "Retrieval must be permission-aware by construction: ACLs carried into every chunk,
filtered inside the vector search, top-k re-verified live, caches keyed by permissions, and an output
guardrail as the last line — with adversarial tests proving a user can't retrieve what they can't open."

---

## Concepts: vector search at scale (drill 2026-11-03/04)

**"Search 100M vectors in 100 ms":** clarify (QPS, recall target, filters, update rate, dims) → math
(100M x 1536 x 4 B ≈ 614 GB; brute force reads it all per query → impossible) → **ANN**: HNSW (or IVF) +
**quantization** (int8 4x, binary 32x, PQ) with **re-scoring** top ~100 on full vectors + **sharding**
across nodes in parallel, replicas for QPS. Budget: embed 10–40 ms, search 5–20 ms per shard, re-score
2–10 ms → ~30–80 ms. Tune `ef_search` against a recall@10 target; watch p99; filter *during* search.

**HNSW:** layered graph — top layers are few vectors with long links ("highways"), bottom layer is all
vectors with short links ("streets"). Greedy hops toward the query, drop a layer, repeat; bottom layer
keeps `ef_search` candidates. Approximate because greedy hops can miss. Knobs: `M` (links per node),
`ef_construction` (build quality), `ef_search` (main speed/accuracy dial).

**Recall@10 vs hit@k:**
- recall@10 = share of the **exact** top-10 (brute force on a sample, plain maths, no human needed) that
  the ANN index returned. Measures the *search engine*.
- hit@k = did retrieval return the **gold page** a domain expert marked. Measures the *whole retrieval
  system*. Perfect recall@10 with poor hit@k = the embeddings, not the index, are the problem.
- Ground truth from humans (gold set, judge checks) needs quality control: two reviewers + adjudication,
  **Cohen's kappa**, spot checks, written labelling guidelines.
