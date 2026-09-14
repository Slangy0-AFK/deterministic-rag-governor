import json
import os
import unittest
from unittest.mock import patch

import model_test_runner


class ModelClientTest(unittest.TestCase):
    def test_uses_user_provider_model_and_api_key(self) -> None:
        captured = {}

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self):
                return json.dumps({"choices": [{"message": {"content": "grounded answer"}}]}).encode()

        def fake_urlopen(http_request):
            captured["url"] = http_request.full_url
            captured["headers"] = dict(http_request.headers)
            captured["body"] = json.loads(http_request.data)
            return Response()

        with patch.dict(
            os.environ,
            {
                "MODEL_PROVIDER": "custom",
                "MODEL_BASE_URL": "https://example.test/v1/chat/completions",
                "MODEL_ID": "user-model",
                "MODEL_API_KEY": "user-secret",
            },
            clear=False,
        ), patch("model_test_runner.request.urlopen", fake_urlopen):
            answer = model_test_runner.model_completion("What happened?", ["An event happened."])

        self.assertEqual(answer, "grounded answer")
        self.assertEqual(captured["url"], "https://example.test/v1/chat/completions")
        self.assertEqual(captured["headers"]["Authorization"], "Bearer user-secret")
        self.assertEqual(captured["body"]["model"], "user-model")


if __name__ == "__main__":
    unittest.main()