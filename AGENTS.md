# AGENTS.md

Self-hosted Docker Compose stacks for two hosts: `nedpi` (Raspberry Pi 5) and `brick` (Debian laptop). There is no application code, test suite, lint, CI, or build step. Do not invent commands for them.

## Deployment model

- Portainer deploys each stack from this repo on `main` (`https://github.com/norodd93/PersonalContainerStackRepo.git`), so **files here are production config**. Pushes are picked up by "Pull and redeploy" in Portainer.
- One stack = one directory under `PortainerStacks/` with a compose file and a README (lowercase `readme.md`, except Dashdot's `README.md`). Portainer is configured with the exact compose path (e.g. `PortainerStacks/WebUI/compose.yml`), so renaming/moving a stack file breaks deployment.
- Directory names are case-sensitive and inconsistent (`snapotter` is lowercase; `Ollama`, `WebUI`, `SyncThing`, `Immich`, `Glance`, `Netbird` are not). Match existing paths exactly.
- Root `portainer.yml` is brick's Portainer bootstrap (CE, `127.0.0.1:9443`, no `8000`); it is not deployed as a Portainer-managed stack. Both hosts serve Portainer on 9443 from loopback via `tailscale serve`; nedpi runs EE.
- `PortainerStacks/OfflineStacks/` holds the undeployed Dashdot stack. It does not follow the live conventions below (it publishes `3101:3001` on all interfaces). Treat it as inactive.
- `PortainerStacks/Netbird/` is also not deployed and uses `network_mode: host` plus a named volume. Its setup-key line is malformed; see its readme before deploying.

## Rules for editing a stack

- Bind published ports to `127.0.0.1` or the host's Tailscale IP — never all interfaces. Docker-published ports bypass ufw, so the bind address *is* the access control. Only documented exceptions: SSH and Syncthing's 22000.
- Persist data with host bind mounts (`/home/norod/docker/<stack>` on nedpi, `/srv/immich/...` on brick), not named volumes. Immich's `model-cache` is the known exception.
- Secrets live in Portainer stack environment variables, never in compose files or committed files. Reference them as `${VAR}`.
- Required variables use `${VAR:?set VAR}`; deploying without them fails with `set VAR`. Avoid `$` in secret values because Compose interpolates it (`openssl rand -hex 24` is safe).
- Do not add `build:` contexts. Community-edition Portainer git stacks cannot build them; this is why `webui` ships `opencode-proxy.py` as a bind-mounted file.
- Containers that must not be update-checked use `wud.watch=false`. Host-built images also need `pull_policy: never` (see `snapotter` / `reclip:latest`).
- Most images use floating tags (`latest`, `main`); "updating" means redeploying with Portainer's **Re-pull image and redeploy**.
- `snapotter` must always redeploy with re-pull **off**. `reclip:latest` exists only on the Pi, and a re-pull aborts the whole stack.

## Stack-specific gotchas

- `PortainerStacks/WebUI/opencode-proxy.py` is in the repo but mounted from `/home/norod/docker/ai/opencode-proxy/proxy.py` on nedpi. Editing the repo file alone changes nothing; re-copy and restart:
  `sudo install -Dm644 PortainerStacks/WebUI/opencode-proxy.py /home/norod/docker/ai/opencode-proxy/proxy.py && sudo docker restart opencode-proxy`
- `ollama` and `webui` share the external `ai-net` network (created once with `sudo docker network create ai-net`) and resolve each other by container name (`http://ollama:11434`). `immich.yml` requires the external `immich_default` network, which this repo does not create.
- Immich is two stacks on two hosts: server on `brick`, machine learning on `nedpi` (`immich-mi.yml`, port 3003). The ML URL is set in Immich's admin UI, not in a compose file.
- Glance has no separate config file: the dashboard YAML is inline under `configs:` in `glance-stack.yml`. The same file deploys on both hosts; per-host differences come from Portainer env vars. `glance-nedpi.env` / `glance-brick.env` are secret-free templates.
- Portainer is not a Portainer-managed stack. Brick's compose project uses `/home/norod/portainer/portainer.yml`; keep that copy in sync with the repo. To change it: `sudo docker rm -f portainer`, then from `~/portainer` run `sudo docker compose -f portainer.yml up -d`. `portainer_data` is external and keeps users/settings; create it once with `sudo docker volume create portainer_data` on a fresh host.

## Tailscale

- IPs are hard-coded: nedpi `100.96.62.97`, brick `100.65.227.39`. Get the current value with `tailscale ip -4`.
- A stale IP fails at deploy with `cannot assign requested address`. The root README lists every file that contains an IP; a change usually touches several stacks, not one.

## Docs and verification

- Every stack has a README ending in `Last updated: YYYY-MM-DD`. Update that date whenever you change the stack or its docs.
- Keep the root README's stack table, ports, and Tailscale table accurate.
- User-facing ports are clickable links in the root stacks table and each stack's Access section; keep new ports linked when you edit.
- Several READMEs embed a "Stack file (copy)" block (Ollama, snapotter, WebUI, Dashdot; Glance has none). Keep the embedded copy identical to the compose file even though Portainer reads the repo file, not the copy; verify after editing.
- No test suite exists. Before committing, check that YAML parses and that `${VAR}` references match the README's variable table. `docker compose config` works only if you supply the required variables first; it fails on unset `${VAR:?...}` values.

## Secrets

- `.env`, `.env.*`, and `*.env` are gitignored. The only tracked env files are `PortainerStacks/Glance/glance-{nedpi,brick}.env`, which are verified secret-free.
- Never commit real values for `AGENT_TOKEN`, `WUD_ADMIN_PASSWORD`, `WEBUI_SECRET_KEY`, or `OPENCODE_GO_KEY`.
- In this environment, shell commands that reference `.env*` paths are blocked; use the EnvSitter tools to inspect those files without printing values.
