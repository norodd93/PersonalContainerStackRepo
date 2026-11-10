#!/usr/bin/env python3
"""OpenAI-compatible passthrough for OpenCode Go.

OpenCode Go refuses requests without an ``x-opencode-session`` header and
answers ``400 missing_session_id``. Open WebUI has no field for custom
provider headers, so this proxy sits in front of OpenCode Go and adds one.

The session id is derived from the model plus the first user message. That
value stays the same for every turn of one conversation and differs between
conversations, which is what OpenCode Go needs to keep the prompt cache for
that conversation warm. It is a hash, so nothing readable leaves the box.

Only /v1/models and /v1/chat/completions are proxied. Standard library only,
so the container needs no build step and no pip install at startup.
"""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM_HOST = os.environ.get("UPSTREAM_HOST", "opencode.ai")
UPSTREAM_PREFIX = os.environ.get("UPSTREAM_PREFIX", "/inference/go/openai/v1")
API_KEY = os.environ.get("OPENCODE_GO_KEY", "")
USER_AGENT = os.environ.get("PROXY_USER_AGENT", "openwebui-opencode-proxy/1.0")
PORT = int(os.environ.get("PORT", "9000"))
UPSTREAM_TIMEOUT = 900.0

# Connection-level headers that must not be copied to the client response.
HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "transfer-encoding",
    "content-length",
    "proxy-authenticate",
    "te",
    "trailer",
    "upgrade",
}


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def session_id(payload: dict) -> str:
    """Stable per-conversation id: same first user turn, same id."""
    first_user = ""
    for message in payload.get("messages") or []:
        if message.get("role") == "user":
            content = message.get("content")
            if isinstance(content, str):
                first_user = content
            else:
                first_user = json.dumps(content, ensure_ascii=False, sort_keys=True)
            break
    seed = f'{payload.get("model", "")}|{first_user}'
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:32]
    return "ses_" + digest


class Handler(BaseHTTPRequestHandler):
    server_version = "opencode-proxy/1.0"
    # HTTP/1.0 closes the connection after the body, which lets us stream
    # without knowing the length in advance.
    protocol_version = "HTTP/1.0"

    def do_GET(self) -> None:
        if self.path.rstrip("/") in ("/health", "/healthz"):
            self._reply(200, b"ok\n", "text/plain")
        elif self.path.split("?")[0].rstrip("/") in ("/v1/models", "/models"):
            self._relay("GET", "/models", b"", None)
        else:
            self._reply(404, b'{"error":"not found"}', "application/json")

    def do_POST(self) -> None:
        path = self.path.split("?")[0].rstrip("/")
        if path not in ("/v1/chat/completions", "/chat/completions"):
            self._reply(404, b'{"error":"not found"}', "application/json")
            return

        try:
            length = int(self.headers.get("content-length") or 0)
            body = self.rfile.read(length) if length else b""
            payload = json.loads(body or b"{}")
        except (ValueError, json.JSONDecodeError) as exc:
            self._reply(400, json.dumps({"error": f"invalid request: {exc}"}).encode(), "application/json")
            return

        session = session_id(payload)
        log(f"{payload.get('model', '?')} {session}")
        self._relay("POST", "/chat/completions", body, session)

    def _relay(self, method: str, path: str, body: bytes, session: str | None) -> None:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        }
        if self.headers.get("accept"):
            headers["Accept"] = self.headers["accept"]
        if session:
            headers["x-opencode-session"] = session

        conn = http.client.HTTPSConnection(UPSTREAM_HOST, timeout=UPSTREAM_TIMEOUT)
        try:
            conn.request(method, UPSTREAM_PREFIX + path, body=body or None, headers=headers)
            upstream = conn.getresponse()
        except Exception as exc:  # noqa: BLE001 - surface any transport error as 502
            log(f"upstream error: {exc!r}")
            conn.close()
            self._reply(502, json.dumps({"error": f"upstream unavailable: {exc}"}).encode(), "application/json")
            return

        try:
            self.send_response(upstream.status)
            for name, value in upstream.getheaders():
                if name.lower() not in HOP_BY_HOP:
                    self.send_header(name, value)
            self.end_headers()
            while True:
                chunk = upstream.read(8192)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass  # client went away (stop button); the upstream close is enough
        finally:
            upstream.close()
            conn.close()

    def _reply(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)


def main() -> None:
    if not API_KEY:
        log("OPENCODE_GO_KEY is not set - every request will fail upstream")
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    server.daemon_threads = True
    log(f"listening on :{PORT}, forwarding to https://{UPSTREAM_HOST}{UPSTREAM_PREFIX}")
    server.serve_forever()


if __name__ == "__main__":
    main()
