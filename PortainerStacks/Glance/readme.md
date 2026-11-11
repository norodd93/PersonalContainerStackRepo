# Glance dashboard stack (nedpi and brick)

Portainer stack `glance`, deployed on both nedpi (Raspberry Pi 5) and brick from one stack file, `glance-stack.yml`. Each host runs its own Glance dashboard, and each dashboard shows both hosts: CPU, RAM and disk, the running containers, and which container images have updates. Everything is reachable over the tailnet only.

Per-host values (IPs, names, passwords) are Portainer environment variables, so the file in the repo is identical on both hosts and holds no secrets.

## What's in the stack

| Service      | Image                                          |  Port | What it does |
|--------------|------------------------------------------------|------:|--------------|
| glance       | `glanceapp/glance:latest`                      |  [8080](http://100.96.62.97:8080) | The dashboard |
| agent        | `glanceapp/agent:latest`                       | 27973 | Reports this host's CPU, RAM and disk. The other host's Glance reads it too |
| docker-proxy | `ghcr.io/tecnativa/docker-socket-proxy:latest` |  2375 | Gives Glance a read-only view of this host's containers. The other host's Glance reads it too |
| wud          | `getwud/wud:latest`                            |  [3055](http://100.96.62.97:3055) | What's Up Docker. Checks registries for newer images and reports them (container port 3000) |

## How it works

**Servers.** Each Glance reads its own agent at `http://agent:27973` and the other host's agent at `PEER_URL`. Both use the same `AGENT_TOKEN`. The agent mounts `/`, `/var` and `/srv` read-only and hides every disk that is not listed in `DISK_MOUNTPOINTS`.

**Containers.** The container lists come from the Docker API through docker-proxy: locally at `tcp://docker-proxy:2375`, and for the other host at `PEER_DOCKER`. The proxy only allows read requests on containers (`CONTAINERS=1`, `POST` stays off).

**Image updates.** WUD checks the registries once a day at 04:00. Two "Image updates" widgets read its API: the local one at `http://wud:3000`, the other host's at `PEER_WUD_ADDR`. Each lists only the containers WUD has flagged, with name and image. Glance caches the result for 15 minutes, but the data only changes when WUD scans. WUD only reports. No trigger is configured, so it never updates or restarts anything.

**Floating tags.** Most images here use tags like `latest` or `main`. WUD does not watch those for Docker Hub images by default, so the stack sets `WUD_WATCHER_LOCAL_WATCHDIGESTDEFAULT=true`. For those images a flag means the image behind the tag changed on the registry. It does not say which version it is. The cost is more registry requests per scan.

**WUD login.** WUD 9 refuses to start without an admin account. `WUD_ADMIN_USER` and `WUD_ADMIN_PASSWORD` create it (the stack file maps them to `WUD_AUTH_ADMIN_USER` and `WUD_AUTH_ADMIN_PASSWORD`). The Glance widgets sign in with it through the URL (`http://user:pass@host/...`, which is Basic auth). The values are the same on both hosts so each Glance can read the other host's WUD.

**Dashboard config.** There is no separate Glance config file. It is inline in the stack file (`configs: glance_config`), and Compose fills in the `${...}` values on deploy. To change the dashboard, edit the stack file and redeploy.

## Access

- nedpi: [http://100.96.62.97:8080](http://100.96.62.97:8080)
- brick: [http://100.65.227.39:8080](http://100.65.227.39:8080)
- WUD web UI: [http://100.96.62.97:3055](http://100.96.62.97:3055) and [http://100.65.227.39:3055](http://100.65.227.39:3055). Log in with `WUD_ADMIN_USER` and its password.

Every published port is bound to the host's Tailscale IP (`BIND_IP`), so none of them is reachable from the LAN. Docker-published ports bypass ufw, so this binding is the access control. Check the current IP with `tailscale ip -4`.

## Storage

This stack has no data folders. The only mounts are read-only host paths for the agent and the Docker socket for docker-proxy and wud. Glance itself keeps no state. WUD keeps its scan results in `/store` inside its container, and the stack file declares no volume for it.

## Settings that matter

Set these in Portainer under the stack's environment variables. The file marks every one as required, so a deploy stops with `set NAME` if one is missing.

| Variable             | nedpi                       | brick                                         | What it is |
|----------------------|-----------------------------|-----------------------------------------------|------------|
| `BIND_IP`            | `100.96.62.97`              | `100.65.227.39`                               | This host's Tailscale IP. All published ports bind to it |
| `LOCAL_NAME`         | `NedPi`                     | `Brick`                                       | This host's name in the dashboard |
| `PEER_NAME`          | `Brick`                     | `NedPi`                                       | The other host's name |
| `PEER_URL`           | `http://100.65.227.39:27973` | `http://100.96.62.97:27973`                  | The other host's agent |
| `PEER_DOCKER`        | `tcp://100.65.227.39:2375`  | `tcp://100.96.62.97:2375`                     | The other host's docker-proxy |
| `PEER_WUD_ADDR`      | `100.65.227.39:3055`        | `100.96.62.97:3055`                           | The other host's WUD as `host:port`, without `http://` |
| `DISK_MOUNTPOINTS`   | `/host/root:Root`           | `/host/root:Root,/host/var:Var,/host/srv:Srv` | Disks the agent reports, as `path:label`, comma-separated |
| `AGENT_TOKEN`        | secret, same on both        | secret, same on both                          | Shared by both agents and both Glances |
| `WUD_ADMIN_USER`     | `wud`                       | `wud`                                         | WUD admin name. Same on both |
| `WUD_ADMIN_PASSWORD` | secret, same on both        | secret, same on both                          | WUD admin password |

- Never commit real values to the repo. Keep the two secrets in your password manager.
- Use passwords without a `$`, because Compose treats it as a variable. A value from `openssl rand -hex 24` is safe.
- To change a secret, change it on both hosts and redeploy both. Until then the widgets for the other host fail.
- If a Tailscale IP changes, update `BIND_IP` on that host and `PEER_URL`, `PEER_DOCKER` and `PEER_WUD_ADDR` on the other host.

Security notes:

- docker-proxy (2375) has no login. Any device on the tailnet can list this host's containers. It probably also exposes each container's environment variables through inspect (assumed, not verified).
- wud (3055) needs the admin login, but it mounts the real Docker socket, not the proxy. The `:ro` on a socket mount does not make the Docker API read-only. It is safe only because no trigger is configured and the login is required.
- Optional hardening: a Tailscale ACL that limits ports 2375 and 3055 to the other host.

## Setting it up

Do this on each host. The widgets for the other host show errors until both stacks are running.

1. Check that Tailscale is up with `tailscale ip -4`.
2. In Portainer: Stacks, Add stack, choose **Repository**, and name it `glance`. Set **Repository URL** to `https://github.com/norodd93/PersonalContainerStackRepo.git`, **Repository reference** to `refs/heads/main`, and **Compose path** to `PortainerStacks/Glance/glance-stack.yml`.
3. Under Environment variables, add all ten variables from the table above, with this host's column. Generate the two secrets once and reuse the same values on the other host.
4. Click **Deploy the stack**, then open the dashboard on port 8080.

## Updating the stack

1. Run `git pull` in the repo clone you are using. There is one on nedpi and one on the laptop.
2. Edit `PortainerStacks/Glance/glance-stack.yml` (and this README, if needed), then commit and push.
3. If you added a variable, add it in both Portainers first. Otherwise the deploy stops with `set NAME`.
4. In Portainer, open Stacks, then `glance`, and click **Pull and redeploy**. Do it on both hosts.
5. Turn **Re-pull image and redeploy** on to get newer images, because every tag here is `latest`.

The redeploy recreates the containers, so the dashboard is down for a few seconds.

## Troubleshooting

| Problem | Meaning | Fix |
|---------|---------|-----|
| `set WUD_ADMIN_PASSWORD` (or another name) on deploy | The variable is missing or misspelled in this host's Portainer | Add it under the stack's environment variables, then redeploy |
| `cannot assign requested address` | `BIND_IP` is not on this host: the IP changed, or `tailscaled` is down | Run `tailscale ip -4`. If the IP differs, update `BIND_IP`. If nothing prints, start Tailscale first |
| `wud` keeps restarting, log says `Authentication is mandatory` | WUD has no admin account | Set `WUD_ADMIN_USER` and `WUD_ADMIN_PASSWORD`, then redeploy |
| `port is already allocated` | Something else on the host uses the port | Find it with `sudo ss -ltnp \| grep 3055` (or the port in the error), then stop it or change the port |
| The other host's servers or containers are missing | Its agent or docker-proxy is down, `AGENT_TOKEN` differs, or `PEER_URL` / `PEER_DOCKER` is wrong | Check that its stack is running and that both tokens match |
| The other host's "Image updates" widget shows an error | Its WUD is down, `PEER_WUD_ADDR` is wrong, or the WUD password differs | From this host run `curl -sS -u wud http://<peer ip>:3055/api/containers`. It prompts for the password and should print JSON, not an error |
| "All watched images are up to date" but you expect updates | Digest watching is off, or WUD has not scanned yet | Run `curl -sS -u wud http://<ip>:3055/api/containers \| grep -o '"watch":true' \| wc -l`. Zero means digest watching is off, so check the `wud` environment in the stack file |

## Stack file

The stack file is `glance-stack.yml` in this folder. Portainer deploys it straight from the repo, so there is no second copy here to keep in sync.

---
Last updated: 2026-11-11
