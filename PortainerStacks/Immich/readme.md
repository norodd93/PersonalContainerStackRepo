# Immich

This folder contains the Compose files for the Immich deployment:

- `immich.yml` runs the Immich server, PostgreSQL database, and Valkey (Redis-compatible) service.
- `immich-mi.yml` runs Immich's machine-learning service, which handles tasks such as image recognition and smart search.

## Data storage

The main stack stores PostgreSQL data in `/srv/immich/ImmichDB` and uploaded photos and videos in `/srv/immich/ImmichUpload` on the Docker host. Make sure these directories exist, have suitable permissions, and are included in your backups before starting the stack.

The machine-learning stack uses a named Docker volume, `model-cache`, to cache downloaded models.

## Deployment notes

The Compose files are separate stacks. If the machine-learning service runs on a different host from the Immich server, configure its URL in Immich's administration settings and make sure the service is reachable from the Immich host. Both files currently bind their published ports to `127.0.0.1`, which makes them accessible only from their respective Docker hosts; adjust the bindings and firewall rules if remote access is needed.

The database password is currently set directly in `immich.yml`. Change it before deployment and keep `POSTGRES_PASSWORD` and `DB_PASSWORD` in sync. Avoid exposing the database port publicly.
