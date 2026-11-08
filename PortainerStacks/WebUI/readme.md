# Open WebUI + SearXNG stack (nedpi)

Portainer stack `webui` on nedpi (Raspberry Pi 5). It runs Open WebUI, the chat frontend, and SearXNG, the search engine behind its web search. The models come from the separate `ollama` stack. Open WebUI is reachable over the tailnet only.

## What's in the stack

| Service     | Image                                | Port | What it does |
|-------------|--------------------------------------|-----:|--------------|
| open-web-ui | `ghcr.io/open-webui/open-webui:main` | 3001 | Chat web UI. Talks to Ollama for models and to SearXNG for web search |
| searxng     | `searxng/searxng:latest`             | 8888 | Metasearch engine that Open WebUI queries for web results |

## How it works

Open WebUI connects to two things:

- **Ollama** at `http://ollama:11434`. This is a different stack, so the connection goes over the external Docker network `ai-net`, which both stacks join.
- **SearXNG** at `http://searxng:8080`. This stays inside the `webui` stack's own network. SearXNG is not on `ai-net`.

When web search is switched on in a chat, Open WebUI sends the query to SearXNG and gets 3 results back (up to 3 requests at once). It hands them to the model as context. Sign-up is off, so new accounts can't be created from the login page. Add users in the admin panel instead.

Open WebUI no longer waits for Ollama on startup, because a stack can't depend on a service in another stack. If Open WebUI starts first, the model list is empty until the `ollama` stack is up.

## Access

Open WebUI is bound to nedpi's Tailscale IP, so it is not reachable from the LAN.

- Open WebUI: http://100.96.62.97:3001 (also http://127.0.0.1:3001 on nedpi)
- SearXNG: http://127.0.0.1:8888, on nedpi only. It is not published on the tailnet.

Check the current IP with `tailscale ip -4`.

## Storage

Everything lives on the system disk under `/home/norod/docker/ai`.

| Folder      | Used by     | Contents |
|-------------|-------------|----------|
| `openwebui` | open-web-ui | Accounts, chats, settings, uploads (mounted at `/app/backend/data`) |
| `searxng`   | searxng     | SearXNG `settings.yml` and config (mounted at `/etc/searxng`) |

Let Docker create these folders on first start. Don't create them by hand as `norod`. The folders from the old `llm` stack are reused as they are, so nothing needs to be moved or migrated.

## Settings that matter

- `WEBUI_SECRET_KEY` is the only variable to set in Portainer. Use the same value on every redeploy. A new value logs everyone out.
- `WEBUI_URL` holds the Tailscale IP. Update it if the IP changes.
- `OLLAMA_BASE_URL=http://ollama:11434` depends on the container name `ollama` and on both stacks being on `ai-net`.
- Open WebUI saves some of its settings in its database after the first start. Editing an environment variable later may then change nothing. If that happens, change it in the admin settings instead (Admin Panel, Settings, Connections for the Ollama URL).
- The SearXNG container drops all Linux capabilities except `CHOWN`, `SETGID` and `SETUID`. Don't remove those three, or it fails to start.
- The external network `ai-net` must exist before the stack is deployed. Portainer does not create it.

## Setting it up

Do these in order. The `ollama` stack must exist first, because it is the one that holds the models and the shared network.

1. Create the `ai-net` network and deploy the `ollama` stack (see its README).
2. If the old `llm` stack is still running, delete it. The container names and ports 3001 and 8888 are already taken by it.
3. In Portainer: Stacks, Add stack, choose **Repository**, and name it `webui`. Set **Repository URL** to `https://github.com/norodd93/PersonalContainerStackRepo.git`, **Repository reference** to `refs/heads/main`, and **Compose path** to `PortainerStacks/WebUI/compose.yml`.
4. Under Environment variables, add `WEBUI_SECRET_KEY`. Reuse the old value if you have one. For a fresh install, generate one with `openssl rand -hex 32`.
5. Click **Deploy the stack**, then open http://100.96.62.97:3001 and check that the model list loads.

## Updating the stack

Open WebUI uses the rolling `main` tag, and a newer version can change the database format. Back up the data folder before you re-pull the image, because going back to an older version afterwards may not work:

```bash
sudo cp -a /home/norod/docker/ai/openwebui /home/norod/docker/ai/openwebui.bak
```

1. Edit `PortainerStacks/WebUI/compose.yml` (and this README, if needed) in the repo, then commit and push.
2. In Portainer, open Stacks, then `webui`, and click **Pull and redeploy**.
3. Turn **Re-pull image and redeploy** on to get newer Open WebUI and SearXNG images, because the tags are `main` and `latest`.

## Troubleshooting

| Problem | Meaning | Fix |
|---------|---------|-----|
| `network ai-net declared as external, but could not be found` on deploy | The shared network does not exist | Create it (see the `ollama` README), then redeploy |
| `cannot assign requested address` on port 3001 | The Tailscale IP in the stack file is not on nedpi: the IP changed, or `tailscaled` is down | Run `tailscale ip -4`. If the IP differs, update the second `ports:` line and `WEBUI_URL`. If nothing prints, start Tailscale first |
| `container name "/open-web-ui" is already in use` or `port is already allocated` | The old `llm` stack is still running | Delete the old stack, then redeploy |
| No models in Open WebUI | The `ollama` stack is down, or the containers are not on the same network | Check that `ollama` is running, then run `sudo docker network inspect ai-net` and look for both `ollama` and `open-web-ui` |
| Web search fails with a 403 or no results | SearXNG may not be returning JSON, which Open WebUI needs | Check that `search.formats` in `/home/norod/docker/ai/searxng/settings.yml` includes `json`, then restart the stack |

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

  open-web-ui:
    image: ghcr.io/open-webui/open-webui:main
    container_name: open-web-ui
    restart: unless-stopped
    depends_on:
      - searxng
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
Last updated: 2026-11-08
