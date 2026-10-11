# Contributing

## Development setup

Use Python 3.11 or later. Install the application dependencies and test tools:

```sh
python -m pip install -r requirements.txt
python -m pip install pytest bandit build
```

Run the checks before submitting a change:

```sh
pytest -q
bandit -r governor.py model_test_runner.py -ll
python -m build
```

The live RAG integration test requires the Docker Compose stack and an Ollama
model; it is opt-in with `RUN_LIVE_RAG=1`. Do not put API keys, operator keys,
or production data in commits, test fixtures, or logs.

## Pull requests

Keep changes focused, include tests for behavior changes, update user-facing
documentation where needed, and describe operational impact and validation in
the pull request.
