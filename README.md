# Twinkly OpenRGB Bridge (RGBW Gen 2 Fix)

A lightweight Python bridge to control **Twinkly** LED strings (specifically **Gen 2 RGBW Special Editions**) via **OpenRGB** using the E1.31 (sACN) protocol.

## The Problem
Twinkly devices do not natively support E1.31. While standard bridges exist, **Gen 2 RGBW devices** (like the TWW210SPP2) often exhibit severe color mapping issues due to:
1. **Byte Shifting:** The proprietary UDP header or frame format consumes bytes differently than V1 protocols, shifting all colors.
2. **Color Channel Misinterpretation:** The hardware interprets color channels in a non-standard order (Green, White, Blue, Red instead of RGB/RGBW).
3. **Mapping Inconsistencies:** OpenRGB sometimes maps the second DMX universe differently than the first, causing split colors across LED segments.

## The Solution
This bridge acts as a "Man-in-the-Middle":
1. Receives E1.31 data from OpenRGB.
2. **Reorders color channels** to match the Gen 2 RGBW hardware expectation: `[G, W, B, R]` instead of `[R, G, B, W]`.
3. Applies a configurable **Byte Padding** (Global Shift) to align the data stream (set to `0` for Gen 2 RGBW).
4. Applies **Matrix Mapping** per Universe to correct specific color swaps between universes.
5. Sends raw UDP packets to the Twinkly device in Real-Time mode.

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Saschlik/twinkly-openrgb-bridge.git
   cd twinkly-openrgb-bridge
   ```

2. **Create and Activate a virtual environment:**
   *Required to avoid "externally-managed-environment" errors on Arch Linux, Fedora, etc.*
   ```bash
   python -m venv venv
   
   # Activate the environment:
   source venv/bin/activate      # Linux/Mac (Bash/Zsh)
   # source venv/bin/activate.fish # Linux/Mac (Fish Shell)
   # venv\Scripts\activate       # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Start the bridge:**
   ```bash
   python bridge.py
   ```

## Configuration

1. Rename `config.json.example` to `config.json`.
2. Open `config.json` and set your **Twinkly IP** and **LED count**.

```json
{
    "device_ip": "192.168.178.XX",
    "num_leds": 210,
    "pad_bytes": 0,
    "map_u1": [0, 1, 2, 3],
    "map_u2": [2, 1, 3, 0] 
}
```

**Parameter Explanation:**
- **device_ip:** Your Twinkly device's IP address (find it in the Twinkly app).
- **num_leds:** Total number of LEDs in your string (e.g., 210 for Curtains).
- **pad_bytes:** Global byte shift - set to `0` for RGBW Gen 2 devices.
- **map_u1:** Channel mapping for Universe 1 (first 170 LEDs) - `[0, 1, 2, 3]` = no remapping.
- **map_u2:** Channel mapping for Universe 2 (remaining LEDs) - `[2, 1, 3, 0]` fixes color swap. **IMPORTANT more Info at the ReadMe.md bottom**

### Twinkly Curtain (210 LEDs) Matrix Layout
The Twinkly Curtains with 210 LEDs have the following matrix dimensions:
- **Width:** 7 LEDs
- **Height:** 30 LEDs

Use these dimensions when setting up 2D effects in OpenRGB or other software.

## Diagnostic Tools

If you don't know your shift or mapping, use the included scanner tool. It sends a pure RED signal while cycling through all possible shifts and orders.

### python scanner.py

Watch your lights. When they turn red, note the `Order` and `Shift` displayed in the terminal and update `config.json`.

## OpenRGB 0.9+ (git1702) Setup [or newer]

1. Add Device → **E1.31**.
2. **IP:** `127.0.0.1` (Localhost).
3. **Start Universe:** `1` ⚠️ **IMPORTANT: Must be set to 1!**
4. **Size:** Your LED count (e.g., 210).
5. **Type:** Linear (or Matrix with 7×30 for Curtains).
6. **Start Channel:** 1 (default).

**Note:** OpenRGB will automatically use Universe 1 and Universe 2 for LED strings exceeding 170 LEDs (510 DMX channels).

## Auto-Start Guide

Since OpenRGB does not natively start external scripts, use one of these methods:

### 🐧 Linux (Systemd User Service) - Recommended

**Basic Service (Recommended for most users):**

1. Create `~/.config/systemd/user/twinkly-bridge.service`:
   ```ini
   [Unit]
   Description=Twinkly OpenRGB Bridge
   After=network-online.target
   Wants=network-online.target

   [Service]
   # UPDATE PATHS!
   ExecStart=/home/YOUR_USER/twinkly-bridge/venv/bin/python /home/YOUR_USER/twinkly-bridge/bridge.py
   WorkingDirectory=/home/YOUR_USER/twinkly-bridge
   
   # Restart policy: only restart on failure, not on clean exit
   Restart=on-failure
   RestartSec=30
   
   # Stop trying after 5 failed attempts in 5 minutes
   StartLimitBurst=5
   StartLimitIntervalSec=300

   [Install]
   WantedBy=default.target
   ```

