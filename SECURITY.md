# Security policy

## Reporting a vulnerability

Please do not report exploitable vulnerabilities in public issues. Use GitHub's
private vulnerability reporting for this repository. Include affected
versions, impact, reproduction steps, and any suggested mitigation. Do not
include real credentials or customer data.

## Supported versions

Security fixes are applied to the latest released version. Update to the
current release before reporting an issue when possible.

## Operational guidance

- Set a strong `GOVERNOR_OPERATOR_KEY` and keep `.env` out of source control.
- Use TLS and network-level access controls when exposing the service.
- Treat the HTTP hook as post-generation governance; it cannot prevent a model
  from seeing or emitting sensitive data before the hook is called.
- Back up the SQLite database and persistent vector-store data before upgrades.
- Configure `PROMETHEUS_BEARER_TOKEN` before enabling Prometheus scraping.
- Configure Sentry only on the server and avoid transmitting personal data.
