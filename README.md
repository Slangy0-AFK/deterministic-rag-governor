# Deterministic RAG Governor

Deterministic policy enforcement and audit for retrieval-augmented generation
(RAG) agents. The governor has no LLM in its decision path. It sits between an
agent/model stack and the user-facing response.

Every request passes through:

`identity -> noise gate -> loop gate -> exact cache -> retrieval cache ->
pre-charged spend -> RAG -> citation check -> release or hold -> hash-chained
log`

## What it helps with

- Model-agnostic integration for agents and model providers.
- Predictable identity, rate, spend, citation, caching, and audit controls.
- Reproducible evaluations and regression testing.
- Blocking answers that are not sufficiently supported by supplied sources.

## What it does not solve

- It is not containment, alignment, tamper-proof, credential-safe, or
	model-attesting.
- The current HTTP hook receives the model output after generation, so it does
	not prevent sensitive data exposure or wasted model inference beforehand.
- Citation overlap is not the same as factual correctness. A model can quote a
	source accurately and still misinterpret it.
- Caller-supplied model and agent identifiers are not cryptographic attestation.

Use this as a deterministic governance boundary inside a broader security,
privacy, and adversarial-evaluation architecture.

## How to run

Set an operator key before starting the service:

```sh
printf 'GOVERNOR_OPERATOR_KEY=change-me\n' > .env
docker compose up -d --build
```

The compose stack starts FastAPI, Chroma persistence, and Ollama. On first
startup the `ollama-models` service downloads `llama3.2` and
`nomic-embed-text`; override `RAG_MODEL` or `RAG_EMBEDDING_MODEL` in `.env` to
use different Ollama models.

Run the deterministic golden set:

```sh
docker compose exec web python tests/golden_set.py --json report.json
```

Run the HTTP hook tests locally:

```sh
python -m unittest tests.test_api_hook -v
```

Run one model through the governor:

```sh
MODEL_PROVIDER=openai \
MODEL_ID=gpt-4o-mini \
MODEL_API_KEY=your-api-key \
npm run test:model
```

`test:model` works with OpenAI-compatible chat-completions providers. Supported
provider aliases include `openai`, `groq`, `together`, `openrouter`, and
`ollama`. For any other provider, set `MODEL_PROVIDER=custom` and provide its
compatible endpoint with `MODEL_BASE_URL`:

```sh
MODEL_PROVIDER=custom \
MODEL_BASE_URL=https://your-provider.example/v1/chat/completions \
MODEL_ID=your-model-id \
MODEL_API_KEY=your-api-key \
npm run test:model
```

Optional inputs are `MODEL_QUERY`, `MODEL_SOURCE`, and `MODEL_AGENT_ID`. The API
key is read from the environment and is never printed. Native APIs that do not
implement the OpenAI-compatible chat-completions request and response shape
need a provider adapter before they can be used.

## How to use the universal hook

Any agent or model provider can submit its retrieval context and generated
answer to `POST /govern`. Register the agent first:

```sh
curl -X POST http://localhost:8000/admin/agent \
	-H 'content-type: application/json' \
	-H 'x-operator-key: change-me' \
	-d '{"agent_id":"demo-agent"}'

curl -X POST http://localhost:8000/govern \
	-H 'content-type: application/json' \
	-d '{
		"agent_id":"demo-agent",
		"query":"explain the audit trail",
		"source_chunks":["The control plane records every request in a hash chained audit log."],
		"answer":"The control plane records every request in a hash chained audit log."
	}'
```

The caller owns retrieval and generation. The governor applies its deterministic
controls to the submitted request and answer.

## Live RAG API

Register an agent with spend, ingest source documents, and query the real
Chroma/Ollama pipeline:

```sh
curl -X POST http://localhost:8000/admin/agent \
	-H 'content-type: application/json' \
	-H 'x-operator-key: change-me' \
	-d '{"agent_id":"rag-demo","initial_balance":10}'

curl -X POST http://localhost:8000/rag/ingest \
	-H 'content-type: application/json' \
	-H 'x-operator-key: change-me' \
	-d '{"documents":["The archive retention period is seven years."]}'

curl -X POST http://localhost:8000/rag/query \
	-H 'content-type: application/json' \
	-d '{"agent_id":"rag-demo","query":"What is the archive retention period?"}'
```

The query endpoint performs embedding-based retrieval and model generation, then
sends both through the same deterministic governor path as `/govern`. The
opt-in live integration test requires the stack to be running:

```sh
RUN_LIVE_RAG=1 python -m unittest tests.test_live_rag -v
```

## Expected results

For the valid example above, the response is similar to:

```json
{
	"released": true,
	"answer": "The control plane records every request in a hash chained audit log.",
	"source": "rag"
}
```

An unrelated answer using the same source is held:

```json
{
	"released": false,
	"answer": "This answer is unrelated to the supplied source.",
	"reason": "citation_check"
}
```

Other expected decisions include:

| Condition | Decision |
| --- | --- |
| Agent is not registered or inactive | `released: false`, `reason: identity` |
| Query has too little signal | `released: false`, `reason: noise_gate` |
| Fourth request in 300 seconds | `released: false`, `reason: loop_gate` |
| Agent balance is below one unit | `released: false`, `reason: precharged_spend` |
| Audit chain is valid | `GET /health` returns `chain_valid: true` |

## Baseline

The golden set currently has 27 cases with zero false positives and zero false
negatives. Its thresholds are 90% quote overlap, 35% prose overlap, and three
requests per agent in 300 seconds. The evaluation set is small and written by
one author, so adversarial evaluation is still required.

License: MIT.
