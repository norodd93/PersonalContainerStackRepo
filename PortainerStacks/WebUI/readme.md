# Open WebUI + SearXNG stack (nedpi)

Portainer stack `webui` on nedpi (Raspberry Pi 5). It runs Open WebUI, the chat frontend, plus SearXNG for web search and a small proxy in front of OpenCode Go. The local models come from the separate `ollama` stack. Open WebUI is reachable over the tailnet only.

## What's in the stack

| Service        | Image                                | Port | What it does |
|----------------|--------------------------------------|-----:|--------------|
| open-web-ui    | `ghcr.io/open-webui/open-webui:main` | 3001 | Chat web UI. Talks to Ollama for models, to SearXNG for web search and to `opencode-proxy` for the cloud models |
| searxng        | `searxng/searxng:latest`             | 8888 | Metasearch engine that Open WebUI queries for web results |
| opencode-proxy | `python:3.12-slim`                   | 9000 | Adds the `x-opencode-session` header OpenCode Go requires. Internal only |

## How it works

Open WebUI connects to three things:

- **Ollama** at `http://ollama:11434`. This is a different stack, so the connection goes over the external Docker network `ai-net`, which both stacks join.
- **SearXNG** at `http://searxng:8080`. This stays inside the `webui` stack's own network. SearXNG is not on `ai-net`.
- **opencode-proxy** at `http://opencode-proxy:9000/v1`, also inside the stack's own network. This is the OpenAI-compatible connection to OpenCode Go.

OpenCode Go rejects any request that does not carry an `x-opencode-session` header with `400 missing_session_id`. Open WebUI has no field for custom provider headers, so it cannot send that header itself. `opencode-proxy` is a small standard-library Python script (`opencode-proxy.py` in this folder, mounted read-only into the container) that forwards `/v1/models` and `/v1/chat/completions` to OpenCode Go and adds the header. It hashes the model plus the first user message into `ses_<32 hex>`, so every turn of one chat gets the same id and separate chats get different ones, which is what keeps OpenCode Go's prompt cache warm. It holds the API key, so the key never has to be stored in Open WebUI.

Only `deepseek-v4.1-flash`, `glm-5.3`, `glm-5.3-flash`, `glm-5.2`, `kimi-k3`, `kimi-k3.1-pro`, `kimi-k2.7-code`, `longcat-2.0`, `longcat-2.5-free`, `step-5-preview`, `mimo-*`, `minimax-m3.1-flash`, `hy3`, `hy4`, `beam-free` and `iceman-contributor-free` speak Chat Completions. Grok 4.7, GPT 6/5.6 Luna and Muse Spark only answer on `/responses`, and MiniMax M3, Qwen3.x and Claude Haiku 5.5 only on Anthropic `/messages`, so they fail through this path. Filter the rest out with Open WebUI's model filter instead of letting users hit errors.

When web search is switched on in a chat, Open WebUI sends the query to SearXNG and gets 3 results back (up to 3 requests at once). It hands them to the model as context. Sign-up is off, so new accounts can't be created from the login page. Add users in the admin panel instead.

Open WebUI no longer waits for Ollama on startup, because a stack can't depend on a service in another stack. If Open WebUI starts first, the model list is empty until the `ollama` stack is up.

## Access

Open WebUI is bound to nedpi's Tailscale IP, so it is not reachable from the LAN.

- Open WebUI: http://100.96.62.97:3001 (also http://127.0.0.1:3001 on nedpi)
- SearXNG: http://127.0.0.1:8888, on nedpi only. It is not published on the tailnet.
- opencode-proxy: not published at all. Only `open-web-ui` can reach it, on the stack's internal network.

Check the current IP with `tailscale ip -4`.

## Storage

Everything lives on the system disk under `/home/norod/docker/ai`.

| Folder           | Used by        | Contents |
|------------------|----------------|----------|
| `openwebui`      | open-web-ui    | Accounts, chats, settings, uploads (mounted at `/app/backend/data`) |
| `searxng`        | searxng        | SearXNG `settings.yml` and config (mounted at `/etc/searxng`) |
| `opencode-proxy` | opencode-proxy | A copy of `opencode-proxy.py` as `proxy.py` (mounted read-only at `/app`) |

