"""Deterministic control plane for retrieval-augmented generation agents."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import sqlite3
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

load_dotenv()

DB_PATH = os.getenv("GOVERNOR_DB", "./governor.db")
CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
OPERATOR_KEY = os.getenv("GOVERNOR_OPERATOR_KEY", "")
REFUSAL = "I cannot answer from the supplied sources."
WORD_RE = re.compile(r"[A-Za-z0-9']+")


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    return connection


def init_db() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with _connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY, active INTEGER NOT NULL DEFAULT 1,
                balance REAL NOT NULL DEFAULT 0, created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS cache (
                cache_key TEXT PRIMARY KEY, answer TEXT NOT NULL,
                created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS retr_cache (
                cache_key TEXT PRIMARY KEY, chunks TEXT NOT NULL,
                doc_version TEXT NOT NULL, created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS loops (
                id INTEGER PRIMARY KEY AUTOINCREMENT, agent_id TEXT NOT NULL,
                created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS log (
                id INTEGER PRIMARY KEY AUTOINCREMENT, request_id TEXT NOT NULL,
                agent_id TEXT NOT NULL, decision TEXT NOT NULL,
                payload TEXT NOT NULL, previous_hash TEXT NOT NULL,
                entry_hash TEXT NOT NULL, created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS cycle (
                id INTEGER PRIMARY KEY CHECK (id = 1), request_count INTEGER NOT NULL,
                restricted INTEGER NOT NULL DEFAULT 0, updated_at REAL NOT NULL
            );
            INSERT OR IGNORE INTO cycle(id, request_count, restricted, updated_at)
                VALUES (1, 0, 0, 0);
            """
        )


def _ngrams(text: str, size: int) -> set[tuple[str, ...]]:
    words = [word.lower() for word in WORD_RE.findall(text)]
    return set(zip(*(words[index:] for index in range(size)))) if len(words) >= size else set()


def _overlap(left: str, right: str, size: int) -> float:
    source = _ngrams(right, size)
    candidate = _ngrams(left, size)
    return len(candidate & source) / len(candidate) if candidate else 0.0


def noise_gate(query: str) -> bool:
    """Return true when a query contains enough signal to process."""
    words = WORD_RE.findall(query or "")
    if len(words) < 3:
        return False
    return len("".join(words)) >= 8 and len(set(word.lower() for word in words)) >= 2


def identity_gate(agent_id: str) -> bool:
    with _connect() as db:
        agent = db.execute("SELECT active FROM agents WHERE agent_id = ?", (agent_id,)).fetchone()
    return bool(agent and agent["active"])


def loop_gate(agent_id: str, now: float | None = None) -> bool:
    """Record a request and reject an agent's fourth request in 300 seconds."""
    current = time.time() if now is None else now
    with _connect() as db:
        db.execute("DELETE FROM loops WHERE created_at < ?", (current - 300,))
        count = db.execute(
            "SELECT COUNT(*) FROM loops WHERE agent_id = ? AND created_at >= ?",
            (agent_id, current - 300),
        ).fetchone()[0]
        allowed = count < 3
        if allowed:
            db.execute("INSERT INTO loops(agent_id, created_at) VALUES (?, ?)", (agent_id, current))
        return allowed


def citation_check(answer: str, source_chunks: Iterable[str]) -> bool:
    """Validate quoted answers at 90% 5-gram overlap, prose at 35% 3-gram."""
    if answer.strip() == REFUSAL:
        return True
    chunks = [chunk for chunk in source_chunks if chunk]
    quotes = re.findall(r'["\u201c](.*?)["\u201d]', answer, flags=re.DOTALL)
    if quotes:
        return bool(chunks) and all(
            max((_overlap(quote, chunk, 5) for chunk in chunks), default=0.0) >= 0.90
            for quote in quotes
        )
    return bool(chunks) and max((_overlap(answer, chunk, 3) for chunk in chunks), default=0.0) >= 0.35


