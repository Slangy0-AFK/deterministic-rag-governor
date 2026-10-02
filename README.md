[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/dougleslie00-afk/deterministic-rag-governor)

# Deterministic RAG Governor

Deterministic control plane for RAG agents. No LLM in the decision path.

Every request passes:
identity → noise gate → loop gate → exact cache → retrieval cache
→ pre-charged spend → RAG → citation check → release or hold
→ hash-chained log → base-60 audit cycle

The governor owns policy, spend accounting, caching, and audit decisions. Retrieval and generation remain supplied by a small adapter; the governor does not provide an LLM, vector store, document-ingestion pipeline, or tenant isolation.

## Configure

Use Python 3.11 and copy `.env.example` to `.env`. Set `GOVERNOR_OPERATOR_KEY` to a long random value, then point `GOVERNOR_RAG_ADAPTER` at a factory in an importable Python module. The factory must return an object with synchronous `retrieve(query) -> list[str]` and `generate(query, chunks) -> str` methods. For cache reuse, expose a stable string `version` property or zero-argument method that changes whenever the source corpus changes. Without it, requests bypass both caches. Adapter modules and their dependencies must be included in the image for Docker deployments.

## Run

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -p 'test_*.py'
python tests/golden_set.py --json report.json
docker compose up --build -d
```

The service is bound to `127.0.0.1:8000`; SQLite and adapter data persist in the `governor_data` volume. `/health` reports audit-chain integrity and adapter configuration. `/ready` returns 503 until an adapter is configured and the audit chain verifies.

Register and fund an agent with the operator key, then submit a governed request:

```sh
curl -X POST http://127.0.0.1:8000/admin/agent \
	-H "X-Operator-Key: $GOVERNOR_OPERATOR_KEY" \
	-H 'Content-Type: application/json' -d '{"agent_id":"lab-agent"}'
curl -X POST http://127.0.0.1:8000/admin/agent/credit \
	-H "X-Operator-Key: $GOVERNOR_OPERATOR_KEY" \
	-H 'Content-Type: application/json' -d '{"agent_id":"lab-agent","amount":10}'
curl -X POST http://127.0.0.1:8000/govern \
	-H 'Content-Type: application/json' \
	-d '{"agent_id":"lab-agent","query":"Summarize the supplied source"}'
```

Requests fail closed when no RAG adapter is configured. The HTTP suite uses a fake adapter and requires no model or vector database. Generation failures consume the precharged unit and are written as holds; retrieval failures are also audited but are not charged. Golden-set checks pass/fail the implemented gates, not model quality: the set is small, author-written, and must be expanded with independent adversarial cases before relying on its metrics. Thresholds to attack include 90% quote overlap, 35% prose overlap, and three requests per agent in 300 seconds.

## Production Limits

The operator key is a shared admin credential, SQLite is suitable for a small single-node deployment, and the hash chain is tamper-evident only while its database is trusted. Put the service behind authenticated TLS, protect backups and adapter credentials, and use an external database/audit sink before multi-node or high-volume deployment. This is not containment, alignment, tamper-proof, credential-safe, or model-attesting.

**Baseline:** see `report.json`. **License:** MIT.
