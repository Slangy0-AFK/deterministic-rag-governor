import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import governor


@unittest.skipUnless(os.getenv("RUN_LIVE_RAG") == "1", "set RUN_LIVE_RAG=1 to call Ollama")
class LiveRagTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        governor.DB_PATH = str(Path(self.directory.name) / "live.db")
        governor.CHROMA_PATH = str(Path(self.directory.name) / "chroma")
        governor.init_db()

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_ingest_and_query_use_real_rag_stack(self) -> None:
        with TestClient(governor.app) as client:
            registered = client.post(
                "/admin/agent",
                headers={"x-operator-key": governor.OPERATOR_KEY or "change-me"},
                json={"agent_id": "live-agent", "initial_balance": 1},
            )
            self.assertEqual(registered.status_code, 200)
            ingested = client.post(
                "/rag/ingest",
                headers={"x-operator-key": governor.OPERATOR_KEY or "change-me"},
                json={"documents": ["The archive retention period is seven years."]},
            )
            self.assertEqual(ingested.status_code, 200)
            result = client.post(
                "/rag/query",
                json={"agent_id": "live-agent", "query": "What is the archive retention period?"},
            )

        self.assertEqual(result.status_code, 200)
        self.assertTrue(result.json()["released"], result.text)
        self.assertIn("seven", result.json()["answer"].lower())


if __name__ == "__main__":
    unittest.main()