2. Enable and start:
   ```bash
   systemctl --user daemon-reload
   systemctl --user enable --now twinkly-bridge.service
   ```

3. Check status:
   ```bash
   systemctl --user status twinkly-bridge.service
   ```

**Advanced: With Failure Notifications (Optional):**

If you want desktop notifications when the service fails (e.g., device is offline):

1. Create notification service `~/.config/systemd/user/twinkly-bridge-notify.service`:
   ```ini
   [Unit]
   Description=Twinkly Bridge Failure Notification

   [Service]
   Type=oneshot
   ExecStart=/usr/bin/notify-send -u critical "Twinkly Bridge Failed" "Check if device is powered on and connected to network"
   ```

2. Add to your main service file:
   ```ini
   [Unit]
   Description=Twinkly OpenRGB Bridge
   After=network-online.target
   Wants=network-online.target
   OnFailure=twinkly-bridge-notify.service  # Add this line
   
   # ... rest of the service configuration
   ```

3. Reload:
   ```bash
   systemctl --user daemon-reload
   ```

### 🪟 Windows (Batch Script)
Create `start_all.bat`:
```batch
@echo off
cd /d "%~dp0"
start "" "venv\Scripts\pythonw.exe" bridge.py
start "" "C:\Program Files\OpenRGB\OpenRGB.exe" --startminimized
```

Place a shortcut to this file in your Startup folder (`Win+R` → `shell:startup`).

### 🍎 macOS (Automator)
1. Create a new **Application** in Automator.
2. Add **"Run Shell Script"**:
   ```bash
   /Users/USER/path/to/venv/bin/python /Users/USER/path/to/bridge.py &
   open -a OpenRGB
   ```
3. Add to **Login Items** in System Settings.

## Troubleshooting

### Service keeps restarting / Getting spam notifications

**Symptom:** `systemctl status` shows high restart counter, or you get repeated notifications.

**Most Common Cause:** Twinkly device is powered off or disconnected from network.

**Solution:**
1. Check if device is powered on and connected:
   ```bash
   ping YOUR_DEVICE_IP
   ```

2. View detailed error logs:
   ```bash
   journalctl --user -u twinkly-bridge.service -n 50
   ```

3. Stop the service temporarily:
   ```bash
   systemctl --user stop twinkly-bridge.service
   ```

4. Test manually to see exact error:
   ```bash
   cd ~/twinkly-bridge
   source venv/bin/activate
   python bridge.py
   ```

**Note:** The bridge includes automatic retry logic (5 attempts with 10-second delays). If your device is slow to boot or you start the service before the device is ready, it will keep trying for up to 50 seconds before giving up.

### Colors are still wrong
- Ensure `pad_bytes` is set to `0`.
- Verify your device is RGBW Gen 2 (model TWW210SPP2 or similar).
- Try the diagnostic `scanner.py` tool to find the correct configuration.

### Bridge won't connect
- **Check device power:** Is the Twinkly device turned on?
- **Check network:** Can you ping the device IP?
- **Close mobile app:** The Twinkly mobile app blocks Real-Time mode when open.
- **Verify IP address:** IP may have changed if assigned by DHCP. Check in Twinkly app.
- **Firewall:** Ensure UDP port 7777 is not blocked.

### Universe 2 colors are shifted
- This is expected behavior - the `map_u2` setting corrects this.
- If still wrong, try different map_u2 values: `[0, 1, 2, 3]` or `[x, 1, x, x]`(try couple variations).

### Device not ready at boot
If the bridge starts before your Twinkly device is ready (common with smart plugs or slow network):
- The built-in retry logic will attempt connection 5 times over 50 seconds
- If this isn't enough, increase `RestartSec=30` to `RestartSec=60` in your service file
- Consider setting a static IP for your Twinkly device in your router

## Technical Details

### RGBW Gen 2 Color Channel Order
The hardware expects pixels in this byte order:
```
[Green, White, Blue, Red]
```

The bridge automatically converts OpenRGB's standard RGB input:
```python
pool = [rgb_buffer[i+1], 0, rgb_buffer[i+2], rgb_buffer[i]]
# [G, W=0, B, R]
```

### Why Two Universes?
E1.31 DMX universes support a maximum of 512 channels. For RGB LEDs:
- 1 LED = 3 channels (R, G, B)
- 170 LEDs = 510 channels (fits in Universe 1) (That causes the Map_2 Shift where White is still white and RGB shifts by 2 bytes/channels)
- LEDs 171-210 require Universe 2

### Error Handling & Retry Logic
The bridge includes built-in connection retry logic:
- **5 retry attempts** with 10-second delays between each
- **Network connectivity check** before attempting connection
- **Clear error messages** indicating common issues
- Compatible with systemd's restart policies for robust autostart

## Credits
Powered by [`xled`](https://github.com/scrool/xled) and [`sacn`](https://github.com/Hundemeier/sacn).