def hash_collection_contents(collection: Any) -> str:
    """Hash Chroma contents and IDs, so a document rename changes no version."""
    data = collection.get(include=["documents", "metadatas"])
    rows = []
    for index, document in enumerate(data.get("documents") or []):
        rows.append({
            "id": (data.get("ids") or [""] * len(data.get("documents") or []))[index],
            "document": document,
            "metadata": (data.get("metadatas") or [{}] * len(data.get("documents") or []))[index],
        })
    payload = json.dumps(sorted(rows, key=lambda row: row["id"]), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def verify_chain() -> bool:
    with _connect() as db:
        entries = db.execute("SELECT * FROM log ORDER BY id").fetchall()
    previous = ""
    for entry in entries:
        payload = json.dumps({"request_id": entry["request_id"], "agent_id": entry["agent_id"], "decision": entry["decision"], "payload": entry["payload"], "created_at": entry["created_at"]}, sort_keys=True, separators=(",", ":"))
        expected = hashlib.sha256((previous + payload).encode()).hexdigest()
        if entry["previous_hash"] != previous or entry["entry_hash"] != expected:
            return False
        previous = entry["entry_hash"]
    return True


def _log(request_id: str, agent_id: str, decision: str, payload: dict[str, Any]) -> None:
    now = time.time()
    with _connect() as db:
        previous = db.execute("SELECT entry_hash FROM log ORDER BY id DESC LIMIT 1").fetchone()
        previous_hash = previous[0] if previous else ""
        encoded = json.dumps({"request_id": request_id, "agent_id": agent_id, "decision": decision, "payload": json.dumps(payload, sort_keys=True), "created_at": now}, sort_keys=True, separators=(",", ":"))
        entry_hash = hashlib.sha256((previous_hash + encoded).encode()).hexdigest()
        db.execute("INSERT INTO log(request_id, agent_id, decision, payload, previous_hash, entry_hash, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (request_id, agent_id, decision, json.dumps(payload, sort_keys=True), previous_hash, entry_hash, now))


def _cycle() -> None:
    with _connect() as db:
        db.execute("UPDATE cycle SET request_count = request_count + 1, updated_at = ? WHERE id = 1", (time.time(),))
        count = db.execute("SELECT request_count FROM cycle WHERE id = 1").fetchone()[0]
        if count % 60 == 0 and not verify_chain():
            db.execute("UPDATE cycle SET restricted = 1 WHERE id = 1")


def govern(agent_id: str, query: str, retrieve: Callable[[str], list[str]], generate: Callable[[str, list[str]], str], request_id: str | None = None) -> dict[str, Any]:
    """Run the complete deterministic path around caller-supplied RAG functions."""
    request_id = request_id or hashlib.sha256(f"{agent_id}:{query}".encode()).hexdigest()[:16]
    with _connect() as db:
        restricted = db.execute("SELECT restricted FROM cycle WHERE id = 1").fetchone()[0]
    if not identity_gate(agent_id):
        decision = {"released": False, "reason": "identity"}
    elif restricted:
        decision = {"released": False, "reason": "operator_restriction"}
    elif not noise_gate(query):
        decision = {"released": False, "reason": "noise_gate"}
    elif not loop_gate(agent_id):
        decision = {"released": False, "reason": "loop_gate"}
    else:
        exact_key = hashlib.sha256(query.strip().lower().encode()).hexdigest()
        with _connect() as db:
            cached = db.execute("SELECT answer FROM cache WHERE cache_key = ?", (exact_key,)).fetchone()
        if cached:
            decision = {"released": True, "answer": cached[0], "source": "exact_cache"}
        else:
            retrieval_key = hashlib.sha256(query.strip().lower().encode()).hexdigest()
            with _connect() as db:
                retrieval = db.execute("SELECT chunks FROM retr_cache WHERE cache_key = ?", (retrieval_key,)).fetchone()
            if retrieval:
                chunks = json.loads(retrieval[0])
            else:
                chunks = retrieve(query)
                doc_version = hashlib.sha256(json.dumps(chunks, sort_keys=True).encode()).hexdigest()
                with _connect() as db:
                    db.execute("INSERT OR REPLACE INTO retr_cache(cache_key, chunks, doc_version, created_at) VALUES (?, ?, ?, ?)", (retrieval_key, json.dumps(chunks), doc_version, time.time()))
            with _connect() as db:
                agent = db.execute("SELECT balance FROM agents WHERE agent_id = ?", (agent_id,)).fetchone()
                if not agent or agent["balance"] < 1:
                    decision = {"released": False, "reason": "precharged_spend"}
                    _log(request_id, agent_id, "hold", decision)
                    _cycle()
                    return decision
                db.execute("UPDATE agents SET balance = balance - 1 WHERE agent_id = ?", (agent_id,))
            answer = generate(query, chunks)
            released = citation_check(answer, chunks)
            decision = {"released": released, "answer": answer, "reason": "citation_check" if not released else "rag"}
            if released:
                with _connect() as db:
                    db.execute("INSERT OR REPLACE INTO cache(cache_key, answer, created_at) VALUES (?, ?, ?)", (exact_key, answer, time.time()))
    _log(request_id, agent_id, "release" if decision["released"] else "hold", decision)
    _cycle()
    return decision


class AgentRequest(BaseModel):
    agent_id: str


class GovernRequest(BaseModel):
    agent_id: str
    query: str
    source_chunks: list[str] = []
    answer: str
    request_id: str | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Deterministic RAG Governor", lifespan=lifespan)


def _operator_required(key: str | None) -> None:
    if not OPERATOR_KEY or key is None or not hmac.compare_digest(key, OPERATOR_KEY):
        raise HTTPException(status_code=403, detail="operator key required")


@app.post("/admin/agent")
def register_agent(request: AgentRequest, x_operator_key: str | None = Header(default=None)) -> dict[str, str]:
    _operator_required(x_operator_key)
    with _connect() as db:
        db.execute("INSERT OR IGNORE INTO agents(agent_id, created_at) VALUES (?, ?)", (request.agent_id, time.time()))
    return {"status": "registered", "agent_id": request.agent_id}


@app.post("/admin/refresh")
def refresh(x_operator_key: str | None = Header(default=None)) -> dict[str, str]:
    _operator_required(x_operator_key)
    with _connect() as db:
        db.execute("UPDATE cycle SET restricted = 0, request_count = 0, updated_at = ? WHERE id = 1", (time.time(),))
    return {"status": "refreshed"}


@app.post("/govern")
def govern_request(request: GovernRequest) -> dict[str, Any]:
    """Universal adapter for agents and model providers to test governance."""
    return govern(
        agent_id=request.agent_id,
        query=request.query,
        retrieve=lambda _: request.source_chunks,
        generate=lambda _, __: request.answer,
        request_id=request.request_id,
    )


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "chain_valid": verify_chain()}