# SnapOtter + ReClip stack (nedpi)

Portainer stack `snapotter` on nedpi (Raspberry Pi 5). It runs SnapOtter, its database and queue, and ReClip. Both web UIs are reachable over the tailnet only.

## What's in the stack

| Service   | Image                      | Port | What it does |
|-----------|----------------------------|-----:|--------------|
| snapotter | `snapotter/snapotter:latest` | [1349](http://100.96.62.97:1349) | SnapOtter web app (image/video processing, optional AI features) |
| db        | `postgres:17-alpine`       | -    | SnapOtter database. No published port |
| redis     | `redis:8-alpine`           | -    | SnapOtter job queue (256 MB cap, `noeviction`). No published port |
| reclip    | `reclip:latest`            | [8899](http://100.96.62.97:8899) | ReClip, built locally from `averygan/reclip`. Not on Docker Hub |

## Access

Both ports are bound to nedpi's Tailscale IP, so they are not reachable from the LAN.

- SnapOtter: [http://100.96.62.97:1349](http://100.96.62.97:1349)
- ReClip: [http://100.96.62.97:8899](http://100.96.62.97:8899)

Check the current IP with `tailscale ip -4`.

## Storage

Everything lives on the system disk under `/home/norod/docker/snapotter`. The stack does not need the external HDD.

| Folder             | Used by   | Contents |
|--------------------|-----------|----------|
| `snapotter-data`   | snapotter | App data, including installed AI bundles in `snapotter-data/ai` |
| `workspace`        | snapotter | Temporary processing files |
| `postgres-data`    | db        | Database files |
| `reclip-downloads` | reclip    | Downloaded files |

Let Docker create these folders on first start. Don't create them by hand as `norod`.

## Settings that matter

- SnapOtter limits: 3 CPUs, 8 GB memory. ReClip limits: 1 CPU, 2 GB memory.
- `PROCESSING_TIMEOUT_S=0` means no processing timeout.
- Upload and processing limits: 250 MB upload, 100 megapixels, 300 s video, 20 files per batch, 2 jobs at a time.
- Installing the AI features (OCR, Transcription) needs the memory cgroup enabled on the Pi. It is turned on by `cgroup_enable=memory cgroup_memory=1` in `/boot/firmware/cmdline.txt` (backup: `cmdline.txt.bak`). A reboot is needed after changing it.
- Changing `POSTGRES_PASSWORD` after the database has been created has no effect. The app would lose access instead.

## Updating the stack

1. Edit `PortainerStacks/snapotter/compose.yml` (and this README, if needed) in the repo, then commit and push.
2. In Portainer, open Stacks, then `snapotter`, and click **Pull and redeploy**.
3. Keep **Re-pull image and redeploy** off. `reclip:latest` exists only on the Pi, and a re-pull fails and aborts the whole stack. The stack file also sets `pull_policy: never` on `reclip` as a second guard.

To rebuild ReClip:

```bash
cd ~/reclip && sudo docker build -t reclip .
```

## Troubleshooting

| Error on deploy | Meaning | Fix |
|-----------------|---------|-----|
| `No such image: reclip:latest` | The local ReClip image is missing | Rebuild it (see above), then redeploy |
| `cannot assign requested address` on port 1349 or 8899 | The Tailscale IP in the stack file is not on nedpi: the IP changed, or `tailscaled` is down | Run `tailscale ip -4`. If the IP differs, update both `ports:` lines. If nothing prints, start Tailscale first |

If the Tailscale IP changes again, update it in both `ports:` lines below.

## Stack file (copy)

Portainer deploys this file from the repo. The copy below is for reference, so keep it in sync when you edit the stack.

```yaml
services:
  snapotter:
    image: snapotter/snapotter:latest
    ports:
      - "100.96.62.97:1349:1349"
    volumes:
      - /home/norod/docker/snapotter/snapotter-data:/data
      - /home/norod/docker/snapotter/workspace:/tmp/workspace
    environment:
      - DATABASE_URL=postgres://snapotter:snapotter@db:5432/snapotter
      - REDIS_URL=redis://redis:6379
      - CONCURRENT_JOBS=2
      - MAX_WORKER_THREADS=3
      - MAX_BATCH_SIZE=20
      - MAX_UPLOAD_SIZE_MB=250
      - MAX_MEGAPIXELS=100
      - MAX_VIDEO_DURATION_S=300
      - PROCESSING_TIMEOUT_S=0
    deploy:
      resources:
        limits:
          cpus: "3"
          memory: 8G
    depends_on:
      - db
      - redis
    restart: unless-stopped

  db:
    image: postgres:17-alpine
    labels:
      - wud.watch=false
    environment:
      - POSTGRES_USER=snapotter
      - POSTGRES_PASSWORD=snapotter
      - POSTGRES_DB=snapotter
    volumes:
      - /home/norod/docker/snapotter/postgres-data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:8-alpine
    labels:
      - wud.watch=false
    command: redis-server --maxmemory 256mb --maxmemory-policy noeviction
    restart: unless-stopped

  reclip:
    image: reclip:latest
    labels:
      - wud.watch=false
    pull_policy: never
    ports:
      - "100.96.62.97:8899:8899"
    volumes:
      - /home/norod/docker/snapotter/reclip-downloads:/app/downloads
    deploy:
      resources:
        limits:
          cpus: "1"
          memory: 2G
    restart: unless-stopped
```

---
Last updated: 2026-11-11
