import json
import os
import queue
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

PORT = 5050


def get_local_ip():
    """Detects the computer's local Wi-Fi / LAN IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


class StateStore:
    def __init__(self):
        self.lock = threading.Lock()
        self.current_text = "45, a, b, c"
        self.current_color = "#10b981"
        self.font_size = 48
        self.is_hidden = False
        self.subscribers = set()

    def get_dict(self):
        with self.lock:
            return {
                "text": self.current_text,
                "color": self.current_color,
                "font_size": self.font_size,
                "is_hidden": self.is_hidden
            }

    def get_json(self):
        return json.dumps(self.get_dict())

    def update_text(self, text):
        with self.lock:
            self.current_text = text
        self.broadcast()

    def update_color(self, color):
        with self.lock:
            self.current_color = color
        self.broadcast()

    def update_size(self, delta):
        with self.lock:
            self.font_size = max(16, min(140, self.font_size + delta))
        self.broadcast()

    def toggle_hidden(self):
        with self.lock:
            self.is_hidden = not self.is_hidden
        self.broadcast()

    def add_subscriber(self, q):
        with self.lock:
            self.subscribers.add(q)

    def remove_subscriber(self, q):
        with self.lock:
            self.subscribers.discard(q)

    def broadcast(self):
        msg = self.get_json()
        with self.lock:
            subs = list(self.subscribers)
        for q in subs:
            try:
                q.put_nowait(msg)
            except Exception:
                pass


store = StateStore()


# =========================================================================
# CONTROLLER PAGE (UI for typing text, presets, colors)
# =========================================================================
CONTROLLER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Screen Overlay Controller</title>
  <style>
    :root {
      --bg: #090d16;
      --card-bg: #131b2e;
      --card-border: #1e293b;
      --accent: #10b981;
      --accent-glow: rgba(16, 185, 129, 0.2);
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text-main);
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 16px;
      min-height: 100vh;
    }
    .container {
      width: 100%;
      max-width: 460px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 4px;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .brand-icon {
      width: 36px;
      height: 36px;
      background: linear-gradient(135deg, #10b981, #06b6d4);
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 18px;
    }
    .brand-text h1 { font-size: 17px; font-weight: 700; color: #fff; }
    .brand-text p { font-size: 11px; color: var(--text-muted); }
    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 12px;
      background: rgba(16, 185, 129, 0.1);
      border: 1px solid rgba(16, 185, 129, 0.3);
      border-radius: 20px;
      font-size: 12px;
      font-weight: 600;
      color: #34d399;
    }
    .pulse-dot {
      width: 8px;
      height: 8px;
      background: #10b981;
      border-radius: 50%;
      animation: pulse 2s infinite;
    }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 16px;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
    }
    .projector-banner {
      background: linear-gradient(135deg, #0284c7, #0f172a);
      border: 1px solid #38bdf8;
      border-radius: 12px;
      padding: 14px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      text-decoration: none;
      color: #fff;
      font-weight: 600;
      transition: transform 0.15s;
    }
    .projector-banner:active { transform: scale(0.98); }
    .screen-monitor {
      background: #020617;
      border: 1px solid #334155;
      border-radius: 12px;
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .preview-canvas {
      min-height: 60px;
      background: #f8fafc;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 10px;
      font-family: Consolas, monospace;
      font-size: 18px;
      font-weight: bold;
      color: #000;
      word-break: break-all;
    }
    .input-group {
      display: flex;
      gap: 8px;
      margin-top: 10px;
    }
    .text-input {
      flex: 1;
      padding: 13px 14px;
      background: #0b0f19;
      border: 1px solid #334155;
      border-radius: 10px;
      color: #fff;
      font-size: 16px;
      outline: none;
    }
    .text-input:focus { border-color: #38bdf8; }
    .btn-send {
      padding: 0 18px;
      background: #10b981;
      color: #020617;
      font-weight: 700;
      font-size: 15px;
      border: none;
      border-radius: 10px;
      cursor: pointer;
    }
    .section-title {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--text-muted);
      margin: 14px 0 8px;
    }
    .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; }
    .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }
    .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
    .btn-chip {
      padding: 11px 4px;
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 8px;
      color: #f1f5f9;
      font-size: 15px;
      font-weight: 600;
      cursor: pointer;
      text-align: center;
    }
    .btn-chip:active { background: #334155; transform: scale(0.95); }
    .color-palette { display: flex; gap: 8px; justify-content: space-between; }
    .color-swatch {
      flex: 1;
      height: 38px;
      border-radius: 10px;
      cursor: pointer;
      border: 2px solid transparent;
    }
    .color-swatch.active { border-color: #ffffff; }
    .btn-action {
      width: 100%;
      padding: 13px;
      border-radius: 10px;
      font-size: 14px;
      font-weight: 700;
      border: 1px solid transparent;
      cursor: pointer;
      margin-top: 8px;
    }
    .btn-secondary { background: #1e293b; border-color: #334155; color: #f8fafc; }
    .btn-danger { background: rgba(239, 68, 68, 0.15); border-color: rgba(239, 68, 68, 0.3); color: #f87171; margin-top: 12px; }
    #toast {
      position: fixed;
      bottom: 24px;
      left: 50%;
      transform: translateX(-50%) translateY(100px);
      background: #0f172a;
      border: 1px solid #38bdf8;
      color: #f8fafc;
      padding: 10px 18px;
      border-radius: 24px;
      font-size: 13px;
      font-weight: 600;
      transition: transform 0.3s;
      z-index: 1000;
    }
    #toast.show { transform: translateX(-50%) translateY(0); }
  </style>
</head>
<body>
  <div class="container">
    <header class="header">
      <div class="brand">
        <div class="brand-icon">⚡</div>
        <div class="brand-text">
          <h1>Daemon Controller</h1>
          <p>Project to Mobile</p>
        </div>
      </div>
      <div class="status-badge">
        <div class="pulse-dot"></div>
        <span>Ready</span>
      </div>
    </header>

    <!-- Link to Open Projector Display -->
    <a href="/display" target="_blank" class="projector-banner">
      <div>
        <div style="font-size:15px;">📽️ Open Mobile Display Screen</div>
        <div style="font-size:11px;color:#93c5fd;font-weight:normal;">Open this on the phone you want to project to</div>
      </div>
      <div style="font-size:20px;">↗</div>
    </a>

    <!-- Preview -->
    <div class="card">
      <div class="screen-monitor">
        <div style="display:flex;justify-content:space-between;font-size:11px;color:#64748b;font-weight:bold;">
          <span>PROJECTED OUTPUT</span>
          <span id="visBadge" style="color:#10b981;">● Active</span>
        </div>
        <div class="preview-canvas" id="preview">45, a, b, c</div>
      </div>

      <form class="input-group" onsubmit="sendText(event)">
        <input type="text" id="customText" class="text-input" placeholder="Type text to project..." autofocus autocomplete="off" />
        <button type="submit" class="btn-send">Send</button>
      </form>
    </div>

    <!-- Quick Buttons -->
    <div class="card">
      <div class="section-title">Quick Numbers & Letters</div>
      <div class="grid-4" style="margin-bottom:6px;">
        <button class="btn-chip" onclick="sendQuick('1')">1</button>
        <button class="btn-chip" onclick="sendQuick('2')">2</button>
        <button class="btn-chip" onclick="sendQuick('3')">3</button>
        <button class="btn-chip" onclick="sendQuick('4')">4</button>
      </div>
      <div class="grid-4" style="margin-bottom:6px;">
        <button class="btn-chip" onclick="sendQuick('A')">A</button>
        <button class="btn-chip" onclick="sendQuick('B')">B</button>
        <button class="btn-chip" onclick="sendQuick('C')">C</button>
        <button class="btn-chip" onclick="sendQuick('D')">D</button>
      </div>
      <div class="grid-3">
        <button class="btn-chip" onclick="sendQuick('45, a, b, c')">45, a, b, c</button>
        <button class="btn-chip" onclick="sendQuick('Ready')">Ready</button>
        <button class="btn-chip" onclick="sendQuick(' ')">🧹 Clear</button>
      </div>

      <!-- Colors & Size -->
      <div class="section-title">Display Style</div>
      <div class="color-palette">
        <div class="color-swatch active" style="background:#10b981;" onclick="sendColor('#10b981')"></div>
        <div class="color-swatch" style="background:#ffffff;" onclick="sendColor('#ffffff')"></div>
        <div class="color-swatch" style="background:#00e5ff;" onclick="sendColor('#00e5ff')"></div>
        <div class="color-swatch" style="background:#f59e0b;" onclick="sendColor('#f59e0b')"></div>
        <div class="color-swatch" style="background:#ef4444;" onclick="sendColor('#ef4444')"></div>
        <div class="color-swatch" style="background:#8b5cf6;" onclick="sendColor('#8b5cf6')"></div>
      </div>
      <div class="grid-2" style="margin-top:8px;">
        <button class="btn-chip" onclick="changeSize(4)">A+ Bigger Font</button>
        <button class="btn-chip" onclick="changeSize(-4)">A- Smaller Font</button>
      </div>
    </div>

    <div class="card">
      <button class="btn-action btn-secondary" onclick="toggleVisibility()">
        <span id="visText">👁️ Toggle Hide / Show on Mobile</span>
      </button>
      <button class="btn-action btn-danger" onclick="closeDaemon()">
        ❌ Shutdown Host Daemon
      </button>
    </div>
  </div>

  <div id="toast">Sent</div>

  <script>
    let state = { text: '45, a, b, c', color: '#10b981', size: 48, hidden: false };

    function showToast(msg) {
      const t = document.getElementById('toast');
      t.innerText = msg;
      t.classList.add('show');
      setTimeout(() => t.classList.remove('show'), 1500);
    }

    async function api(endpoint, data = {}) {
      try {
        const res = await fetch(endpoint, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(data)
        });
        return await res.json();
      } catch (e) {}
    }

    function render() {
      const p = document.getElementById('preview');
      p.innerText = state.hidden ? '(Hidden on Phone)' : (state.text === ' ' ? '(Blank)' : state.text);
      p.style.color = state.hidden ? '#64748b' : state.color;
      document.getElementById('visBadge').innerText = state.hidden ? '● Hidden' : '● Projecting';
      document.getElementById('visBadge').style.color = state.hidden ? '#ef4444' : '#10b981';
      document.getElementById('visText').innerText = state.hidden ? 'Show Text on Mobile' : 'Hide Text on Mobile';
    }

    window.addEventListener('DOMContentLoaded', async () => {
      try {
        const res = await fetch('/api/status');
        const d = await res.json();
        if (d.text !== undefined) state.text = d.text;
        if (d.color) state.color = d.color;
        if (d.is_hidden !== undefined) state.hidden = d.is_hidden;
        render();
      } catch (e) {}
    });

    function sendText(e) {
      if (e) e.preventDefault();
      const input = document.getElementById('customText');
      const val = input.value;
      if (val !== undefined && val !== '') {
        state.text = val;
        render();
        api('/api/text', { text: val });
        showToast('Projected to mobile');
        input.value = '';
      }
    }

    function sendQuick(txt) {
      state.text = txt;
      render();
      api('/api/text', { text: txt });
      showToast(txt === ' ' ? 'Cleared screen' : `Sent: "${txt}"`);
    }

    function sendColor(hex) {
      state.color = hex;
      render();
      document.querySelectorAll('.color-swatch').forEach(el => {
        el.classList.toggle('active', el.style.backgroundColor.includes(hex.toLowerCase()) || el.style.background.includes(hex));
      });
      api('/api/color', { color: hex });
      showToast('Color updated');
    }

    function changeSize(delta) {
      state.size = Math.max(16, Math.min(140, state.size + delta));
      api('/api/size', { delta: delta });
      showToast(`Size adjusted`);
    }

    function toggleVisibility() {
      state.hidden = !state.hidden;
      render();
      api('/api/toggle', {});
      showToast(state.hidden ? 'Hidden on mobile' : 'Visible on mobile');
    }

    function closeDaemon() {
      if (confirm('Stop host daemon on PC?')) {
        api('/api/exit', {});
        document.body.innerHTML = '<div style="text-align:center;padding:60px 20px;"><div style="font-size:42px;">✅</div><h2>Daemon Stopped</h2></div>';
      }
    }
  </script>
</body>
</html>
"""


