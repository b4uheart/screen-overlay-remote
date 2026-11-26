# ⚡ Screen Overlay Remote (Headless Daemon + Mobile Projector)

[![OS: Windows / Cross-Platform](https://img.shields.io/badge/OS-Windows%20%7C%20Linux%20%7C%20macOS-0078D6?logo=windows&logoColor=white)](https://microsoft.com)
[![Python: 3.8+](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![Dependencies: 0 Pip Packages](https://img.shields.io/badge/Dependencies-0%20Pip%20Packages-success)](https://github.com/b4uheart/screen-overlay-remote)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A lightweight, **100% headless network daemon** that runs on your host PC and **projects live text, cues, numbers, and notes directly onto any smartphone or tablet browser over local Wi-Fi**.

Designed for situations where you want presenter cues, teleprompting, or notes **without rendering any windows or pixels on your host PC monitor**.

---

## 🌟 Key Architecture & Highlights

- **100% Headless on Host PC:** No Tkinter window, no Win32 top-level window, and **zero pixels drawn on your PC monitor**.
- **Immune to Windows Desktop Switches:** Because nothing is drawn on the PC display, separate Windows Desktops (`CreateDesktop` / `SwitchDesktop`), proctoring software, and lock-down environments cannot occlude or interact with it.
- **Zero OS GUI Footprint:** Invisible to `EnumWindows` window enumeration because no graphical window handle (`HWND`) exists on the host.
- **Dual Web Interface:**
  1. **Mobile Projector Screen (`/display`):** The live fullscreen display you open on your phone or tablet. OLED pitch-black background, ultra-crisp typography, auto-reconnecting Server-Sent Events (SSE), and Screen WakeLock (screen never turns off).
  2. **Controller Interface (`/`):** The remote control dashboard with custom text input, fast single-tap buttons (`1`, `2`, `3`, `4` and `A`, `B`, `C`, `D`), sequences, color swatches, and font steppers.
- **Instant Live Push (<30ms):** Uses HTTP Server-Sent Events (SSE) to push text updates to connected mobile screens immediately without polling lag.
- **Zero External Dependencies:** Built 100% with standard Python libraries (`http.server`, `socket`, `threading`, `json`). No `pip install` required!

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/b4uheart/screen-overlay-remote.git
cd screen-overlay-remote
```

### 2. Start the Daemon

| File | Mode | Description |
| :--- | :--- | :--- |
| **`start_silent.vbs`** *(Recommended)* | **Stealth Mode** | Starts `pythonw.exe` in the background with **0 command windows and 0 taskbar buttons**. Shows a brief 4-second self-closing toast notification on start. |
| **`run_overlay.bat`** | **Console Mode** | Launches with a Command Prompt window displaying your exact local Wi-Fi IP and URLs. |

---

## 📱 How to Use with Your Phone

1. Make sure your phone/tablet is connected to the **same Wi-Fi network** as your PC.
2. Open your phone's browser (Safari, Chrome, etc.):

### Step A: Open the Projector Screen on Your Phone
Navigate to:
```text
http://<YOUR-PC-IP>:5050/display
```
* **Fullscreen:** Tap anywhere on the screen to enter full-screen mode.
* **Stay-Awake:** Keeps your phone screen locked ON so it never sleeps or dims during use.

### Step B: Open the Controller (on PC or Second Phone)
Navigate to:
```text
http://<YOUR-PC-IP>:5050/
```
*(Or open `http://localhost:5050` in a browser on your PC)*

Whenever you tap **`1`**, **`2`**, **`A`**, **`B`**, or type custom text on the controller, it **instantly appears on the mobile projector screen**!

---

## 🎮 Controller Features

- **Instant Quick Buttons:**
  - Numbers: `1`, `2`, `3`, `4`
  - Letters: `A`, `B`, `C`, `D`
  - Sequences: `45, a, b, c`, `Ready`, `🧹 Clear`
- **Live Text Input:** Type any phrase or response and click **Send**.
- **Color Styling:** Emerald Green, Crisp White, Electric Cyan, Amber Gold, Crimson Red, and Violet.
- **Font Size Steppers:** `A+ Bigger Font` and `A- Smaller Font`.
- **Visibility Toggle:** Instantly hide or reveal text on the phone screen with one tap.
- **Remote Shutdown:** Cleanly stop the background PC daemon directly from the web interface.

---

## 🛑 How to Stop / Close the Daemon

1. **From the Web Controller:** Tap the red **❌ Shutdown Host Daemon** button.
2. **1-Click Stop Script:** Double-click **`stop_overlay.bat`** on your PC to kill the background process immediately.
3. **From Console (if using BAT):** Press **`Ctrl + C`** in the command prompt.

---

## 📁 Repository Structure

```text
├── overlay.py         # Multi-threaded headless daemon (SSE server + Controller & Display)
├── start_silent.vbs   # Silent launcher (0 taskbar presence, runs via pythonw)
├── run_overlay.bat    # Interactive launcher with console connection info
├── stop_overlay.bat   # 1-click process cleanup script
├── .gitignore         # Git ignore rules
└── README.md          # Project documentation
```

---

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).
