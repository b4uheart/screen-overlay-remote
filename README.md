# ⚡ Screen Overlay Remote

[![OS: Windows 10 / 11](https://img.shields.io/badge/OS-Windows%2010%20%7C%2011-0078D6?logo=windows&logoColor=white)](https://microsoft.com)
[![Python: 3.8+](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![Dependencies: 0 Pip Packages](https://img.shields.io/badge/Dependencies-0%20Pip%20Packages-success)](https://github.com/b4uheart/screen-overlay-remote)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A lightweight, high-performance desktop screen overlay for Windows with **zero taskbar footprint** and **full real-time control over local Wi-Fi from your smartphone or tablet**.

Built specifically for presentations, live streaming, meeting HUDs, and discreet presenter notes.

---

## 🌟 Key Features

- **100% Transparent Background:** Only the active text is rendered; no borders, title bars, or canvas background.
- **Full Mouse Click-Through:** Clicks pass straight through to any window, presentation, or desktop underneath (`WS_EX_TRANSPARENT`).
- **Screen Capture Protection:** Completely invisible in screen shares, screenshots, and screen recordings (Zoom, OBS Studio, Discord, Microsoft Teams, Snipping Tool) using Windows native `SetWindowDisplayAffinity` (`WDA_EXCLUDEFROMCAPTURE = 0x11`).
- **Zero Taskbar Footprint:** Runs windowless via `pythonw.exe` — your taskbar only shows your presentation software (e.g., Zoom).
- **Mobile Wi-Fi Remote Control:** Built-in web controller served directly from Python. Type text, switch presets, move position, adjust font size, and change colors live from your phone.
- **Persistent Topmost Watchdog:** Commands the Windows Desktop Window Manager (DWM) every 250ms via native 64-bit `SetWindowPos(HWND_TOPMOST)` so full-screen slides or newly focused windows never bury the overlay.
- **Zero External Dependencies:** Built entirely using Python standard libraries. No `pip install` required!

---

## 📋 Prerequisites & Dependencies

### 1. Operating System
* **Windows 10 (Version 2004 or later) or Windows 11** *(required for `WDA_EXCLUDEFROMCAPTURE` capture exclusion)*.

### 2. Python Environment
* **Python 3.8 or higher** (Python 3.10+ recommended).
* **Included Standard Libraries Used:**
  * `ctypes` (Win32 user32 API bindings)
  * `tkinter` (Native GUI rendering engine)
  * `http.server` (Lightweight remote web server)
  * `socket`, `threading`, `json`, `os`, `sys`

> **Note on Python Installation:**  
> When installing Python on Windows, make sure the default option **"tcl/tk and IDLE"** is checked (this is checked by default in the official installer from [python.org](https://www.python.org/downloads/)).  
> **No third-party packages (`pip install`) are required!**

---

## 🚀 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/b4uheart/screen-overlay-remote.git
cd screen-overlay-remote
```

### 2. Run the Overlay

You have two ways to start the overlay depending on your scenario:

| File | Mode | Use Case |
| :--- | :--- | :--- |
| **`start_silent.vbs`** *(Recommended)* | **Stealth Mode** | Starts via `pythonw.exe` with **0 command windows and 0 taskbar icons**. Shows a brief 3-second self-closing toast notification on launch. |
| **`run_overlay.bat`** | **Interactive / Debug** | Opens a Command Prompt window displaying your local Wi-Fi IP and connection URL. |

---

## 📱 Connecting Your Phone / Tablet

1. Connect your phone or tablet to the **same Wi-Fi network** as your Windows PC.
2. Open any browser (Safari, Chrome, Firefox) on your mobile device.
3. Navigate to:
   ```text
   http://<YOUR-PC-IP>:5050
   ```
   *(To find your PC's IP address manually, open Command Prompt on your PC and run `ipconfig`, then look for IPv4 Address, e.g. `192.168.1.50`)*.

---

## 🎮 Mobile Remote Controls

The mobile web controller includes:

* **Live Output Monitor:** A real-time mirror showing the exact text currently displayed on your PC screen, along with position coordinates `(X, Y)`, font size, and color.
* **Instant Text Input:** Type custom text into the field and tap **Send** (or press Enter).
* **Quick Presets:** One-tap chips for:
  * Letters: `A`, `B`, `C`, `D`
  * Digits: `1`, `2`, `3`, `4`
  * Sequences: `45, a, b, c`, `Ready`, and `🧹 Clear` (blank screen).
* **3x3 D-Pad Positioner:** Arrow buttons (`▲`, `▼`, `◀`, `▶`) to nudge text by 25px in any direction, plus corner snaps (`↖ Top-Left`, `↗ Top-Right`, `↙ Bottom-Left`, `↘ Bottom-Right`, `● Center`).
* **Styling Tools:**
  * 6 preset color swatches: Classic Black, Emerald Green, Pure White, Crimson Red, Electric Cyan, Amber Gold.
  * `A+ Enlarge` / `A- Shrink` buttons with real-time pixel size readout.
* **Visibility Toggle:** Instantly hide or show the overlay text.
* **Remote Shutdown:** Cleanly terminate the background process directly from your phone.

---

## 🛑 How to Stop / Close the Overlay

Since the overlay is click-through and runs with no taskbar button in silent mode, you can stop it using any of these 3 methods:

1. **From Your Phone (Most Discreet):** Tap the red **❌ Close Overlay on PC** button at the bottom of the mobile web controller.
2. **Global Keyboard Hotkey:** Press **`Ctrl + Shift + X`** anywhere on your PC keyboard.
3. **1-Click Stop Script:** Double-click **`stop_overlay.bat`** on your PC to kill the background process immediately.

---

## 📁 Repository Structure

```text
├── overlay.py         # Main script (Tkinter overlay + multi-threaded HTTP server)
├── start_silent.vbs   # Silent launcher (0 taskbar presence, runs via pythonw)
├── run_overlay.bat    # Interactive launcher with console connection info
├── stop_overlay.bat   # 1-click process cleanup script
├── .gitignore         # Git ignore rules
└── README.md          # Project documentation
```

---

## 🔧 Troubleshooting

### 1. Phone cannot connect to `http://<IP>:5050`
* Ensure both your phone and PC are on the **exact same Wi-Fi network** (not guest Wi-Fi or cellular data).
* If Windows Defender Firewall shows a prompt when running Python for the first time, click **Allow access** on Private networks.
* To check if the port is accessible, try visiting `http://localhost:5050` in a browser on the PC itself.

### 2. `_tkinter` Not Found
If you see an error like `No module named '_tkinter'`, run the official Python Windows installer again, choose **Modify**, and make sure the **"tcl/tk and IDLE"** feature is checked.

### 3. Overlay Appears Behind Certain Apps
The built-in watchdog calls native 64-bit `SetWindowPos(HWND_TOPMOST)` every 250ms to keep it on top. However, special Windows system surfaces (like the Windows UAC Secure Desktop or applications running on isolated desktops) are protected by the Windows kernel and do not allow standard desktop windows to composite over them.

---

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).