# =========================================================================
# MOBILE PROJECTOR SCREEN PAGE (The live screen opened on the phone)
# =========================================================================
PROJECTOR_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Mobile Display</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    html, body {
      width: 100%;
      height: 100%;
      background: #000000;
      color: #10b981;
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: Consolas, "Courier New", monospace, sans-serif;
      touch-action: manipulation;
      user-select: none;
    }
    #projector-text {
      text-align: center;
      padding: 24px;
      font-size: 48px;
      font-weight: 900;
      word-break: break-word;
      white-space: pre-wrap;
      line-height: 1.25;
      transition: color 0.2s, font-size 0.2s;
    }
    #status-indicator {
      position: fixed;
      top: 14px;
      right: 14px;
      font-family: -apple-system, sans-serif;
      font-size: 11px;
      padding: 4px 10px;
      border-radius: 12px;
      background: rgba(255,255,255,0.06);
      color: #64748b;
      opacity: 0.7;
      transition: opacity 0.3s;
    }
    #status-indicator.connected {
      color: #10b981;
      opacity: 0.4;
    }
    #fullscreen-hint {
      position: fixed;
      bottom: 14px;
      font-family: -apple-system, sans-serif;
      font-size: 11px;
      color: #334155;
      pointer-events: none;
    }
  </style>
