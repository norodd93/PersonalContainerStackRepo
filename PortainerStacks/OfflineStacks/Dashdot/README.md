# Dashdot stack (nedpi)

Portainer stack `dashdot` on nedpi (Raspberry Pi 5). It runs Dashdot, a simple dashboard for host metrics (OS, CPU, RAM, storage, network).

## What's in the stack

| Service | Image | Port | What it does |
|---------|-------|-----:|--------------|
| dash    | `mauricenino/dashdot:latest` | 3001 | Serves the Dashdot web UI and reads host metrics |

The `latest` tag is multi-arch and runs on Raspberry Pi 5 (ARM64). The NVIDIA/GPU image variant is not applicable to the Pi.

## How it works

Dashdot runs inside a container but reports metrics from the Docker host. To do that, the stack:

- runs the container as `privileged: true`, and
- mounts the host root filesystem read-only at `/mnt/host` (`/:/mnt/host:ro`).

Only use this on trusted hosts/networks, since it grants the container broad access to host information.

Dashdot listens on port 3001 inside the container. The stack publishes it on the host (default in the copy below: `3001:3001`).

## Access

From a browser: http://<host-ip>:3001/

Adjust the host port mapping if you want a different port (for example, `80:3001` if port 80 is free).

## Storage

This stack has no persistent volumes by default. Dashdot configuration is provided through environment variables. If you later add custom branding/assets or other features that require persistence, add the appropriate volumes and document them here.

## Settings that matter

- `DASHDOT_WIDGET_LIST` controls which widgets are shown. Example: `os,cpu,storage,ram,network`. The storage widget does not need a separate data/path env var in this setup; it reads host filesystems via `/:/mnt/host:ro`.
- `DASHDOT_ENABLE_CPU_TEMPS: "true"` enables CPU temperature reporting. On Raspberry Pi OS this often works with `privileged: true` and the host mount; if temps do not appear, redeploy and check that the OS exposes thermal data.
- `DASHDOT_CPU_TEMPS_MODE` can be `max` or `avg` if you need to tune temperature reporting.
- Optional storage customization (only if needed): `DASHDOT_FS_DEVICE_FILTER`, `DASHDOT_FS_TYPE_FILTER`, `DASHDOT_STORAGE_WIDGET_ITEMS_PER_PAGE`, etc. Check container logs at startup to see detected device names.
- Port mapping: change `3001:3001` to avoid conflicts with Portainer or other services.
- Security: `privileged: true` + `/:/mnt/host:ro` is required for host metrics. Do not expose the dashboard publicly without appropriate network controls/auth in front of it.
- See the Dashdot documentation for the full list of environment variables: https://getdashdot.com/docs/configuration

## Setting it up

1. In Portainer: Stacks, Add stack, choose **Repository**, and name it `dashdot`.
2. Set **Repository URL** to `https://github.com/norodd93/PersonalContainerStackRepo.git` and **Repository reference** to `refs/heads/main`.
3. Set **Compose path** to `PortainerStacks/Dashdot/compose.yml`.
4. (Optional) Add or change environment variables, then click **Deploy the stack**.
5. Open http://<host-ip>:3001/ and confirm widgets load.

## Updating the stack

1. Edit `PortainerStacks/Dashdot/compose.yml` (and this README, if needed) in the repo, then commit and push.
2. In Portainer, open Stacks, then `dashdot`, and click **Pull and redeploy**.
3. Turn **Re-pull image and redeploy** on if you want the latest `dashdot:latest` image.

Dashdot has no persistent app data in this stack, so updates/restarts are low risk. A restart briefly interrupts the dashboard.

## Troubleshooting

| Problem | Meaning | Fix |
|---------|---------|-----|
| `port is already allocated` on deploy | Another service is using the chosen host port | Change the left side of the port mapping (e.g., `3002:3001`) and redeploy |
| Metrics/widgets are missing or incorrect | Dashdot cannot read host information | Confirm `privileged: true` and `/:/mnt/host:ro` are present; redeploy the stack |
| CPU temperature is not shown | Thermal data not exposed or temp reporting disabled | Set `DASHDOT_ENABLE_CPU_TEMPS: "true"`; try `DASHDOT_CPU_TEMPS_MODE=max` or `avg`; verify Raspberry Pi OS thermal interfaces are available |
| Storage widget is empty/wrong | Devices filtered unexpectedly or detection issue | Check Portainer logs for Static Server Info -> storage; add `DASHDOT_FS_DEVICE_FILTER` / `DASHDOT_FS_TYPE_FILTER` only if needed |
| Dashboard not reachable | Wrong IP/port, firewall, or container not running | Check the container status/logs in Portainer; confirm the host IP and published port |

## Stack file (copy)

Portainer holds the real stack. This is a copy, so keep it in sync when you edit the stack.

```yaml
version: "3.5"

services:
  dash:
    image: mauricenino/dashdot:latest
    container_name: dashdot
    restart: unless-stopped
    privileged: true
    ports:
      - "3001:3001"   # change left side if you want a different host port (e.g. "80:3001")
    volumes:
      - /:/mnt/host:ro
    environment:
      DASHDOT_WIDGET_LIST: "os,cpu,storage,ram,network"
      # Optional: enable CPU temperature reporting on the Pi
      DASHDOT_ENABLE_CPU_TEMPS: "true"
      # If temps don't show, you can also try:
      # DASHDOT_CPU_TEMPS_MODE: "max"   # or "avg"
```

---
Last updated: 2026-11-08
