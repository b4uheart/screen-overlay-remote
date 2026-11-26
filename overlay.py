import ctypes
from ctypes import wintypes
import json
import os
import socket
import sys
import threading
import time
import tkinter as tk
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

# Windows API Constants
GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000

# SetWindowPos 64-bit definitions
SetWindowPos = ctypes.windll.user32.SetWindowPos
SetWindowPos.argtypes = [
    wintypes.HWND,
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT
]
SetWindowPos.restype = wintypes.BOOL

HWND_TOPMOST = wintypes.HWND(-1)
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_TOPMOST_FLAGS = SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE

# Screen Capture Protection Flag (Windows 10 2004+ and Windows 11)
# Excludes the window entirely from screenshots and screen recordings (e.g. Zoom, OBS, Discord)
WDA_EXCLUDEFROMCAPTURE = 0x00000011
WDA_MONITOR = 0x00000001

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


class OverlayApp:
    def __init__(self):
        self.root = tk.Tk()

        # 1. Frameless & Topmost
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)

        # 2. Transparent background chroma key
        self.bg_color = "#000001"
        self.root.config(bg=self.bg_color)
        self.root.wm_attributes("-transparentcolor", self.bg_color)

        # 3. Position state (auto-resizes to fit text)
        self.pos_x = 70
        self.pos_y = 70
        self.root.geometry(f"+{self.pos_x}+{self.pos_y}")

        # 4. State
        self.current_text = "R"
        self.current_color = "#000000"
        self.font_size = 10
        self.is_hidden = False

        # 5. Label (Explicit font applied on startup)
        self.label = tk.Label(
            self.root,
            text=self.current_text,
            font=("Consolas", self.font_size, "bold"),
            fg=self.current_color,
            bg=self.bg_color
        )
        self.label.pack(expand=True)

        # 6. Apply Windows Styles
        self.root.update()
        self.hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()

        # Click-through: clicks pass through to whatever window is behind it
        styles = ctypes.windll.user32.GetWindowLongW(self.hwnd, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(self.hwnd, GWL_EXSTYLE, styles | WS_EX_TRANSPARENT | WS_EX_LAYERED)

        # Anti-screen capture: invisible to Zoom screen share & recordings
        res = ctypes.windll.user32.SetWindowDisplayAffinity(self.hwnd, WDA_EXCLUDEFROMCAPTURE)
        if not res:
            ctypes.windll.user32.SetWindowDisplayAffinity(self.hwnd, WDA_MONITOR)

        # Initial topmost placement
        SetWindowPos(self.hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_TOPMOST_FLAGS)

        # 7. Keep-On-Top watchdog: asserts topmost every 250ms against competing topmost apps
        self.keep_on_top()

    def keep_on_top(self):
        try:
            SetWindowPos(self.hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_TOPMOST_FLAGS)
            self.root.after(250, self.keep_on_top)
        except Exception:
            pass

    # Thread-safe methods called by HTTP server via root.after
    def set_text(self, new_text):
        try:
            self.current_text = new_text
            if not self.is_hidden:
                self.label.config(text=new_text)
        except Exception:
            pass

    def set_color(self, hex_color):
        try:
            self.current_color = hex_color
            self.label.config(fg=hex_color)
        except Exception:
            pass

    def set_font_size(self, delta):
        try:
            self.font_size = max(8, min(72, self.font_size + delta))
            self.label.config(font=("Consolas", self.font_size, "bold"))
        except Exception:
            pass

    def move_by(self, dx, dy):
        try:
            self.pos_x = max(0, self.pos_x + dx)
            self.pos_y = max(0, self.pos_y + dy)
            self.root.geometry(f"+{self.pos_x}+{self.pos_y}")
        except Exception:
            pass

    def set_preset_pos(self, preset):
        try:
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            if preset == "top-left":
                self.pos_x, self.pos_y = 60, 60
            elif preset == "top-right":
                self.pos_x, self.pos_y = max(0, sw - 160), 60
            elif preset == "center":
                self.pos_x, self.pos_y = sw // 2 - 50, sh // 2 - 20
            elif preset == "bottom-left":
                self.pos_x, self.pos_y = 60, max(0, sh - 80)
            elif preset == "bottom-right":
                self.pos_x, self.pos_y = max(0, sw - 160), max(0, sh - 80)
            self.root.geometry(f"+{self.pos_x}+{self.pos_y}")
        except Exception:
            pass

    def toggle_visibility(self):
        try:
            self.is_hidden = not self.is_hidden
            self.label.config(text="" if self.is_hidden else self.current_text)
        except Exception:
            pass

    def exit_app(self):
        try:
            self.root.destroy()
        except Exception:
            pass
        os._exit(0)


# HTML & JavaScript for the Mobile Web Control Panel
HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Screen Overlay Remote</title>
  <style>
    :root {
      --bg: #090d16;
      --card-bg: #131b2e;
      --card-border: #1e293b;
      --accent: #10b981;
      --accent-glow: rgba(16, 185, 129, 0.2);
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --primary-btn: #10b981;
      --primary-btn-hover: #059669;
      --secondary-btn: #1e293b;
      --secondary-btn-border: #334155;
      --danger-btn: #ef4444;
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
      line-height: 1.5;
    }
    .container {
      width: 100%;
      max-width: 460px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    /* Header */
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
      box-shadow: 0 4px 12px var(--accent-glow);
    }
    .brand-text h1 {
      font-size: 17px;
      font-weight: 700;
      color: #fff;
      letter-spacing: -0.02em;
    }
    .brand-text p {
      font-size: 11px;
      color: var(--text-muted);
    }
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
      box-shadow: 0 0 8px #10b981;
      animation: pulse 2s infinite;
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.5; transform: scale(0.85); }
    }
    /* Card */
    .card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 16px;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
    }
    /* Live Preview Screen */
    .screen-monitor {
      background: #020617;
      border: 1px solid #334155;
      border-radius: 12px;
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      position: relative;
      overflow: hidden;
    }
    .screen-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 11px;
      color: #64748b;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-weight: 700;
    }
    .preview-canvas {
      min-height: 58px;
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
      box-shadow: inset 0 2px 6px rgba(0,0,0,0.06);
      transition: all 0.2s ease;
    }
    .meta-bar {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }
    .tag {
      font-size: 11px;
      padding: 3px 8px;
      background: #1e293b;
      border-radius: 6px;
      color: #cbd5e1;
      font-family: monospace;
    }
    /* Input Form */
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
      transition: border-color 0.2s;
    }
    .text-input:focus {
      border-color: #38bdf8;
      box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.15);
    }
    .btn-send {
      padding: 0 18px;
      background: #10b981;
      color: #020617;
      font-weight: 700;
      font-size: 15px;
      border: none;
      border-radius: 10px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: transform 0.1s, background-color 0.15s;
    }
    .btn-send:active { transform: scale(0.96); background: #059669; }
    /* Section Headings */
    .section-title {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--text-muted);
      margin: 14px 0 8px;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    /* Grids & Buttons */
    .grid-4 {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 6px;
    }
    .grid-2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 6px;
    }
    .grid-3 {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 6px;
    }
    .btn-chip {
      padding: 10px 4px;
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 8px;
      color: #f1f5f9;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      text-align: center;
      transition: background 0.15s, transform 0.1s, border-color 0.15s;
      touch-action: manipulation;
    }
    .btn-chip:active {
      transform: scale(0.95);
      background: #334155;
      border-color: #64748b;
    }
    /* Colors */
    .color-palette {
      display: flex;
      justify-content: space-between;
      gap: 8px;
      padding: 4px 0;
    }
    .color-swatch {
      flex: 1;
      height: 38px;
      border-radius: 10px;
      cursor: pointer;
      border: 2px solid transparent;
      transition: transform 0.15s, border-color 0.15s;
    }
    .color-swatch:active { transform: scale(0.92); }
    .color-swatch.active { border-color: #ffffff; box-shadow: 0 0 10px rgba(255,255,255,0.4); }

    /* D-Pad Positioning */
    .dpad-container {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 6px;
      max-width: 260px;
      margin: 4px auto 10px;
    }
    .dpad-btn {
      padding: 14px 0;
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 10px;
      color: #fff;
      font-size: 16px;
      font-weight: bold;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.15s, transform 0.1s;
    }
    .dpad-btn:active { transform: scale(0.93); background: #334155; }

    /* Actions */
    .btn-action {
      width: 100%;
      padding: 13px;
      border-radius: 10px;
      font-size: 14px;
      font-weight: 700;
      border: 1px solid transparent;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      margin-top: 8px;
      transition: transform 0.1s;
    }
    .btn-action:active { transform: scale(0.97); }
    .btn-secondary { background: #1e293b; border-color: #334155; color: #f8fafc; }
    .btn-danger { background: rgba(239, 68, 68, 0.12); border-color: rgba(239, 68, 68, 0.3); color: #f87171; margin-top: 12px; }

    /* Toast */
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
      box-shadow: 0 10px 25px rgba(0,0,0,0.6);
      transition: transform 0.3s cubic-bezier(0.18, 0.89, 0.32, 1.28);
      z-index: 1000;
      pointer-events: none;
    }
    #toast.show {
      transform: translateX(-50%) translateY(0);
    }
  </style>
</head>
<body>
  <div class="container">
    <!-- Header -->
    <header class="header">
      <div class="brand">
        <div class="brand-icon">⚡</div>
        <div class="brand-text">
          <h1>Screen Overlay</h1>
          <p>Presentation Controller</p>
        </div>
      </div>
      <div class="status-badge">
        <div class="pulse-dot"></div>
        <span>Live</span>
      </div>
    </header>

    <!-- Monitor Card -->
    <div class="card">
      <div class="screen-monitor">
        <div class="screen-header">
          <span>PC Screen Output</span>
          <span id="visBadge" style="color:#10b981;">● Active</span>
        </div>
        <div class="preview-canvas" id="preview">R</div>
        <div class="meta-bar">
          <span class="tag" id="tagPos">Pos: (70, 70)</span>
          <span class="tag" id="tagSize">Size: 10px</span>
          <span class="tag" id="tagColor">Color: #000000</span>
        </div>
      </div>

      <!-- Live Input -->
      <form class="input-group" onsubmit="sendText(event)">
        <input type="text" id="customText" class="text-input" placeholder="Type text to display..." autofocus autocomplete="off" />
        <button type="submit" class="btn-send">Send</button>
      </form>
    </div>

    <!-- Quick Presets Card -->
    <div class="card">
      <div class="section-title">Quick Presets</div>
      <div class="grid-4" style="margin-bottom: 6px;">
        <button class="btn-chip" onclick="sendQuick('A')">A</button>
        <button class="btn-chip" onclick="sendQuick('B')">B</button>
        <button class="btn-chip" onclick="sendQuick('C')">C</button>
        <button class="btn-chip" onclick="sendQuick('D')">D</button>
      </div>
      <div class="grid-4" style="margin-bottom: 6px;">
        <button class="btn-chip" onclick="sendQuick('1')">1</button>
        <button class="btn-chip" onclick="sendQuick('2')">2</button>
        <button class="btn-chip" onclick="sendQuick('3')">3</button>
        <button class="btn-chip" onclick="sendQuick('4')">4</button>
      </div>
      <div class="grid-3">
        <button class="btn-chip" onclick="sendQuick('45, a, b, c')">45, a, b, c</button>
        <button class="btn-chip" onclick="sendQuick('Ready')">Ready</button>
        <button class="btn-chip" onclick="sendQuick(' ')">🧹 Clear</button>
      </div>

      <!-- Color & Size -->
      <div class="section-title">Text Style</div>
      <div class="color-palette">
        <div class="color-swatch active" style="background:#000000; border:1px solid #475569;" onclick="sendColor('#000000')"></div>
        <div class="color-swatch" style="background:#10b981;" onclick="sendColor('#10b981')"></div>
        <div class="color-swatch" style="background:#ffffff;" onclick="sendColor('#ffffff')"></div>
        <div class="color-swatch" style="background:#ef4444;" onclick="sendColor('#ef4444')"></div>
        <div class="color-swatch" style="background:#00e5ff;" onclick="sendColor('#00e5ff')"></div>
        <div class="color-swatch" style="background:#f59e0b;" onclick="sendColor('#f59e0b')"></div>
      </div>
      <div class="grid-2" style="margin-top: 8px;">
        <button class="btn-chip" onclick="changeSize(2)">A+ Enlarge</button>
        <button class="btn-chip" onclick="changeSize(-2)">A- Shrink</button>
      </div>
    </div>

    <!-- Position Card -->
    <div class="card">
      <div class="section-title">Position Adjuster</div>
      <div class="dpad-container">
        <div></div>
        <button class="dpad-btn" onclick="move(0, -25)">▲</button>
        <div></div>
        <button class="dpad-btn" onclick="move(-25, 0)">◀</button>
        <button class="dpad-btn" onclick="setPos('center')">●</button>
        <button class="dpad-btn" onclick="move(25, 0)">▶</button>
        <div></div>
        <button class="dpad-btn" onclick="move(0, 25)">▼</button>
        <div></div>
      </div>
      <div class="grid-2">
        <button class="btn-chip" onclick="setPos('top-left')">↖ Top-Left</button>
        <button class="btn-chip" onclick="setPos('top-right')">↗ Top-Right</button>
        <button class="btn-chip" onclick="setPos('bottom-left')">↙ Bottom-Left</button>
        <button class="btn-chip" onclick="setPos('bottom-right')">↘ Bottom-Right</button>
      </div>
    </div>

    <!-- Actions Card -->
    <div class="card">
      <button class="btn-action btn-secondary" onclick="toggleVisibility()">
        <span id="visIcon">👁️</span> <span id="visText">Toggle Hide / Show</span>
      </button>
      <button class="btn-action btn-danger" onclick="closeOverlay()">
        ❌ Close Overlay on PC
      </button>
    </div>
  </div>

  <div id="toast">Command sent</div>

  <script>
    let state = { text: 'R', color: '#000000', size: 10, posX: 70, posY: 70, hidden: false };

    function showToast(msg) {
      const t = document.getElementById('toast');
      t.innerText = msg;
      t.classList.add('show');
      setTimeout(() => t.classList.remove('show'), 1600);
    }

    async function api(endpoint, data = {}) {
      try {
        const res = await fetch(endpoint, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(data)
        });
        return await res.json();
      } catch (err) {
        console.error(err);
      }
    }

    function renderState() {
      const p = document.getElementById('preview');
      p.innerText = state.hidden ? '(Hidden)' : (state.text === ' ' ? '(Blank)' : state.text);
      p.style.color = state.hidden ? '#94a3b8' : state.color;
      document.getElementById('tagPos').innerText = `Pos: (${state.posX}, ${state.posY})`;
      document.getElementById('tagSize').innerText = `Size: ${state.size}px`;
      document.getElementById('tagColor').innerText = `Color: ${state.color}`;
      document.getElementById('visBadge').innerText = state.hidden ? '● Hidden' : '● Active';
      document.getElementById('visBadge').style.color = state.hidden ? '#ef4444' : '#10b981';
      document.getElementById('visText').innerText = state.hidden ? 'Show Overlay Text' : 'Hide Overlay Text';
    }

    window.addEventListener('DOMContentLoaded', async () => {
      try {
        const res = await fetch('/api/status');
        const d = await res.json();
        if (d.text !== undefined) state.text = d.text;
        if (d.color) state.color = d.color;
        if (d.font_size) state.size = d.font_size;
        if (d.pos_x !== undefined) state.posX = d.pos_x;
        if (d.pos_y !== undefined) state.posY = d.pos_y;
        if (d.is_hidden !== undefined) state.hidden = d.is_hidden;
        renderState();
      } catch (e) {}
    });

    function sendText(e) {
      if (e) e.preventDefault();
      const input = document.getElementById('customText');
      const val = input.value;
      if (val !== undefined && val !== '') {
        state.text = val;
        renderState();
        api('/api/text', { text: val });
        showToast('Updated text');
        input.value = '';
      }
    }

    function sendQuick(txt) {
      state.text = txt;
      renderState();
      api('/api/text', { text: txt });
      showToast(txt === ' ' ? 'Cleared screen' : `Sent: "${txt}"`);
    }

    function sendColor(hex) {
      state.color = hex;
      renderState();
      document.querySelectorAll('.color-swatch').forEach(el => {
        el.classList.toggle('active', el.style.backgroundColor.includes(hex.toLowerCase()) || el.style.background.includes(hex));
      });
      api('/api/color', { color: hex });
      showToast('Color updated');
    }

    function changeSize(delta) {
      state.size = Math.max(8, Math.min(72, state.size + delta));
      renderState();
      api('/api/size', { delta: delta });
      showToast(`Size: ${state.size}px`);
    }

    function move(dx, dy) {
      state.posX = Math.max(0, state.posX + dx);
      state.posY = Math.max(0, state.posY + dy);
      renderState();
      api('/api/move', { dx: dx, dy: dy });
      showToast(`Moved (${state.posX}, ${state.posY})`);
    }

    function setPos(preset) {
      api('/api/preset_pos', { preset: preset });
      showToast(`Position: ${preset}`);
      setTimeout(async () => {
        const res = await fetch('/api/status');
        const d = await res.json();
        state.posX = d.pos_x;
        state.posY = d.pos_y;
        renderState();
      }, 100);
    }

    function toggleVisibility() {
      state.hidden = !state.hidden;
      renderState();
      api('/api/toggle', {});
      showToast(state.hidden ? 'Hidden on screen' : 'Visible on screen');
    }

    function closeOverlay() {
      if (confirm('Close overlay on PC?')) {
        api('/api/exit', {});
        document.body.innerHTML = '<div style="text-align:center;padding:60px 20px;"><div style="font-size:42px;margin-bottom:12px;">✅</div><h2>Overlay Terminated</h2><p style="color:#94a3b8;margin-top:8px;">The background process has exited.</p></div>';
      }
    }
  </script>
</body>
</html>
"""


class WebRequestHandler(BaseHTTPRequestHandler):
    app: OverlayApp = None

    def log_message(self, format, *args):
        # Silent HTTP logging to keep console clean
        return

    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            if parsed.path in ("/", "/index.html"):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(HTML_PAGE.encode("utf-8"))
            elif parsed.path == "/api/status":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                data = json.dumps({
                    "text": self.app.current_text,
                    "color": self.app.current_color,
                    "font_size": self.app.font_size,
                    "pos_x": self.app.pos_x,
                    "pos_y": self.app.pos_y,
                    "is_hidden": self.app.is_hidden
                })
                self.wfile.write(data.encode("utf-8"))
            else:
                self.send_response(404)
                self.end_headers()
        except Exception:
            pass

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length > 0 else b"{}"
            try:
                payload = json.loads(body.decode("utf-8"))
            except Exception:
                payload = {}

            parsed = urlparse(self.path)

            if parsed.path == "/api/text":
                new_text = payload.get("text", "")
                self.app.root.after(0, self.app.set_text, new_text)
            elif parsed.path == "/api/color":
                hex_color = payload.get("color", "#000000")
                self.app.root.after(0, self.app.set_color, hex_color)
            elif parsed.path == "/api/size":
                delta = int(payload.get("delta", 0))
                self.app.root.after(0, self.app.set_font_size, delta)
            elif parsed.path == "/api/move":
                dx = int(payload.get("dx", 0))
                dy = int(payload.get("dy", 0))
                self.app.root.after(0, self.app.move_by, dx, dy)
            elif parsed.path == "/api/preset_pos":
                preset = payload.get("preset", "top-left")
                self.app.root.after(0, self.app.set_preset_pos, preset)
            elif parsed.path == "/api/toggle":
                self.app.root.after(0, self.app.toggle_visibility)
            elif parsed.path == "/api/exit":
                self.app.root.after(0, self.app.exit_app)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
        except Exception:
            pass


class ReusableHTTPServer(HTTPServer):
    # Prevents WinError 10048 (Address already in use) when restarting quickly
    allow_reuse_address = True


def start_server(app: OverlayApp):
    WebRequestHandler.app = app
    server = ReusableHTTPServer(("0.0.0.0", PORT), WebRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def start_hotkey_listener(app: OverlayApp):
    """Emergency hotkey listener on PC: Ctrl + Shift + X cleanly terminates."""
    def listener():
        while True:
            time.sleep(0.15)
            try:
                ctrl = ctypes.windll.user32.GetAsyncKeyState(0x11) & 0x8000
                shift = ctypes.windll.user32.GetAsyncKeyState(0x10) & 0x8000
                x_key = ctypes.windll.user32.GetAsyncKeyState(0x58) & 0x8000
                if ctrl and shift and x_key:
                    app.root.after(0, app.exit_app)
                    break
            except Exception:
                pass

    t = threading.Thread(target=listener, daemon=True)
    t.start()


def main():
    local_ip = get_local_ip()
    url = f"http://{local_ip}:{PORT}"

    print("=" * 60)
    print("             SCREEN OVERLAY (PRESENTATION READY)")
    print("=" * 60)
    print(f" [!] Open this URL on your phone/tablet browser:")
    print(f"     👉  {url}")
    print("=" * 60)
    print(" - Clicks pass through 100%.")
    print(" - Hidden from Zoom screen share & recordings.")
    print(" - Keep-on-top active: stays above full-screen slides.")
    print(" - Emergency Stop Hotkey: Ctrl + Shift + X")
    print("=" * 60)

    app = OverlayApp()
    start_server(app)
    start_hotkey_listener(app)

    try:
        app.root.mainloop()
    except KeyboardInterrupt:
        app.exit_app()


if __name__ == "__main__":
    main()