</head>
<body onclick="requestFullscreenAndWakeLock()">
  <div id="status-indicator">● Connecting...</div>
  <div id="projector-text">45, a, b, c</div>
  <div id="fullscreen-hint">Tap anywhere for fullscreen</div>

  <script>
    let wakeLock = null;

    async function requestFullscreenAndWakeLock() {
      // 1. Request Browser Fullscreen
      try {
        if (!document.fullscreenElement) {
          await document.documentElement.requestFullscreen();
          document.getElementById('fullscreen-hint').style.display = 'none';
        }
      } catch (e) {}

      // 2. Request Screen WakeLock (prevents screen from sleeping)
      try {
        if ('wakeLock' in navigator && !wakeLock) {
          wakeLock = await navigator.wakeLock.request('screen');
        }
      } catch (e) {}
    }

    // Auto-acquire WakeLock on load if allowed
    document.addEventListener('visibilitychange', async () => {
      if (document.visibilityState === 'visible') {
        try {
          if ('wakeLock' in navigator) wakeLock = await navigator.wakeLock.request('screen');
        } catch (e) {}
      }
    });

    // Server-Sent Events (SSE) Live Stream
    function connectStream() {
      const statusEl = document.getElementById('status-indicator');
      const textEl = document.getElementById('projector-text');

      const evtSource = new EventSource('/api/stream');

      evtSource.onopen = () => {
        statusEl.innerText = '● Live';
        statusEl.className = 'connected';
      };

      evtSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.is_hidden) {
            textEl.innerText = '';
          } else {
            textEl.innerText = data.text === ' ' ? '' : data.text;
          }
          if (data.color) textEl.style.color = data.color;
          if (data.font_size) textEl.style.fontSize = data.font_size + 'px';
        } catch (e) {}
      };

      evtSource.onerror = () => {
        statusEl.innerText = '● Reconnecting...';
        statusEl.className = '';
        evtSource.close();
        setTimeout(connectStream, 2000);
      };
    }

    window.addEventListener('DOMContentLoaded', connectStream);
  </script>
