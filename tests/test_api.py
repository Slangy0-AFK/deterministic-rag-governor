"""HTTP-level tests for operator controls and governed requests."""

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import governor


SOURCE = "The control plane records every request in a hash chained audit log."
OPERATOR_KEY = "test-operator-key"


class FakeRagAdapter:
    version = "lab-v1"

    def __init__(self) -> None:
        self.retrieval_count = 0

    def retrieve(self, query: str) -> list[str]:
        self.retrieval_count += 1
        return [SOURCE]

    def generate(self, query: str, chunks: list[str]) -> str:
        return chunks[0]


class GovernorApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        governor.DB_PATH = str(Path(self.directory.name) / "test.db")
        governor.OPERATOR_KEY = OPERATOR_KEY
        governor.RAG_ADAPTER = ""
        self.client = TestClient(governor.app)
        self.client.__enter__()
        governor.app.state.rag_adapter = FakeRagAdapter()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.directory.cleanup()

    def register_agent(self) -> None:
        response = self.client.post(
            "/admin/agent",
            headers={"X-Operator-Key": OPERATOR_KEY},
            json={"agent_id": "lab-agent"},
        )
        self.assertEqual(response.status_code, 200)

    def test_operator_funds_and_governs_request(self) -> None:
        self.assertEqual(self.client.post("/admin/agent", json={"agent_id": "lab-agent"}).status_code, 403)
        self.register_agent()

        credit = self.client.post(
            "/admin/agent/credit",
            headers={"X-Operator-Key": OPERATOR_KEY},
            json={"agent_id": "lab-agent", "amount": 2},
        )
        self.assertEqual(credit.status_code, 200)
        self.assertEqual(credit.json()["balance"], 2)
        invalid_credit = self.client.post(
            "/admin/agent/credit",
            headers={"X-Operator-Key": OPERATOR_KEY},
            json={"agent_id": "lab-agent", "amount": 0},
        )
        self.assertEqual(invalid_credit.status_code, 422)

        response = self.client.post(
            "/govern",
            json={"agent_id": "lab-agent", "query": "Summarize the source audit record"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["released"])
        self.assertEqual(response.json()["reason"], "rag")

        cached = self.client.post(
            "/govern",
            json={"agent_id": "lab-agent", "query": "Summarize the source audit record"},
        )
        self.assertEqual(cached.json()["source"], "exact_cache")
        self.assertEqual(governor.app.state.rag_adapter.retrieval_count, 1)

        governor.app.state.rag_adapter.version = "lab-v2"
        refreshed = self.client.post(
            "/govern",
            json={"agent_id": "lab-agent", "query": "Summarize the source audit record"},
        )
        self.assertEqual(refreshed.json()["reason"], "rag")
        self.assertEqual(governor.app.state.rag_adapter.retrieval_count, 2)
        self.assertEqual(self.client.get("/ready").status_code, 200)
        self.assertTrue(self.client.get("/health").json()["chain_valid"])

    def test_rag_failures_are_logged_as_holds(self) -> None:
        class FailingAdapter(FakeRagAdapter):
            def generate(self, query: str, chunks: list[str]) -> str:
                raise RuntimeError("private backend detail")

        self.register_agent()
        self.client.post(
            "/admin/agent/credit",
            headers={"X-Operator-Key": OPERATOR_KEY},
            json={"agent_id": "lab-agent", "amount": 1},
        )
        governor.app.state.rag_adapter = FailingAdapter()
        response = self.client.post(
            "/govern",
            json={"agent_id": "lab-agent", "query": "Summarize the source audit record"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"released": False, "reason": "generation_error"})
        self.assertTrue(governor.verify_chain())
        with governor._connect() as db:
            balance = db.execute("SELECT balance FROM agents WHERE agent_id = ?", ("lab-agent",)).fetchone()[0]
        self.assertEqual(balance, 0)

    def test_ungrounded_answer_is_not_returned(self) -> None:
        class UngroundedAdapter(FakeRagAdapter):
            def generate(self, query: str, chunks: list[str]) -> str:
                return "An unrelated answer with no supporting source material."

        self.register_agent()
        self.client.post(
            "/admin/agent/credit",
            headers={"X-Operator-Key": OPERATOR_KEY},
            json={"agent_id": "lab-agent", "amount": 1},
        )
        governor.app.state.rag_adapter = UngroundedAdapter()

        response = self.client.post(
            "/govern",
            json={"agent_id": "lab-agent", "query": "Summarize the source audit record"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["released"], False)
        self.assertEqual(response.json()["reason"], "citation_check")
        self.assertNotIn("answer", response.json())
        self.assertTrue(governor.verify_chain())

    def test_request_without_adapter_is_not_ready(self) -> None:
        governor.app.state.rag_adapter = None
        self.assertEqual(self.client.get("/ready").status_code, 503)
        response = self.client.post(
            "/govern",
            json={"agent_id": "lab-agent", "query": "Summarize the source audit record"},
        )
        self.assertEqual(response.status_code, 503)

    def test_insufficient_balance_is_logged_as_a_hold(self) -> None:
        self.register_agent()
        response = self.client.post(
            "/govern",
            json={"agent_id": "lab-agent", "query": "Summarize the source audit record"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"released": False, "reason": "precharged_spend"})
        self.assertTrue(governor.verify_chain())


if __name__ == "__main__":
    unittest.main()