# PersonalContainerStackRepo

Compose files and notes for my self-hosted stacks. They run on two machines, are managed with Portainer, and are reachable over Tailscale only.

## Hosts

| Host  | Hardware                                          | What runs there |
|-------|---------------------------------------------------|-----------------|
| nedpi | Raspberry Pi 5, 16 GB                             | Ollama, Open WebUI, SearXNG, SnapOtter, ReClip, Hindsight, Immich machine learning |
| brick | Old Toshiba laptop, Debian 13 headless, WiFi only | Portainer, Syncthing, Immich |

## Fresh install?

Install Docker first, then use Docker to deploy Portainer for management. Or Coolify, which is experimental.

1. Install Docker Engine from Docker's apt repo: https://docs.docker.com/engine/install/. Commands in this repo use `sudo docker`.
2. Install Tailscale and join the tailnet: https://tailscale.com/download. Check the host's IP with `tailscale ip -4`.
3. Deploy Portainer: https://docs.portainer.io. Keep its UI off the LAN. Either bind it to `127.0.0.1` and publish it to the tailnet with `tailscale serve`, or bind it to the host's Tailscale IP.
4. On nedpi only, create the shared network for the AI stacks (see below).
5. In Portainer, go to Stacks, Add stack, choose **Repository**, and deploy the stack from this repo (`https://github.com/norodd93/PersonalContainerStackRepo.git`, `refs/heads/main`). Set the **Compose path** to the stack's `compose.yml` under `PortainerStacks/`, add any variables, and click **Deploy the stack**.

The `ollama` and `webui` stacks talk to each other over an external Docker network called `ai-net`. Portainer does not create it, and both stacks fail to deploy without it. Create it once, before deploying either:

```bash
sudo docker network create ai-net
```

## Stacks

| Stack       | Host  | Services                           | Ports | Docs |
|-------------|-------|------------------------------------|-------|------|
| `ollama`    | nedpi | Ollama                             | 11434 | [README-ollama.md](README-ollama.md) |
| `webui`     | nedpi | Open WebUI, SearXNG                | 3001, SearXNG 8888 (localhost only) | [README-webui.md](README-webui.md) |
| `snapotter` | nedpi | SnapOtter, ReClip, Postgres, Redis | 1349, 8899 | [README-snapotter.md](README-snapotter.md) |
| `hindsight` | nedpi | Hindsight                          | 8888, 9999 | - |
| `immich-ml` | nedpi | Immich machine learning            | 3003 (localhost, published with `tailscale serve`) | - |
| `immich`    | brick | Immich                             | 2283 | - |
| `syncthing` | brick | Syncthing                          | 8384 (GUI), 22000 (sync) | - |
| `portainer` | brick | Portainer                          | 9000 | - |

`webui` needs the `ollama` stack and the `ai-net` network. Hindsight and SearXNG both use 8888 on nedpi. They bind different addresses (Tailscale IP and `127.0.0.1`), so they don't clash.

## How the stacks are set up

- **Ports.** Published ports are bound to `127.0.0.1` or to the host's Tailscale IP, never to all interfaces, so nothing is reachable from the LAN. Exceptions are SSH and Syncthing's sync port (22000).
- **Remote access.** Tailnet only. A stack either binds to the Tailscale IP directly, or stays on `127.0.0.1` and is published with `tailscale serve`.
- **Data.** Bind mounts on the host, not named volumes. On nedpi this is usually `/home/norod/docker/<stack>`.
- **Secrets.** Set them as Portainer variables where the stack supports it, for example `WEBUI_SECRET_KEY` for `webui`. Don't put them in the compose file.
- **Images.** Most stacks use rolling tags (`latest`, `main`), so updating means re-pulling. Local images such as `reclip:latest` exist only on the host and must never be re-pulled.
- **Real stack vs copy.** Portainer holds the real stack. The stack files in this repo and in each README are copies, so keep them in sync. Each README has a "Last updated" date at the bottom.

## Updating a stack

1. Edit the stack's `compose.yml` (and its README, if needed) in this repo, then commit and push.
2. In Portainer, open Stacks, then the stack, and click **Pull and redeploy** to pick up the change from GitHub.
3. Turn **Re-pull image and redeploy** on when you want newer images, except for `snapotter`, where it must stay off (see its README).
4. Update the "Last updated" date in the stack's README when you change it.

## When nedpi's Tailscale IP changes

The current IP is `100.96.62.97`. It is written into several files, so a change breaks things in more than one place. A stack that binds to a stale IP fails to start with `cannot assign requested address`.

| Where           | What to update |
|-----------------|----------------|
| `ollama`        | The first `ports:` line |
| `webui`         | The second `ports:` line of `open-web-ui`, and `WEBUI_URL` |
| `snapotter`     | Both `ports:` lines (`snapotter` and `reclip`) |
| `hindsight`     | The `ports:` lines, and the Ollama base URL (`http://<ip>:11434/v1`) |
| `immich` (brick) | The machine learning URL in Immich's admin settings (`http://<ip>:3003`) |

Run `tailscale ip -4` on nedpi to get the new address.

## Common errors

| Error on deploy | Meaning | Fix |
|-----------------|---------|-----|
| `network ai-net declared as external, but could not be found` | The shared network does not exist | Create it (see Fresh install), then redeploy |
| `cannot assign requested address` | The Tailscale IP in the stack file is not on the host: the IP changed, or `tailscaled` is down | Run `tailscale ip -4` and update the files in the table above. If nothing prints, start Tailscale first |
| `No such image` for a local image | The image was built on the host and is missing | Rebuild it (see the stack's README), then redeploy |
| `port is already allocated` or `container name ... is already in use` | An old stack or container still holds the name or port | Delete the old stack, then redeploy |

Stack-specific problems are in each stack's README.

---
Last updated: 2026-11-08
