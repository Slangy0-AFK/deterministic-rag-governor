[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/dougleslie00-afk/deterministic-rag-governor)

# Deterministic RAG Governor

Deterministic control plane for RAG agents. No LLM in the decision path.

Every request passes:
identity → noise gate → loop gate → exact cache → retrieval cache
→ pre-charged spend → RAG → citation check → release or hold
→ hash-chained log → base-60 audit cycle

**It is not:** containment, alignment, tamper-proof, credential-safe, or model-attesting.

**Baseline:** see `report.json`. Golden set runs in under a second, no LLM calls.
**Gap:** the eval set is small and written by one author. Adversarial evaluation needed.

**Run:**

```sh
docker compose up -d --build
docker compose exec web python tests/golden_set.py --json report.json
```

**Thresholds to attack:** 90% quote overlap, 35% prose overlap, 3 loops in 300s.
**License:** MIT.
