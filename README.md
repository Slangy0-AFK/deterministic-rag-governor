# deterministic-rag-governor
Deterministic control plane for RAG agents. Every request passes identity, gates, cache, pre-charged spend, citation check, and hash-chained log before release. No LLM in the decision path. Baseline FP/FN rates included. Adversarial evaluation needed — the set is small and written by one author.
# Deterministic RAG Governor

Deterministic control plane for RAG agents. No LLM in the decision path.

Every request passes:
identity → noise gate → loop gate → exact cache → retrieval cache
→ pre-charged spend → RAG → citation check → release or hold
→ hash-chained log → base-60 audit cycle

**It is not:** containment, alignment, tamper-proof, credential-safe, or model-attesting.

**Baseline:** see `report.json`. Golden set runs in under a second, no LLM calls.
**Gap:** the eval set is small and written by one author. Adversarial evaluation needed.

**Run (Codespaces or local):**

**Thresholds to attack:** 90% quote overlap, 35% prose overlap, 3 loops in 300s.
**License:** MIT.
