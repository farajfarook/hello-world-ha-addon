"""Tiny web UI for the Hello World add-on, served through HA Ingress."""
import json
import os
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8099
SUPERVISOR = "http://supervisor"
TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
INGRESS_IP = "172.30.32.2"  # Only the HA ingress proxy may connect


def supervisor(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        SUPERVISOR + path,
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read() or b"{}")


def get_options():
    return supervisor("GET", "/addons/self/info")["data"]["options"]


PAGE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hello World</title>
<style>
  :root { --accent: #03a9f4; }
  body { font-family: system-ui, sans-serif; margin: 0; padding: 24px;
         background: #f5f5f5; color: #212121; }
  @media (prefers-color-scheme: dark) {
    body { background: #111; color: #e1e1e1; }
    .card { background: #1c1c1c !important; }
    input { background: #2a2a2a; color: #e1e1e1; border-color: #444 !important; }
  }
  .card { background: #fff; border-radius: 12px; padding: 24px; max-width: 520px;
          margin: 0 auto 24px; box-shadow: 0 2px 6px rgba(0,0,0,.15); }
  h1 { color: var(--accent); margin-top: 0; }
  label { display: block; margin: 14px 0 4px; font-weight: 600; font-size: .9em; }
  input { width: 100%; padding: 8px; box-sizing: border-box; border: 1px solid #ccc;
          border-radius: 6px; font-size: 1em; }
  input[type=color] { height: 40px; padding: 2px; }
  button { margin-top: 18px; margin-right: 8px; padding: 10px 18px; border: 0;
           border-radius: 6px; background: var(--accent); color: #fff;
           font-size: 1em; cursor: pointer; }
  button.secondary { background: #757575; }
  #status { margin-top: 12px; font-size: .9em; min-height: 1.2em; }
</style>
</head>
<body>
  <div class="card">
    <h1 id="greeting">Hello!</h1>
    <p id="message"></p>
  </div>

  <div class="card">
    <h2>Configuration</h2>
    <form id="form">
      <label for="f-message">Message</label>
      <input id="f-message" name="message" required>
      <label for="f-name">Name</label>
      <input id="f-name" name="name" required>
      <label for="f-color">Accent color</label>
      <input id="f-color" name="color" type="color">
      <label for="f-interval">Log interval (seconds, 5-3600)</label>
      <input id="f-interval" name="log_interval" type="number" min="5" max="3600" required>
      <button type="submit">Save</button>
      <button type="button" class="secondary" id="restart">Save &amp; restart</button>
    </form>
    <div id="status"></div>
  </div>

<script>
  // Relative URLs are required so requests go through the ingress path.
  const $ = (id) => document.getElementById(id);
  const status = (t) => $("status").textContent = t;

  function render(o) {
    $("greeting").textContent = "Hello, " + o.name + "!";
    $("message").textContent = o.message;
    document.documentElement.style.setProperty("--accent", o.color);
    $("f-message").value = o.message;
    $("f-name").value = o.name;
    $("f-color").value = o.color;
    $("f-interval").value = o.log_interval;
  }

  async function load() {
    const r = await fetch("api/options");
    if (!r.ok) return status("Failed to load options");
    render(await r.json());
  }

  async function save(restart) {
    const body = {
      message: $("f-message").value,
      name: $("f-name").value,
      color: $("f-color").value,
      log_interval: parseInt($("f-interval").value, 10),
    };
    status("Saving...");
    const r = await fetch("api/options" + (restart ? "?restart=1" : ""), {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(body),
    });
    const res = await r.json();
    if (!r.ok) return status("Error: " + (res.error || r.status));
    render(body);
    status(restart ? "Saved. Restarting add-on..." : "Saved.");
  }

  $("form").addEventListener("submit", (e) => { e.preventDefault(); save(false); });
  $("restart").addEventListener("click", () => {
    if ($("form").reportValidity()) save(true);
  });
  load();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body.encode() if isinstance(body, str) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _allowed(self):
        if self.client_address[0] != INGRESS_IP:
            self._send(403, {"error": "forbidden"})
            return False
        return True

    def do_GET(self):
        if not self._allowed():
            return
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self._send(200, PAGE, "text/html; charset=utf-8")
        elif path == "/api/options":
            try:
                self._send(200, get_options())
            except Exception as e:  # noqa: BLE001
                self._send(500, {"error": str(e)})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if not self._allowed():
            return
        path, _, query = self.path.partition("?")
        if path != "/api/options":
            return self._send(404, {"error": "not found"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            new = json.loads(self.rfile.read(length))
            options = get_options()
            options.update({k: new[k] for k in ("message", "name", "color", "log_interval") if k in new})
            supervisor("POST", "/addons/self/options", {"options": options})
            self._send(200, {"ok": True})
            if "restart=1" in query:
                supervisor("POST", "/addons/self/restart")
        except urllib.error.HTTPError as e:
            self._send(400, {"error": e.read().decode(errors="replace")})
        except Exception as e:  # noqa: BLE001
            self._send(500, {"error": str(e)})

    def log_message(self, fmt, *args):
        pass  # keep add-on log clean


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