Let Docker create these folders on first start, except `opencode-proxy`. That one needs the script inside it before the container starts, see step 3 below. Don't create them by hand as `norod`. The folders from the old `llm` stack are reused as they are, so nothing needs to be moved or migrated.

## Settings that matter

- `WEBUI_SECRET_KEY` is the only required variable in Portainer. Use the same value on every redeploy. A new value logs everyone out.
- `OPENCODE_GO_KEY` is the OpenCode Go API key, from https://opencode.ai/console. Leave it empty if you don't use OpenCode Go, and leave the connection out of Open WebUI.
- The proxy script lives in this repo (`opencode-proxy.py`) but is mounted from `/home/norod/docker/ai/opencode-proxy/proxy.py`, because a Git-based Portainer stack cannot use a relative `build:` context without the Business edition. Re-copy it after every change, see Updating.
- `WEBUI_URL` holds the Tailscale IP. Update it if the IP changes.
- `OLLAMA_BASE_URL=http://ollama:11434` depends on the container name `ollama` and on both stacks being on `ai-net`.
- Open WebUI saves some of its settings in its database after the first start. Editing an environment variable later may then change nothing. If that happens, change it in the admin settings instead (Admin Panel, Settings, Connections for the Ollama URL and the OpenCode Go connection).
- The SearXNG container drops all Linux capabilities except `CHOWN`, `SETGID` and `SETUID`. Don't remove those three, or it fails to start.
- The external network `ai-net` must exist before the stack is deployed. Portainer does not create it.

## Setting it up

Do these in order. The `ollama` stack must exist first, because it is the one that holds the models and the shared network.

1. Create the `ai-net` network and deploy the `ollama` stack (see its README).
2. If the old `llm` stack is still running, delete it. The container names and ports 3001 and 8888 are already taken by it.
3. Put the proxy script where the stack mounts it. Run this on nedpi from a checkout of this repo:
   ```bash
   sudo install -Dm644 PortainerStacks/WebUI/opencode-proxy.py /home/norod/docker/ai/opencode-proxy/proxy.py
   ```
4. In Portainer: Stacks, Add stack, choose **Repository**, and name it `webui`. Set **Repository URL** to `https://github.com/norodd93/PersonalContainerStackRepo.git`, **Repository reference** to `refs/heads/main`, and **Compose path** to `PortainerStacks/WebUI/compose.yml`.
5. Under Environment variables, add `WEBUI_SECRET_KEY`. Reuse the old value if you have one. For a fresh install, generate one with `openssl rand -hex 32`. Add `OPENCODE_GO_KEY` too, with your OpenCode Go key, if you want the cloud models.
6. Click **Deploy the stack**, then open http://100.96.62.97:3001 and check that the model list loads.
7. Add the OpenCode Go connection: **Admin Panel, Settings, Connections, OpenAI API**. Set the URL to `http://opencode-proxy:9000/v1`, the key to any dummy value such as `sk-local` (the proxy holds the real one), and the API type to **Chat Completions**. Verify it with the refresh button. Use **Model IDs (Filter)** to keep only the Chat Completions models listed above.

## Updating the stack

Open WebUI uses the rolling `main` tag, and a newer version can change the database format. Back up the data folder before you re-pull the image, because going back to an older version afterwards may not work:

```bash
sudo cp -a /home/norod/docker/ai/openwebui /home/norod/docker/ai/openwebui.bak
```

1. Edit `PortainerStacks/WebUI/compose.yml` (and this README, if needed) in the repo, then commit and push.
2. If you changed `opencode-proxy.py`, copy it to the host again before redeploying, or the container keeps running the old script:
   ```bash
   sudo install -Dm644 PortainerStacks/WebUI/opencode-proxy.py /home/norod/docker/ai/opencode-proxy/proxy.py
   sudo docker restart opencode-proxy
   ```
3. In Portainer, open Stacks, then `webui`, and click **Pull and redeploy**.
4. Turn **Re-pull image and redeploy** on to get newer Open WebUI and SearXNG images, because the tags are `main` and `latest`.

## Troubleshooting

