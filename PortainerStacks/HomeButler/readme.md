# HomeButler stack (nedpi)

Portainer stack `homebutler` on nedpi (Raspberry Pi 5). It runs the HomeButler web dashboard, which reports what changed on the servers it watches — not just what is running now. The dashboard is reachable over the tailnet only.

## What's in the stack

| Service   | Image                               | Port                              | What it does |
|-----------|-------------------------------------|-----------------------------------|--------------|
| homebutler | `ghcr.io/higangssh/homebutler:latest` | [8081](http://100.96.62.97:8081) | Web dashboard and API; reaches the servers in `config.yaml` over SSH |

## How it works

The image is the hub, not the probe. A container cannot see the machine it runs on: `status` would read the container's own `/proc`, and a server marked `local: true` is reported as not visible rather than answered with the container's numbers. To report on nedpi, add it to `servers:` in the config and reach it over SSH, with the `homebutler` binary installed on nedpi.

The container reads its config from `/config/config.yaml` and keeps snapshots and watch incidents in `/root/.homebutler`. Both are bind-mounted so they survive a restart; without the state mount, a restart turns "what changed" into "everything is new".

The dashboard can only write to a config file that already exists, so `/config/config.yaml` is created once during setup. `homebutler init` inside the image writes to `/root/.config/homebutler/config.yaml` instead, which is not the mounted path, so it does not create the file the dashboard reads.

## Access

- From the tailnet: [http://100.96.62.97:8081](http://100.96.62.97:8081)

The port is bound to nedpi's Tailscale IP, so it is not reachable from the LAN. Check the current IP with `tailscale ip -4`. The container listens on 8080 internally; it is published as 8081 on the host because glance already uses 8080 on nedpi.

## Variables

Set these in Portainer when deploying the stack. There is no `.env` file in the repo — secrets belong in Portainer's stack variables.

| Variable           | Required | What it is |
|--------------------|----------|------------|
| `HOMEBUTLER_TOKEN` | yes      | Bearer token for the dashboard and every `/api/*` route. Generate one with `openssl rand -hex 24` |

`serve` refuses to bind beyond `127.0.0.1` without a token, and an empty value counts as unset, so the container will not start until the variable is filled in. The token crosses the network in clear, so keep the port on the tailnet, or put a reverse proxy with TLS in front of it.

## Setting it up

1. Generate a token: `openssl rand -hex 24`.
2. In Portainer: Stacks, Add stack, choose **Repository**. Name it `homebutler`, set **Repository URL** to `https://github.com/norodd93/PersonalContainerStackRepo.git`, **Repository reference** to `refs/heads/main`, and **Compose path** to `PortainerStacks/HomeButler/compose.yml`. Add `HOMEBUTLER_TOKEN` under environment variables, then click **Deploy the stack**.
3. Create the config file the dashboard saves to, then restart the container so `serve` picks it up. On nedpi:
   ```bash
   sudo mkdir -p /home/norod/docker/homebutler/config
   echo 'servers: []' | sudo tee /home/norod/docker/homebutler/config/config.yaml
   sudo chmod 600 /home/norod/docker/homebutler/config/config.yaml
   sudo docker restart homebutler
   ```
   Without this file the Config tab says "there is no config file to write", and `homebutler init` does not fix it (see How it works).
4. Open [http://100.96.62.97:8081](http://100.96.62.97:8081) and sign in with the token. Reload the page if the banner about the config file changing on disk is still there.
5. Install the `homebutler` binary on every server you want to watch. On nedpi:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/Higangssh/homebutler/main/install.sh | sh
   ```
   Or, from a machine that already has your key, deploy it remotely with `homebutler deploy --server <name>`. An older binary on the far side fails with `unknown command`; upgrade it there.
6. Add the servers on the dashboard's **Config** tab. With a token set, the settings screen is editable. The container cannot resolve the host's own hostname, so use its Tailscale IP in **Host**. A minimal `config.yaml` for the two hosts:
   ```yaml
   servers:
     - name: nedpi
       host: 100.96.62.97
       user: norod
       key: ~/.ssh/id_ed25519
     - name: brick
       host: 100.65.227.39
       user: norod
       key: ~/.ssh/id_ed25519
   ```
   `~` resolves to `/root` in the container, which is where the host's `.ssh` is mounted. Use `id_rsa` if that is the key you have. Once the settings screen has written the file, check it from nedpi with `homebutler config validate --config /home/norod/docker/homebutler/config/config.yaml`, or from inside the container with `sudo docker exec homebutler homebutler config validate`.
7. Make sure the container's key is allowed in on each server. It connects as `norod` with your `~/.ssh/id_ed25519`, so that key's public half has to be in `~norod/.ssh/authorized_keys` there. On nedpi:
   ```bash
   cat ~/.ssh/id_ed25519.pub >> ~/.ssh/authorized_keys
   chmod 600 ~/.ssh/authorized_keys
   ```
8. Trust the hosts the first time. The SSH mount is read-only, so a host that is not in `known_hosts` fails instead of being trusted silently. On nedpi, with `~/.ssh` writable:
   ```bash
   ssh-keyscan -H 100.96.62.97 >> ~/.ssh/known_hosts
   ```
   Or use the CLI, pointing it at the mounted config: `homebutler trust --config /home/norod/docker/homebutler/config/config.yaml nedpi`. Restart the container afterwards: `sudo docker restart homebutler`.

The dashboard does not watch its own host. If you want nedpi's own CPU, disks and containers in it, add nedpi over SSH as above; the alternative is running the binary directly on nedpi outside the container.

## Storage

Everything lives on the system disk under `/home/norod/docker/homebutler`.

| Folder    | Used by    | Contents |
|-----------|------------|----------|
| `config`  | homebutler | `config.yaml`, written by the settings screen |
| `state`   | homebutler | Report snapshots and watch incidents (`/root/.homebutler`) |

The stack also mounts `/home/norod/.ssh` read-only at `/root/.ssh`, for the private key and `known_hosts` used to reach the servers.

Let Docker create the two folders on first start. Don't create them by hand as `norod`. For a dedicated key instead of your main one, generate a keypair under `/home/norod/docker/homebutler/ssh`, add it to the servers' `authorized_keys`, and point the third volume at that folder.

## Updating the stack

1. Edit `PortainerStacks/HomeButler/compose.yml` (and this README, if needed) in the repo, then commit and push.
2. In Portainer, open Stacks, then `homebutler`, and click **Pull and redeploy**.
3. Turn **Re-pull image and redeploy** on to get a newer HomeButler, because the tag is `latest`.

The config and snapshots in `/home/norod/docker/homebutler` are kept.

## Operations and useful commands

**Current setup (runtime/host state, not stored in this repo):**
- **Dashboard:** [http://100.96.62.97:8081](http://100.96.62.97:8081) (tailnet, token required).
- **Monitored servers:** `nedpi` (`100.96.62.97`) and `brick` (`100.65.227.39`) over SSH (hub config in `/home/norod/docker/homebutler/config/config.yaml`).
- **Watch services:** installed on both hosts (`homebutler watch install`, systemd user units) monitoring selected local Docker containers and recording incidents/history. On `nedpi` the watch list contains only running containers (`homebutler`, `immich_machine_learning`, `portainer`); the AI-stack rule was removed on 2026-11-12 because its containers were intentionally stopped (see [Notifications keep arriving for a stopped container](#notifications-keep-arriving-for-a-stopped-container)).
- **Notifications:** Telegram configured (`watch.notify_on: incident`, `cooldown: 5m`); keep secrets in host configs/Portainer, not in this repo.
- **Reports:** baselines/snapshots in `/home/norod/docker/homebutler/state`; daily `report --all` cron on `nedpi` at 07:00 (`docker exec homebutler homebutler report --all`).

**From nedpi (hub/container commands):**
```bash
# Overview across servers
sudo docker exec homebutler homebutler status --all
sudo docker exec homebutler homebutler report --all          # save snapshot/changes
sudo docker exec homebutler homebutler report --all --no-save
sudo docker exec homebutler homebutler doctor --server nedpi
sudo docker exec homebutler homebutler doctor --server brick

# Details
sudo docker exec homebutler homebutler ports --server nedpi
sudo docker exec homebutler homebutler ports --server brick
sudo docker exec homebutler homebutler docker list --server nedpi
sudo docker exec homebutler homebutler docker list --server brick

# Config & notifications
sudo docker exec homebutler homebutler config validate
sudo docker exec homebutler homebutler notify test
```

**On each host (`nedpi` / `brick`, local):**
```bash
# Watch (monitoring/restarts)
homebutler watch list
homebutler watch check
homebutler watch history        # or: incidents
homebutler watch show <id>
homebutler watch installed
homebutler watch add --kind docker <container>   # then reinstall/restart watcher

# Local config/notify
homebutler config validate
homebutler notify test
```

**Tuning knobs:**
- **Notification volume:** change `watch.notify_on` (`incident` / `flapping` / `all` / `off`) and/or `cooldown` in config, then restart the hub container and reinstall/restart host watchers.
- **Thresholds:** adjust `alerts.cpu`, `alerts.memory`, `alerts.disk` in config.
- **Rules:** add/edit `alerts.rules` (e.g. per-container notify/restart) in the relevant host config (and keep hub/host configs in sync as desired), then restart watchers. Only list containers that should be running: a missing container with `action: restart` notifies every 30s and cannot recover.
- **Reports:** adjust the daily cron with `crontab -e` on `nedpi`.

Host-side watch/config files live in `~/.config/homebutler/` on each host and in `/home/norod/docker/homebutler/config/config.yaml` for the hub; keep secrets out of this repo.

## Troubleshooting

### Notifications keep arriving for a stopped container

`homebutler watch remove <container>` only edits the watch list in
`~/.homebutler/watch/targets.json`. It does not edit `alerts.rules`, and every
rule has its own `watch:` list under `alerts:`. A container that no longer exists
in Docker but is still named in a rule is checked every 30 seconds; the
`action: restart` step fails because there is nothing to restart, and each
failure sends a notification. Removing containers from the watch list makes the rule move on to
the next missing container, which is why the messages can seem to ignore the
removal.

On `nedpi` the notifier is the host watcher (`dev.homebutler.watch.service`,
config `~/.config/homebutler/config.yaml`), not the Portainer container. The
container has its own copy at `/home/norod/docker/homebutler/config/config.yaml`;
editing one does not change the other. Keep both in sync if the dashboard should
show the same rules.

To stop it:

1. Remove the stopped containers from every `alerts.rules[].watch` list, or remove
   the rule entirely:
   ```yaml
   alerts:
     rules: []
   ```
2. Remove them from the watch list:
   ```bash
   homebutler watch remove <container>
   ```
3. Restart the host watcher so it reads both files again:
   ```bash
   systemctl --user restart dev.homebutler.watch.service
   ```
4. Confirm the last entry in `~/.homebutler/alerts-history.json` stops moving.

Putting a container in `alerts.rules` is an instruction to restart it when it is
missing, so only list containers that should be running. `homebutler watch list`
on its own only records restarts and incidents; it never restarts anything.

| Error on deploy or in the logs | Meaning | Fix |
|--------------------------------|---------|-----|
| `set HOMEBUTLER_TOKEN` or the container exits at once | The variable is missing, or empty | Add `HOMEBUTLER_TOKEN` in Portainer, then redeploy |
| `there is no config file to write; run homebutler init first` | `/config/config.yaml` does not exist, so the dashboard has nothing to save to | Create it (see Setting it up), then restart the container |
| `Permission denied (publickey)` from a server | The container's key is not in that server's `authorized_keys` | Add the public half of `~/.ssh/id_ed25519` to `~norod/.ssh/authorized_keys` on the server |
| `cannot assign requested address` on port 8081 | The Tailscale IP in the stack file is not on nedpi: the IP changed, or `tailscaled` is down | Run `tailscale ip -4`. If the IP differs, update the `ports:` line. If nothing prints, start Tailscale first |
| `port is already allocated` | Another container already holds 8081 | Stop it, or change the host port in the `ports:` line |
| A server shows as not visible | It is the machine the container runs on | Add it over SSH with the binary installed, as in Setting it up |
| `unknown command` from a server | The `homebutler` binary on that server is older than the dashboard | Upgrade it on that server |
| SSH host key verification failed | The host is not in `known_hosts`, and the mount is read-only | Run `homebutler trust <name>` on the host, then restart the container |
| The settings screen will not save | No token is set, so the dashboard is read-only | Set `HOMEBUTLER_TOKEN` in Portainer |

## Stack file (copy)

Portainer deploys this file from the repo. The copy below is for reference, so keep it in sync when you edit the stack.

```yaml
# HomeButler dashboard on nedpi.
# The container is the hub, not the probe: it reaches the servers listed in
# config.yaml over SSH, so the host's SSH keys are mounted read-only.
# Required variable in Portainer: HOMEBUTLER_TOKEN (the dashboard API token).
services:
  homebutler:
    image: ghcr.io/higangssh/homebutler:latest
    container_name: homebutler
    restart: unless-stopped
    ports:
      # The container listens on 8080, which glance already publishes on nedpi
      - "100.96.62.97:8081:8080"
    environment:
      - HOMEBUTLER_TOKEN=${HOMEBUTLER_TOKEN:?set HOMEBUTLER_TOKEN}
    volumes:
      - /home/norod/docker/homebutler/config:/config
      - /home/norod/docker/homebutler/state:/root/.homebutler
      - /home/norod/.ssh:/root/.ssh:ro
```

---
Last updated: 2026-11-12