</body>
</html>
"""


class WebRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silent HTTP logging
        return

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(CONTROLLER_HTML.encode("utf-8"))

        elif parsed.path in ("/display", "/project", "/screen"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(PROJECTOR_HTML.encode("utf-8"))

        elif parsed.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(store.get_json().encode("utf-8"))

        elif parsed.path == "/api/stream":
            # Server-Sent Events (SSE) Live Push Stream
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            q = queue.Queue()
            store.add_subscriber(q)
            q.put(store.get_json())  # send initial state immediately

            try:
                while True:
                    try:
                        msg = q.get(timeout=15)
                        self.wfile.write(f"data: {msg}\n\n".encode("utf-8"))
                        self.wfile.flush()
                    except queue.Empty:
                        self.wfile.write(b": ping\n\n")
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, Exception):
                pass
            finally:
                store.remove_subscriber(q)

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            payload = {}

        parsed = urlparse(self.path)

        if parsed.path == "/api/text":
            store.update_text(payload.get("text", ""))
        elif parsed.path == "/api/color":
            store.update_color(payload.get("color", "#10b981"))
        elif parsed.path == "/api/size":
            store.update_size(int(payload.get("delta", 0)))
        elif parsed.path == "/api/toggle":
            store.toggle_hidden()
        elif parsed.path == "/api/exit":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b'{"status": "shutting_down"}')
            threading.Thread(target=lambda: (time.sleep(0.5), os._exit(0)), daemon=True).start()
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b'{"status": "ok"}')


class ReusableThreadingServer(ThreadingHTTPServer):
    allow_reuse_address = True


def main():
    local_ip = get_local_ip()
    ctrl_url = f"http://{local_ip}:{PORT}"
    proj_url = f"http://{local_ip}:{PORT}/display"

    print("=" * 65)
    print("        SCREEN OVERLAY REMOTE - HEADLESS NETWORK DAEMON")
    print("=" * 65)
    print(" [!] ZERO GUI / ZERO pixels on PC (100% Headless).")
    print(" [!] Immune to Windows Desktop switches & EnumWindows.")
    print("=" * 65)
    print(f" 📱 Mobile Projector Screen: 👉  {proj_url}")
    print(f" 🎛️  Controller Interface:    👉  {ctrl_url}")
    print("=" * 65)
    print(" - Open the Projector Screen on your phone (it will stay awake).")
    print(" - Send 1, 2, 3, A, B, or text from the Controller.")
    print(" - Press Ctrl+C in this console or tap Shutdown to exit.")
    print("=" * 65)

    server = ReusableThreadingServer(("0.0.0.0", PORT), WebRequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
        os._exit(0)


if __name__ == "__main__":
    main()
