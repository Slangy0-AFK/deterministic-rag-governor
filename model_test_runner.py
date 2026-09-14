#!/usr/bin/env python3
"""Run one user-selected chat model through the governor."""

from __future__ import annotations

import json
import os
import sys
from urllib import error, request

import governor


PROVIDER_URLS = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "together": "https://api.together.xyz/v1/chat/completions",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
    "ollama": "http://localhost:11434/v1/chat/completions",
}


def _setting(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def model_completion(query: str, source_chunks: list[str]) -> str:
    """Call any provider exposing the OpenAI-compatible chat completions API."""
    provider = _setting("MODEL_PROVIDER", "custom").lower()
    model_id = _setting("MODEL_ID")
    api_key = _setting("MODEL_API_KEY")
    endpoint = _setting("MODEL_BASE_URL") or PROVIDER_URLS.get(provider, "")
    if not model_id:
        raise ValueError("MODEL_ID is required")
    if not endpoint:
        raise ValueError("MODEL_BASE_URL is required for custom providers")

    prompt = "\n\n".join(source_chunks)
    payload = {
        "model": model_id,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": "Answer only from the supplied sources. If they do not help, say you cannot answer from the supplied sources.",
            },
            {
                "role": "user",
                "content": f"Sources:\n{prompt}\n\nQuestion: {query}",
            },
        ],
    }
    headers = {"content-type": "application/json"}
    if api_key:
        headers["authorization"] = f"Bearer {api_key}"
    body = json.dumps(payload).encode()
    try:
        with request.urlopen(request.Request(endpoint, data=body, headers=headers, method="POST")) as response:
            result = json.loads(response.read())
    except error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise RuntimeError(f"model provider returned HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"could not reach model provider: {exc.reason}") from exc

    try:
        return result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("model provider returned an unexpected chat-completions response") from exc


def main() -> int:
    query = _setting("MODEL_QUERY", "Explain the audit trail")
    source = _setting(
        "MODEL_SOURCE",
        "The control plane records every request in a hash chained audit log.",
    )
    agent_id = _setting("MODEL_AGENT_ID", "model-test")
    governor.init_db()
    with governor._connect() as db:
        db.execute(
            "INSERT OR IGNORE INTO agents(agent_id, balance, created_at) VALUES (?, ?, ?)",
            (agent_id, 1, 0),
        )
    try:
        result = governor.govern(
            agent_id=agent_id,
            query=query,
            retrieve=lambda _: [source],
            generate=lambda _, chunks: model_completion(query, chunks),
        )
    except (RuntimeError, ValueError) as exc:
        print(f"test:model failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0 if result.get("released") else 2


if __name__ == "__main__":
    raise SystemExit(main())