| Problem | Meaning | Fix |
|---------|---------|-----|
| `network ai-net declared as external, but could not be found` on deploy | The shared network does not exist | Create it (see the `ollama` README), then redeploy |
| `cannot assign requested address` on port 3001 | The Tailscale IP in the stack file is not on nedpi: the IP changed, or `tailscaled` is down | Run `tailscale ip -4`. If the IP differs, update the second `ports:` line and `WEBUI_URL`. If nothing prints, start Tailscale first |
| `container name "/open-web-ui" is already in use` or `port is already allocated` | The old `llm` stack is still running | Delete the old stack, then redeploy |
| No models in Open WebUI | The `ollama` stack is down, or the containers are not on the same network | Check that `ollama` is running, then run `sudo docker network inspect ai-net` and look for both `ollama` and `open-web-ui` |
| Web search fails with a 403 or no results | SearXNG may not be returning JSON, which Open WebUI needs | Check that `search.formats` in `/home/norod/docker/ai/searxng/settings.yml` includes `json`, then restart the stack |
| `400 missing_session_id` in the chat | Open WebUI is talking to OpenCode Go directly, so no `x-opencode-session` header is sent | Point the connection at `http://opencode-proxy:9000/v1` instead of `https://opencode.ai/...` (step 7) |
| `ModelProtocolUnsupported` or a 401 for one model but not others | That model is not served on `/chat/completions` (Grok, GPT Luna, Muse Spark use `/responses`; MiniMax M3, Qwen3.x, Claude Haiku use `/messages`) | Use one of the Chat Completions models, and filter the rest out in the connection settings |
| `opencode-proxy` is restarting, logs say `OPENCODE_GO_KEY is not set` | The Portainer environment variable is missing or empty | Add it to the stack's environment variables and redeploy |
| `opencode-proxy` is restarting, logs show `can't open file '/app/proxy.py'` | The bind-mounted folder has no script in it | Run the `install` command from step 3, then redeploy |

If the Tailscale IP changes again, update it in the second `ports:` line and in `WEBUI_URL` below. The `ollama` stack has the same IP in its own file.

## Stack file (copy)

Portainer holds the real stack. This is a copy, so keep it in sync when you edit the stack.

```yaml
services:
  searxng:
    image: searxng/searxng:latest
    container_name: searxng
    restart: unless-stopped
    environment:
      - SEARXNG_BASE_URL=http://searxng:8080/
    volumes:
      - /home/norod/docker/ai/searxng:/etc/searxng:rw
    ports:
      - "127.0.0.1:8888:8080"
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - SETGID
      - SETUID

  opencode-proxy:
    image: python:3.12-slim
    container_name: opencode-proxy
    restart: unless-stopped
    command: ["python", "-u", "/app/proxy.py"]
    environment:
      - OPENCODE_GO_KEY=${OPENCODE_GO_KEY}
      - PORT=9000
    volumes:
      - /home/norod/docker/ai/opencode-proxy:/app:ro
    expose:
      - "9000"
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9000/health').read()"]
      interval: 30s
      timeout: 5s
      retries: 3
    read_only: true
    tmpfs:
      - /tmp
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true

  open-web-ui:
    image: ghcr.io/open-webui/open-webui:main
    container_name: open-web-ui
    restart: unless-stopped
    depends_on:
      - searxng
      - opencode-proxy
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
      - ENABLE_SIGNUP=false
      - WEBUI_SECRET_KEY=${WEBUI_SECRET_KEY}
      - WEBUI_URL=http://100.96.62.97:3001
      - ENABLE_WEB_SEARCH=true
      - WEB_SEARCH_ENGINE=searxng
      - SEARXNG_QUERY_URL=http://searxng:8080/search?q=<query>
      - WEB_SEARCH_RESULT_COUNT=3
      - WEB_SEARCH_CONCURRENT_REQUESTS=3
    volumes:
      - /home/norod/docker/ai/openwebui:/app/backend/data:rw
    ports:
      - "127.0.0.1:3001:8080"
      - "100.96.62.97:3001:8080"
    networks:
      - default
      - ai-net

networks:
  ai-net:
    external: true
```

---
Last updated: 2026-11-10
