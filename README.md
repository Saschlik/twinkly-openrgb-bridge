# Twinkly OpenRGB Bridge (RGBW Gen 2 Fix)

A lightweight Python bridge to control **Twinkly** LED strings (specifically **Gen 2 RGBW Special Editions**) via **OpenRGB** using the E1.31 (sACN) protocol.

## The Problem
Twinkly devices do not natively support E1.31. While standard bridges exist, **Gen 2 RGBW devices** (like the TWW210SPP2) often exhibit severe color mapping issues due to:
1.  **Byte Shifting:** The proprietary UDP header or frame format consumes bytes differently than V1 protocols, shifting all colors.
2.  **Mapping Inconsistencies:** OpenRGB sometimes maps the second DMX universe differently than the first, causing split colors.

## The Solution
This bridge acts as a "Man-in-the-Middle":
1.  Receives E1.31 data from OpenRGB.
2.  Applies a configurable **Byte Padding** (Global Shift) to align the data stream.
3.  Applies a **Matrix Mapping** per Universe to correct specific color swaps (e.g., Red/Green/Blue/White reordering).
4.  Sends raw UDP packets to the Twinkly device in Real-Time mode.

## Installation

1.  **Clone the repository:**
    ```
    git clone https://github.com/YOUR_USERNAME/twinkly-openrgb-bridge.git
    cd twinkly-openrgb-bridge
    ```

2.  **Create a virtual environment (Recommended):**
    ```
    python -m venv venv
    source venv/bin/activate  # Linux/Mac
    # venv\Scripts\activate   # Windows
    ```

3.  **Install dependencies:**
    ```
    pip install -r requirements.txt
    ```

## Configuration

1.  Rename `config.json.example` to `config.json`.
2.  Open `config.json` and set your **Twinkly IP** and **LED count**.

```
{
"device_ip": "192.168.1.50",
"num_leds": 250,
"pad_bytes": 2,
"map_u1": ,
"map_u2":
}
```


*   **pad_bytes:** Global byte shift (2 is common for RGBW Gen 2).
*   **map_u1/u2:** Remap channels per universe `[R_Input, G_Input, B_Input, W_Input]`.

## Diagnostic Tools

If you don't know your shift or mapping, use the included scanner tool. It sends a pure RED signal while cycling through all possible shifts and orders.

### python scanner.py

Watch your lights. When they turn red, note the `Order` and `Shift` displayed in the terminal and update `config.json`.

## OpenRGB Setup

1.  Add Device -> **E1.31**.
2.  IP: `127.0.0.1` (Localhost).
3.  Universe: 1.
4.  Size: Your LED count (e.g., 210).
5.  Type: Linear.

## Auto-Start Guide

Since OpenRGB does not natively start external scripts, use one of these methods:

### 🐧 Linux (Systemd User Service) - Recommended
1.  Create `~/.config/systemd/user/twinkly-bridge.service`:
    ```
    [Unit]
    Description=Twinkly OpenRGB Bridge
    After=network.target

    [Service]
    # UPDATE PATHS!
    ExecStart=/home/YOUR_USER/twinkly-bridge/venv/bin/python /home/YOUR_USER/twinkly-bridge/bridge.py
    WorkingDirectory=/home/YOUR_USER/twinkly-bridge
    Restart=always
    RestartSec=5

    [Install]
    WantedBy=default.target
    ```
2.  Run `systemctl --user enable --now twinkly-bridge`.

### 🪟 Windows (Batch Script)
Create `start_all.bat`:
```
@echo off
cd /d "%~dp0"
start "" "venv\Scripts\pythonw.exe" bridge.py
start "" "C:\Program Files\OpenRGB\OpenRGB.exe" --startminimized
```

Place a shortcut to this file in your Startup folder (`Win+R` -> `shell:startup`).

### 🍎 macOS (Automator)
1.  Create a new **Application** in Automator.
2.  Add **"Run Shell Script"**:
    ```
    /Users/USER/path/to/venv/bin/python /Users/USER/path/to/bridge.py &
    open -a OpenRGB
    ```
3.  Add to **Login Items** in System Settings.

## Credits
Powered by `xled` and `sacn`.
# twinkly-openrgb-bridge
# twinkly-openrgb-bridge
