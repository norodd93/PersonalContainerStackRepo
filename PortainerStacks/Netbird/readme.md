# Netbird stack (brick)

Not currently deployed: no `netbird-client` container runs on nedpi or brick.

`compose.yml` runs the Netbird client with `network_mode: host`, `/dev/net/tun`, and the `netbird-client` named volume for state. Unlike the other stacks it publishes no ports and is not bound to the tailnet through Docker.

## Before deploying

The setup key line is malformed:

```yaml
environment:
  - NB_SETUP_${NB_SETUP_KEY}
```

This interpolates the key into the variable *name* (for example `NB_SETUP_abc123`), so the container never receives a value. It should be:

```yaml
environment:
  - NB_SETUP_KEY=${NB_SETUP_KEY}
```

Set `NB_SETUP_KEY` as a Portainer stack environment variable.

## Access

No published ports. Check the Netbird IP from inside the container or in the Netbird admin console.

---
Last updated: 2026-11-11
