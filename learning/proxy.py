#!/usr/bin/env python3
"""
Reverse proxy that manages the hashcards lifecycle:
- Starts hashcards on boot.
- Runs `git pull` on every request (debounced).
- Restarts hashcards after a pull that brings in changes.
- Watchdog thread restarts hashcards if it exits unexpectedly.
"""
import http.server
import urllib.request
import urllib.error
import subprocess
import threading
import time

HASHCARDS_PORT = 8001
PROXY_PORT = 8000
DECKS_PATH = "/data/decks"
CARDS_PATH = "/data/decks/cards"
PULL_MIN_INTERVAL = 30  # seconds

_last_pull = 0.0
_pull_lock = threading.Lock()

_hashcards_proc = None
_hashcards_lock = threading.Lock()


def start_hashcards():
    global _hashcards_proc
    proc = subprocess.Popen([
        "hashcards", "drill",
        "--host", "0.0.0.0",
        "--port", str(HASHCARDS_PORT),
        "--open-browser", "false",
        CARDS_PATH,
    ])
    _hashcards_proc = proc
    print(f"hashcards started (pid {proc.pid})", flush=True)


def restart_hashcards():
    global _hashcards_proc
    with _hashcards_lock:
        if _hashcards_proc is not None and _hashcards_proc.poll() is None:
            print("stopping hashcards...", flush=True)
            _hashcards_proc.terminate()
            try:
                _hashcards_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                _hashcards_proc.kill()
                _hashcards_proc.wait()
        start_hashcards()


def watchdog():
    """Restart hashcards if it exits unexpectedly."""
    while True:
        time.sleep(5)
        with _hashcards_lock:
            if _hashcards_proc is not None and _hashcards_proc.poll() is not None:
                print("hashcards exited unexpectedly, restarting...", flush=True)
                start_hashcards()


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
            output = result.stdout.strip()
            if output and output != "Already up to date.":
                print(output, flush=True)
                restart_hashcards()
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

        # Retry briefly to allow hashcards time to start after a restart.
        last_err = None
        for _ in range(10):
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    self.send_response(resp.status)
                    for key, val in resp.headers.items():
                        if key.lower() not in HOP_BY_HOP:
                            self.send_header(key, val)
                    self.end_headers()
                    self.wfile.write(resp.read())
                    return
            except urllib.error.HTTPError as e:
                self.send_response(e.code)
                for key, val in e.headers.items():
                    if key.lower() not in HOP_BY_HOP:
                        self.send_header(key, val)
                self.end_headers()
                self.wfile.write(e.read())
                return
            except Exception as e:
                last_err = e
                time.sleep(0.5)

        self.send_error(502, f"Bad Gateway: {last_err}")

    do_GET = proxy
    do_POST = proxy
    do_PUT = proxy
    do_DELETE = proxy
    do_PATCH = proxy
    do_HEAD = proxy

    def log_message(self, fmt, *args):
        pass  # suppress per-request noise


if __name__ == "__main__":
    start_hashcards()
    threading.Thread(target=watchdog, daemon=True).start()

    server = http.server.ThreadingHTTPServer(("0.0.0.0", PROXY_PORT), PullProxyHandler)
    print(f"Proxy listening on :{PROXY_PORT} -> hashcards :{HASHCARDS_PORT}", flush=True)
    server.serve_forever()
