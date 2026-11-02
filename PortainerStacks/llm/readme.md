# LLM stack (nedpi)

Portainer stack `llm` on nedpi (Raspberry Pi 5). It runs Ollama, SearXNG and Open WebUI together, so Open WebUI can chat with local models and search the web through SearXNG. The web UI is reachable over the tailnet only.

## What's in the stack

| Service    | Port on nedpi | What it does |
|------------|--------------:|--------------|
| Open WebUI | 3001 (Tailscale IP) | Chat UI. Talks to Ollama and SearXNG |
| Ollama     | none | Runs the models. Open WebUI reaches it inside the stack as `http://ollama:11434` |
| SearXNG    | 8888 (localhost only) | Search backend for Open WebUI. Open WebUI reaches it as `http://searxng:8080/search?q=<query>`. The localhost port is for testing only |

The names `ollama` and `searxng` only work between containers inside the stack. They don't resolve on the Pi itself.

## Access

Open WebUI: http://100.96.62.97:3001

Check the current IP with `tailscale ip -4`.

## Where things live

- **Compose file:** GitHub repo `norodd93/PersonalContainerStackRepo`.
- **Data:** the system disk, not the HDD.

| Folder                          | Used by    | Contents |
|---------------------------------|------------|----------|
| `/home/norod/docker/ai/ollama`    | Ollama     | Downloaded models. It grows with every model you pull, so check it with `du -sh` now and then |
| `/home/norod/docker/ai/searxng`   | SearXNG    | Config, including `settings.yml` |
| `/home/norod/docker/ai/openwebui` | Open WebUI | App data, users and settings |

## Settings that matter

- **`WEBUI_SECRET_KEY`** is the only Portainer variable. Set it in the stack's environment variables and keep its value out of the repo.
- **SearXNG must allow JSON.** `/home/norod/docker/ai/searxng/settings.yml` needs `json` under `search.formats`. Without it, web search in Open WebUI fails with HTTP 403.
- **Web search settings in the compose file only apply on the first start**, with an empty `openwebui` data folder. After that, change them in Open WebUI under Admin Panel → Settings → Web Search. Editing the compose file won't change them.

The relevant part of `settings.yml` is shown below. This is only a fragment, so merge it into your existing file and don't replace the whole file with it:

```yaml
search:
  formats:
    - html
    - json
```

## Giving other apps access to Ollama

Ollama has no published port by default, so nothing outside the stack can reach it. To let other apps use it, add these two lines under `ports` for the `ollama` service in the compose file:

Use exactly these two addresses. Ollama has no login, so don't publish it on `0.0.0.0`. That would expose it to your whole LAN.

```yaml
  ollama:
    ports:
      - "100.96.62.97:11434:11434"
      - "127.0.0.1:11434:11434"
```

The first line is for other devices on the tailnet and the second is for apps on the Pi itself.

## Updating the stack

1. Change the compose file in the repo, commit and push.
2. Redeploy the `llm` stack in Portainer.

## If the Tailscale IP changes

Update the IP in the compose file, in `WEBUI_URL` and in every `ports` entry that uses it, then redeploy. Get the new IP from `tailscale ip -4`.

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Web search in Open WebUI returns HTTP 403 | SearXNG isn't allowed to return JSON | Add `json` under `search.formats` in `/home/norod/docker/ai/searxng/settings.yml`, then restart SearXNG. Test with `curl "http://127.0.0.1:8888/search?q=test&format=json"` on the Pi |
| Deploy fails with `cannot assign requested address` | The Tailscale IP in the compose file isn't on nedpi: the IP changed, or `tailscaled` is down | Run `tailscale ip -4`. If the IP differs, update it (see above). If nothing prints, start Tailscale first |
| Changed a web search setting in the compose file and nothing happened | These settings only apply on the first start | Change it in Admin Panel → Settings → Web Search |

---
Last updated: 2026-11-02
