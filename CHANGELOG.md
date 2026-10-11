# Changelog

All notable changes to this project are documented here. This project follows
Semantic Versioning.

## [0.1.0] - 2026-10-11

### Added

- Initial Python package metadata and tag-triggered PyPI publishing workflow.
- CI secret, filesystem, dependency, and Python security checks.
- `/healthz` and `/readyz` endpoints, structured request logging, and optional
  server-side Sentry reporting.
- Bearer-token-protected Prometheus metrics endpoint and scrape configuration
  example.
- Staging-only k6 smoke/load script and Docker image-tag rollback guidance.
