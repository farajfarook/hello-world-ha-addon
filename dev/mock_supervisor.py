"""Minimal mock of the Home Assistant Supervisor API for local add-on development.

Implements just the endpoints the hello_world add-on (and bashio) use:
  GET  /addons/self/info            -> add-on info incl. options
  GET  /addons/self/options/config  -> options (used by bashio::config)
  POST /addons/self/options         -> save options (validated like the schema)
  POST /addons/self/restart         -> restarts the add-on container via Docker
Options are persisted to /data/options.json (bind-mounted to dev/data/).
"""
import http.client
import json
import os
import re
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKEN = os.environ.get("SUPERVISOR_TOKEN", "dev-token")
ADDON_CONTAINER = os.environ.get("ADDON_CONTAINER", "hello_world_dev")
OPTIONS_FILE = "/data/options.json"
DEFAULTS = {"message": "Hello world!", "name": "Home Assistant", "color": "#03a9f4", "log_interval": 60}


def load():
    try:
        with open(OPTIONS_FILE) as f:
            return {**DEFAULTS, **json.load(f)}
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(DEFAULTS)


def save(options):
    os.makedirs(os.path.dirname(OPTIONS_FILE), exist_ok=True)
    with open(OPTIONS_FILE, "w") as f:
        json.dump(options, f, indent=2)


def validate(o):
    """Mirror the schema in hello_world/config.yaml."""
    errors = []
    for key in ("message", "name"):
        if not isinstance(o.get(key), str):
            errors.append(f"{key} must be a string")
    if not isinstance(o.get("color"), str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", o["color"]):
        errors.append("color must match ^#[0-9a-fA-F]{6}$")
    li = o.get("log_interval")
    if not isinstance(li, int) or isinstance(li, bool) or not 5 <= li <= 3600:
        errors.append("log_interval must be an int between 5 and 3600")
    return errors


class DockerConn(http.client.HTTPConnection):
    def __init__(self):
        super().__init__("localhost", timeout=30)

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect("/var/run/docker.sock")


def restart_addon():
    conn = DockerConn()
    conn.request("POST", f"/containers/{ADDON_CONTAINER}/restart?t=2")
    status = conn.getresponse().status
    conn.close()
    return status


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        data = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _ok(self, data=None):
        self._send(200, {"result": "ok", "data": data if data is not None else {}})

    def _err(self, code, msg):
        self._send(code, {"result": "error", "message": msg})

    def _authed(self):
        if self.headers.get("Authorization") != f"Bearer {TOKEN}":
            self._err(401, "Unauthorized")
            return False
        return True

    def do_GET(self):
        if not self._authed():
            return
        path = self.path.split("?")[0]
        if path == "/addons/self/info":
            self._ok({"name": "Hello World", "slug": "local_hello_world", "state": "started", "options": load()})
        elif path == "/addons/self/options/config":
            self._ok(load())
        else:
            self._err(404, f"mock supervisor: {path} not implemented")

    def do_POST(self):
        if not self._authed():
            return
        path = self.path.split("?")[0]
        if path == "/addons/self/options":
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            options = body.get("options", {})
            errors = validate(options)
            if errors:
                return self._err(400, "; ".join(errors))
            save(options)
            print(f"[supervisor] options saved: {options}", flush=True)
            self._ok()
        elif path == "/addons/self/restart":
            self._ok()
            try:
                print(f"[supervisor] restarting {ADDON_CONTAINER}: HTTP {restart_addon()}", flush=True)
            except Exception as e:  # noqa: BLE001
                print(f"[supervisor] restart failed: {e}", flush=True)
        else:
            self._err(404, f"mock supervisor: {path} not implemented")

    def log_message(self, fmt, *args):
        print("[supervisor] " + fmt % args, flush=True)


if __name__ == "__main__":
    print("[supervisor] mock listening on :80", flush=True)
    ThreadingHTTPServer(("0.0.0.0", 80), Handler).serve_forever()
