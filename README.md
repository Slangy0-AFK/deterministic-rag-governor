[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/dougleslie00-afk/deterministic-rag-governor)
Deterministic RAG Governor is a deterministic control plane for RAG agents with no LLM in the decision path. Every request passes through a fixed, auditable pipeline: identity → noise gate → loop gate → exact cache → retrieval cache → pre-charged spend → RAG → citation check → release or hold → hash-chained log → base-60 audit cycle. Same input, same decision. It is not containment, alignment, tamper-proof, credential-safe, or model-attesting, so do not treat it as a security boundary. Quickstart: run `docker compose up -d --build` then `docker compose exec web python tests/golden_set.py --json report.json`. The golden set runs in under a second and makes no LLM calls; baseline is in `report.json`. Known gaps: the eval set is small and written by one author, and adversarial evaluation is needed before trusting it in production. Thresholds to attack: 90% quote overlap, 35% prose overlap, 3 loops in 300s. License: MIT.

**Run:**

```sh
docker compose up -d --build
docker compose exec web python tests/golden_set.py --json report.json
```

**Thresholds to attack:** 90% quote overlap, 35% prose overlap, 3 loops in 300s.
**License:** MIT.
