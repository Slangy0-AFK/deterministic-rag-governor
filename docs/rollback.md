# Rollback procedure

The service is deployed as a Docker image. Roll back by redeploying the
previously deployed image tag; do not rebuild or redeploy the current source
commit as a rollback.

1. Identify the last known-good image tag from the deployment record.
2. Set the same image repository used by the deployment and select that tag:

   ```sh
   export GOVERNOR_IMAGE_REPOSITORY=registry.example.com/team/deterministic-rag-governor
   export GOVERNOR_IMAGE_TAG=0.1.0
   ```

3. Pull and start the previous image without rebuilding:

   ```sh
   docker compose pull web
   docker compose up -d --no-build web
   ```

4. Verify the deployment:

   ```sh
   curl --fail https://governor.example.com/healthz
   curl --fail https://governor.example.com/readyz
   ```

The database and Chroma data are persistent deployment state. Before an
upgrade, take backups and confirm the new release remains compatible with
existing data. If a release includes an incompatible data migration, restore a
matching database backup as part of the rollback; changing the image alone
cannot reverse data changes. Retain the previous image tag and its deployment
configuration until the new release has passed its rollback window.
