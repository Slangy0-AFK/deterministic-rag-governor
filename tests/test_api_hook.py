import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import governor


class UniversalHookTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        governor.DB_PATH = str(Path(self.directory.name) / "hook.db")
        governor.init_db()
        with governor._connect() as db:
            db.execute(
                "INSERT INTO agents(agent_id, balance, created_at) VALUES (?, ?, ?)",
                ("test-agent", 1, 0),
            )

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_model_output_is_released_through_universal_hook(self) -> None:
        payload = {
            "agent_id": "test-agent",
            "query": "explain the audit trail",
            "source_chunks": [
                "The control plane records every request in a hash chained audit log."
            ],
            "answer": "The control plane records every request in a hash chained audit log.",
        }

        with TestClient(governor.app) as client:
            response = client.post("/govern", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["released"])
        self.assertEqual(response.json()["reason"], "rag")

    def test_invalid_model_output_is_held(self) -> None:
        payload = {
            "agent_id": "test-agent",
            "query": "explain the audit trail",
            "source_chunks": ["The control plane records every request."],
            "answer": "This answer is unrelated to the supplied source.",
        }

        with TestClient(governor.app) as client:
            response = client.post("/govern", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["released"])
        self.assertEqual(response.json()["reason"], "citation_check")

    def test_liveness_and_readiness_endpoints(self) -> None:
        with TestClient(governor.app) as client:
            live = client.get("/healthz")
            ready = client.get("/readyz")

        self.assertEqual(live.status_code, 200)
        self.assertEqual(live.json(), {"ok": True})
        self.assertEqual(ready.status_code, 200)
        self.assertEqual(ready.json(), {"ok": True})

    def test_metrics_endpoint_requires_configured_bearer_token(self) -> None:
        original_token = governor.PROMETHEUS_BEARER_TOKEN
        governor.PROMETHEUS_BEARER_TOKEN = "test-metrics-token"
        try:
            with TestClient(governor.app) as client:
                unauthorized = client.get("/metrics")
                authorized = client.get(
                    "/metrics",
                    headers={"Authorization": "Bearer test-metrics-token"},
                )
        finally:
            governor.PROMETHEUS_BEARER_TOKEN = original_token

        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(authorized.status_code, 200)
        self.assertIn("governor_up 1", authorized.text)


if __name__ == "__main__":
    unittest.main()