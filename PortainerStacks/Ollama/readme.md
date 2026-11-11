# Ollama stack (nedpi)

Portainer stack `ollama` on nedpi (Raspberry Pi 5). It runs Ollama on its own, so models can be updated and loaded without touching the web UI. Ollama is reachable over the tailnet only. Open WebUI (stack `webui`) uses it as its model backend.

## What's in the stack

| Service | Image                  | Port  | What it does |
|---------|------------------------|------:|--------------|
| ollama  | `ollama/ollama:latest` | [11434](http://100.96.62.97:11434) | Runs local LLMs and serves the Ollama API |

## How it works

Ollama listens on port 11434 inside the container. The stack file publishes that port in two places only: nedpi's Tailscale IP and localhost. It is not reachable from the LAN.

The container is attached to the external Docker network `ai-net`, which is shared with the `webui` stack. Containers on `ai-net` reach Ollama by name at `http://ollama:11434`. That works because `container_name: ollama` is fixed in the stack file. Everything outside Docker uses the published ports instead.

## Access

- From the tailnet: [http://100.96.62.97:11434](http://100.96.62.97:11434)
- On nedpi itself: [http://127.0.0.1:11434](http://127.0.0.1:11434)
- From containers on `ai-net`: `http://ollama:11434`

Check the current IP with `tailscale ip -4`. A quick health check on nedpi: `curl http://127.0.0.1:11434` prints `Ollama is running`.

## Storage

Everything lives on the system disk in `/home/norod/docker/ai/ollama`, mounted at `/root/.ollama` in the container. It holds the downloaded models and is the only data in this stack. It sits next to the `webui` stack's folders (`openwebui` and `searxng`) under `/home/norod/docker/ai`, but each stack only touches its own.

Let Docker create the folder on first start. Don't create it by hand as `norod`.

## Settings that matter

- `OLLAMA_HOST=0.0.0.0:11434` makes Ollama listen on all interfaces inside the container. Who can actually connect is decided by the `ports:` lines, not by this setting.
- `OLLAMA_KEEP_ALIVE=10m` keeps a model in RAM for 10 minutes after its last request, then unloads it. The first request after that is slow while the model reloads.
- `OLLAMA_MAX_LOADED_MODELS=1` and `OLLAMA_NUM_PARALLEL=1` mean one model loaded and one request at a time. This keeps RAM use predictable on the Pi.
- `OLLAMA_CONTEXT_LENGTH=8192` is the default context window. Larger values use more RAM and slow responses down.
- The external network `ai-net` must exist before the stack is deployed. Portainer does not create it.

## Setting it up

Create the shared network once. Do this before deploying either stack, because both fail to deploy without it. In Portainer: Networks, Add network, name `ai-net`, driver `bridge`. Or on nedpi:

```bash
sudo docker network create ai-net
```

Then in Portainer: Stacks, Add stack, choose **Repository**, and name it `ollama`. Set **Repository URL** to `https://github.com/norodd93/PersonalContainerStackRepo.git`, **Repository reference** to `refs/heads/main`, and **Compose path** to `PortainerStacks/Ollama/compose.yml`. No variables are needed. Click **Deploy the stack**.

If the old `llm` stack is still running, delete it first. The container name and port 11434 are already taken by it.

## Managing models

`ollama rm` deletes the model files immediately, so check the name with `list` first.

```bash
sudo docker exec -it ollama ollama pull llama3.2:3b
sudo docker exec ollama ollama list
sudo docker exec ollama ollama rm llama3.2:3b
```

## Updating the stack

1. Edit `PortainerStacks/Ollama/compose.yml` (and this README, if needed) in the repo, then commit and push.
2. In Portainer, open Stacks, then `ollama`, and click **Pull and redeploy**.
3. Turn **Re-pull image and redeploy** on to get a newer Ollama, because the tag is `latest`.

The models in `/home/norod/docker/ai/ollama` are kept. The container restarts, so any loaded model is unloaded and running requests fail.

## Troubleshooting

| Error on deploy | Meaning | Fix |
|-----------------|---------|-----|
| `network ai-net declared as external, but could not be found` | The shared network does not exist | Create it (see Setting it up), then redeploy |
| `cannot assign requested address` on port 11434 | The Tailscale IP in the stack file is not on nedpi: the IP changed, or `tailscaled` is down | Run `tailscale ip -4`. If the IP differs, update the first `ports:` line. If nothing prints, start Tailscale first |
| `port is already allocated` or `container name "/ollama" is already in use` | The old `llm` stack, or another Ollama, is still running | Delete the old stack, then redeploy |
| Open WebUI shows no models | The `ollama` stack is down, or the containers are not on the same network | Check that the stack is running, then run `sudo docker network inspect ai-net` and look for both `ollama` and `open-web-ui` |

If the Tailscale IP changes again, update it in the first `ports:` line below. The `webui` stack has the same IP in its own file.

## Stack file (copy)

Portainer deploys this file from the repo. The copy below is for reference, so keep it in sync when you edit the stack.

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    restart: unless-stopped
    environment:
      - OLLAMA_HOST=0.0.0.0:11434
      - OLLAMA_KEEP_ALIVE=10m
      - OLLAMA_MAX_LOADED_MODELS=1
      - OLLAMA_NUM_PARALLEL=1
      - OLLAMA_CONTEXT_LENGTH=8192
    volumes:
      - /home/norod/docker/ai/ollama:/root/.ollama:rw
    ports:
      - "100.96.62.97:11434:11434"
      - "127.0.0.1:11434:11434"
    command: serve
    networks:
      - ai-net

networks:
  ai-net:
    external: true
```

---
Last updated: 2026-11-11
