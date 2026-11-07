#!/usr/bin/env python3
"""FT-T1 logging proxy: sit between a Tier-1 CLI and the local oMLX endpoint.

The Tier-1 harnesses (Claude Code & friends) are separate processes — an
in-process httpx hook cannot see their LLM traffic. So the harness points the
CLI at this proxy (ANTHROPIC_BASE_URL=http://127.0.0.1:<port>), which forwards
every request to the upstream oMLX and **logs each request/response pair** to
the case's ``artifacts/llm/call-NNNN-{request,response}.json`` — sanitized —
so `ft_assert_llm_capture` and the deep-verification LLM gate have the same
evidence the in-process frameworks produce.

Stdlib only (no new deps). Usage::

    t1_proxy.py UPSTREAM_URL LOG_DIR [PORT]   # PORT default 0 = ephemeral
    # prints "T1_PROXY_READY <url>" then serves until killed.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

_SECRET = re.compile(r"sk-[A-Za-z0-9]{16,}|Bearer\s+[A-Za-z0-9._-]{20,}", re.IGNORECASE)


def _san(obj: object) -> object:
    if isinstance(obj, str):
        return _SECRET.sub("[REDACTED]", obj)
    if isinstance(obj, dict):
        return {k: ("[REDACTED]" if k.lower() in ("authorization", "api_key", "x-api-key")
                    else _san(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_san(v) for v in obj]
    return obj


def main(argv: list[str]) -> int:
    upstream = argv[1].rstrip("/")
    log_dir = Path(argv[2])
    log_dir.mkdir(parents=True, exist_ok=True)
    port = int(argv[3]) if len(argv) > 3 else 0
    counter = [0]

    class Proxy(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a: object) -> None:  # quiet
            pass

        def _forward(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b""
            req_headers = {k: v for k, v in self.headers.items()
                           if k.lower() not in ("host", "content-length")}
            req = urllib.request.Request(  # noqa: S310 - upstream is operator-pinned
                upstream + self.path, data=body or None, headers=req_headers,
                method=self.command,
            )
            try:
                with urllib.request.urlopen(req) as resp:  # noqa: S310
                    resp_body = resp.read()
                    status = resp.status
                    resp_headers = dict(resp.headers)
            except urllib.error.HTTPError as e:  # upstream said no
                resp_body = e.read()
                status = e.code
                resp_headers = dict(e.headers)
            # log the pair (LLM calls only)
            if any(p in self.path for p in
                   ("/messages", "/completions", "/embeddings", "/responses")):
                counter[0] += 1
                name = f"call-{counter[0]:04d}"
                try:
                    req_json = json.loads(body.decode() or "{}")
                except Exception:
                    req_json = {"_raw": body.decode("utf-8", "replace")[:4000]}
                (log_dir / f"{name}-request.json").write_text(
                    json.dumps(_san({"method": self.command, "url": self.path,
                                     "body": req_json}), indent=2) + "\n", encoding="utf-8")
                try:
                    resp_json = json.loads(resp_body.decode() or "{}")
                except Exception:
                    resp_json = {"_raw": resp_body.decode("utf-8", "replace")[:4000]}
                (log_dir / f"{name}-response.json").write_text(
                    json.dumps(_san({"status_code": status, "body": resp_json}),
                               indent=2) + "\n", encoding="utf-8")
            # relay
            payload = resp_body
            self.send_response(status)
            for k, v in resp_headers.items():
                if k.lower() not in ("transfer-encoding", "content-encoding",
                                     "content-length", "connection"):
                    self.send_header(k, v)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        do_GET = do_POST = do_DELETE = do_PUT = do_PATCH = _forward

    server = ThreadingHTTPServer(("127.0.0.1", port), Proxy)
    print(f"T1_PROXY_READY http://127.0.0.1:{server.server_address[1]}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

