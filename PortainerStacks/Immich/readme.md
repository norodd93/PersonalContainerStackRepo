# Immich

This folder contains the Compose files for the Immich deployment:

- `immich.yml` runs the Immich server, PostgreSQL database, and Valkey (Redis-compatible) service.
- `immich-mi.yml` runs Immich's machine-learning service, which handles tasks such as image recognition and smart search.

The server stack runs on brick; the machine-learning stack runs on nedpi. Both use image tag `v3.3.6`.

## Access

- Immich (brick): [http://100.65.227.39:2283](http://100.65.227.39:2283)
- Machine learning (nedpi): [http://127.0.0.1:3003](http://127.0.0.1:3003), published on the tailnet as [http://100.96.62.97:3003](http://100.96.62.97:3003) with `tailscale serve`

## Data storage

The main stack stores PostgreSQL data in `/srv/immich/ImmichDB` and uploaded photos and videos in `/srv/immich/ImmichUpload` on the Docker host. Make sure these directories exist, have suitable permissions, and are included in your backups before starting the stack.

The machine-learning stack uses a named Docker volume, `model-cache`, to cache downloaded models.

## Deployment notes

`immich.yml` joins the external Docker network `immich_default`. The Immich install normally creates it; if it is missing, create it on brick before deploying:

```bash
sudo docker network create immich_default
```

The Compose files are separate stacks. Because the machine-learning service runs on a different host from the Immich server, its URL is configured in Immich's administration settings as `http://100.96.62.97:3003`, and the service must be reachable from brick over the tailnet. Both files bind their published ports to `127.0.0.1`; the machine-learning port is then exposed with `tailscale serve` on nedpi.

The database password is currently set directly in `immich.yml`. Change it before deployment and keep `POSTGRES_PASSWORD` and `DB_PASSWORD` in sync. Avoid exposing the database port publicly.

---
Last updated: 2026-11-11
