#!/usr/bin/env python3
"""
Reverse proxy that runs `git pull` on every request before forwarding to hashcards.
Pulls are debounced so rapid reloads don't hammer git.
"""
import http.server
import urllib.request
import urllib.error
import os
import subprocess
import threading
import time

HASHCARDS_PORT = 8001
PROXY_PORT = 8000
DECKS_PATH = "/data/decks"
PULL_MIN_INTERVAL = 30  # seconds
IGNORED_FILES = ["CLAUDE.md"]  # files pulled from git but excluded from the decks dir

_last_pull = 0.0
_pull_lock = threading.Lock()


def pull_decks():
    global _last_pull
    now = time.time()
    if now - _last_pull < PULL_MIN_INTERVAL:
        return
    with _pull_lock:
        if time.time() - _last_pull < PULL_MIN_INTERVAL:
            return
        try:
            result = subprocess.run(
                ["git", "-C", DECKS_PATH, "pull"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.stdout.strip() and result.stdout.strip() != "Already up to date.":
                print(result.stdout.strip(), flush=True)
        except Exception as e:
            print(f"git pull failed: {e}", flush=True)
        _last_pull = time.time()


HOP_BY_HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
               "te", "trailers", "transfer-encoding", "upgrade"}


class PullProxyHandler(http.server.BaseHTTPRequestHandler):
    def proxy(self):
        pull_decks()

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length else None

        url = f"http://localhost:{HASHCARDS_PORT}{self.path}"
        req = urllib.request.Request(url, data=body, method=self.command)

        for key, val in self.headers.items():
            if key.lower() not in HOP_BY_HOP | {"host", "content-length"}:
                req.add_header(key, val)
        if body:
            req.add_header("Content-Length", str(len(body)))

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                self.send_response(resp.status)
                for key, val in resp.headers.items():
                    if key.lower() not in HOP_BY_HOP:
                        self.send_header(key, val)
                self.end_headers()
                self.wfile.write(resp.read())
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            for key, val in e.headers.items():
                if key.lower() not in HOP_BY_HOP:
                    self.send_header(key, val)
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            self.send_error(502, f"Bad Gateway: {e}")

    do_GET = proxy
    do_POST = proxy
    do_PUT = proxy
    do_DELETE = proxy
    do_PATCH = proxy
    do_HEAD = proxy

    def log_message(self, fmt, *args):
        pass  # suppress per-request noise


if __name__ == "__main__":
    server = http.server.ThreadingHTTPServer(("0.0.0.0", PROXY_PORT), PullProxyHandler)
    print(f"Proxy listening on :{PROXY_PORT} -> hashcards :{HASHCARDS_PORT}", flush=True)
    server.serve_forever()
