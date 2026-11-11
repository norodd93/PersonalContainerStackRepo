# PersonalContainerStackRepo

Compose files and notes for my self-hosted stacks. They run on two machines, are managed with Portainer, and are reachable over Tailscale only.

## Hosts

| Host  | Hardware                                          | What runs there |
|-------|---------------------------------------------------|-----------------|
| nedpi | Raspberry Pi 5, 16 GB                             | Portainer (EE), Ollama, Open WebUI, SearXNG, OpenCode proxy, SnapOtter, ReClip, Immich machine learning, Glance, WUD, HomeButler |
| brick | Old Toshiba laptop, Debian 13 headless, WiFi only | Portainer (CE), Syncthing, Immich, Glance, WUD |

## Stacks

| Stack       | Host         | Services                                | Ports | Docs |
|-------------|--------------|-----------------------------------------|-------|------|
| `ollama`    | nedpi        | Ollama                                  | [11434](http://100.96.62.97:11434) | [Ollama](PortainerStacks/Ollama/readme.md) |
| `webui`     | nedpi        | Open WebUI, SearXNG, OpenCode proxy     | [3001](http://100.96.62.97:3001), SearXNG [8888](http://127.0.0.1:8888) (localhost only) | [WebUI](PortainerStacks/WebUI/readme.md) |
| `snapotter` | nedpi        | SnapOtter, ReClip, Postgres, Redis      | [1349](http://100.96.62.97:1349), [8899](http://100.96.62.97:8899) | [SnapOtter](PortainerStacks/snapotter/readme.md) |
| `homebutler` | nedpi       | HomeButler dashboard                    | [8081](http://100.96.62.97:8081) | [HomeButler](PortainerStacks/HomeButler/readme.md) |
| `immich-ml` | nedpi        | Immich machine learning                 | 3003 localhost, [100.96.62.97:3003](http://100.96.62.97:3003) via `tailscale serve` | [Immich](PortainerStacks/Immich/readme.md) |
| `immich`    | brick        | Immich                                  | [2283](http://100.65.227.39:2283) | [Immich](PortainerStacks/Immich/readme.md) |
| `syncthing` | brick        | Syncthing                               | [8384](http://100.65.227.39:8384) (GUI), 22000 (sync) | - |
| `portainer` | nedpi, brick | Portainer (EE on nedpi, CE on brick)    | [nedpi 9443](https://100.96.62.97:9443), [brick 9443](https://100.65.227.39:9443) | [portainer.yml](portainer.yml) |
| `glance`    | nedpi, brick | Glance, Glance Agent, docker-proxy, WUD | [nedpi 8080](http://100.96.62.97:8080), [brick 8080](http://100.65.227.39:8080), WUD [nedpi 3055](http://100.96.62.97:3055), [brick 3055](http://100.65.227.39:3055); 27973 and 2375 (tailnet, host-to-host) | [Glance](PortainerStacks/Glance/readme.md) |

`webui` needs the `ollama` stack and the `ai-net` network. The `immich` stack expects the external `immich_default` network, which the Immich install creates.

Portainer runs on both hosts on **9443**. nedpi binds `127.0.0.1` and is published over the tailnet with `tailscale serve`; brick's `portainer.yml` does the same (CE image, `127.0.0.1:9443`). Brick's live copy is `/home/norod/portainer/portainer.yml`; to change the binding, recreate the container from that file. `portainer_data` is external and keeps users and settings.

Not deployed: [`PortainerStacks/Netbird`](PortainerStacks/Netbird/readme.md) (no container on either host) and [`PortainerStacks/OfflineStacks/Dashdot`](PortainerStacks/OfflineStacks/Dashdot/README.md).

`glance` runs on both hosts. Each dashboard shows both hosts' CPU, RAM and disks, their containers, and the images WUD has flagged for updates. It reads the other host's agent, Docker proxy and WUD over the tailnet. The per-host values are Portainer environment variables; `glance-nedpi.env` and `glance-brick.env` in its folder are templates. WUD only reports updates; it never pulls or restarts anything.

## Fresh install?

Install Docker first, then use Docker to deploy Portainer for management. Or Coolify, which is experimental.

1. Install Docker Engine from Docker's apt repo: https://docs.docker.com/engine/install/. Commands in this repo use `sudo docker`.
2. Install Tailscale and join the tailnet: https://tailscale.com/download. Check the host's IP with `tailscale ip -4`.
3. Deploy Portainer: https://docs.portainer.io. The UI is on **9443**. Create the data volume first (`sudo docker volume create portainer_data`), then `portainer.yml` binds `127.0.0.1:9443`; publish it to the tailnet with `tailscale serve --bg --tcp=9443 tcp://127.0.0.1:9443`. Keep the UI off the LAN. The optional edge port `8000` is not published; add it only if you use Edge Agents.
4. On nedpi only, create the shared network for the AI stacks (see below).
5. On brick, make sure the external `immich_default` network exists before deploying `immich` (the Immich install creates it; otherwise run `sudo docker network create immich_default`).
6. In Portainer, go to Stacks, Add stack, choose **Repository**, and deploy the stack from this repo (`https://github.com/norodd93/PersonalContainerStackRepo.git`, `refs/heads/main`). Set the **Compose path** to the stack's compose file under `PortainerStacks/` (for example `PortainerStacks/Ollama/compose.yml` or `PortainerStacks/Glance/glance-stack.yml`), add any variables, and click **Deploy the stack**.

The `ollama` and `webui` stacks talk to each other over an external Docker network called `ai-net`. Portainer does not create it, and both stacks fail to deploy without it. Create it once, before deploying either:

```bash
sudo docker network create ai-net
```

## How the stacks are set up

- **Ports.** Published ports are bound to `127.0.0.1` or to the host's Tailscale IP, never to all interfaces, so nothing is reachable from the LAN. Exceptions are SSH and Syncthing's sync port (22000). Portainer also binds `127.0.0.1` and is published with `tailscale serve`.
- **Remote access.** Tailnet only. A stack either binds to the Tailscale IP directly, or stays on `127.0.0.1` and is published with `tailscale serve`.
- **Data.** Bind mounts on the host, not named volumes. On nedpi this is usually `/home/norod/docker/<stack>`.
- **Secrets.** Set them as Portainer variables where the stack supports it, for example `WEBUI_SECRET_KEY` for `webui`. Don't put them in the compose file.
- **Images.** Most stacks use rolling tags (`latest`, `main`), so updating means re-pulling. Local images such as `reclip:latest` exist only on the host and must never be re-pulled.
- **Image updates.** `glance` runs WUD on both hosts. It only reports images with newer versions; it does not pull or redeploy them.
- **Source of truth.** Portainer deploys the stack files from this repo, so they are the source. Some READMEs still include a copy for reference; keep those in sync. Each stack README ends with a "Last updated" date at the bottom.

## Updating a stack

1. Edit the stack's compose file (and its README, if needed) in this repo, then commit and push.
2. In Portainer, open Stacks, then the stack, and click **Pull and redeploy** to pick up the change from GitHub.
3. Turn **Re-pull image and redeploy** on when you want newer images, except for `snapotter`, where it must stay off (see its README).
4. Update the "Last updated" date in the stack's README when you change it.

## When a Tailscale IP changes

The current IPs are `100.96.62.97` (nedpi) and `100.65.227.39` (brick). They are written into several files, so a change breaks things in more than one place. A stack that binds to a stale IP fails to start with `cannot assign requested address`.

| Where           | What to update |
|-----------------|----------------|
| `ollama`        | The first `ports:` line |
| `webui`         | The second `ports:` line of `open-web-ui`, and `WEBUI_URL` |
| `snapotter`     | Both `ports:` lines (`snapotter` and `reclip`) |
| `homebutler`    | The `ports:` line                                |
| `immich` (brick) | The machine learning URL in Immich's admin settings (`http://<ip>:3003`) |
| `glance` (both hosts) | `BIND_IP` on the host whose IP changed, then `PEER_URL`, `PEER_DOCKER` and `PEER_WUD_ADDR` on the other host |

Run `tailscale ip -4` on the affected host to get the new address.

## Common errors

| Error on deploy | Meaning | Fix |
|-----------------|---------|-----|
| `network ai-net declared as external, but could not be found` | The shared network does not exist | Create it (see Fresh install), then redeploy |
| `network immich_default declared as external, but could not be found` | The Immich network does not exist | Create it with `sudo docker network create immich_default`, then redeploy |
| `cannot assign requested address` | The Tailscale IP in the stack's config or environment variables is not on the host: the IP changed, or `tailscaled` is down | Run `tailscale ip -4` and update the places listed above. If nothing prints, start Tailscale first |
| `set NAME` or `set NAME is required` | A variable the stack marks as required is missing or misspelled in Portainer | Add it under the stack's environment variables, then redeploy |
| `No such image` for a local image | The image was built on the host and is missing | Rebuild it (see the stack's README), then redeploy |
| `port is already allocated` or `container name ... is already in use` | An old stack or container still holds the name or port | Delete the old stack, then redeploy |

Stack-specific problems are in each stack's README.

---
Last updated: 2026-11-11
