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

## Installation (Bash not Fish!!)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Saschlik/twinkly-openrgb-bridge.git
   cd twinkly-openrgb-bridge
   ```

2. **Create a virtual environment (Recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # venv\Scripts\activate   # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
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
1. Create `~/.config/systemd/user/twinkly-bridge.service`:
   ```ini
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
2. Run `systemctl --user enable --now twinkly-bridge`.

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

### Colors are still wrong
- Ensure `pad_bytes` is set to `0`.
- Verify your device is RGBW Gen 2 (model TWW210SPP2 or similar).
- Try the diagnostic `scanner.py` tool to find the correct configuration.

### Bridge won't connect
- Close the Twinkly mobile app completely (it blocks the Real-Time mode).
- Verify the IP address is correct.
- Ensure your firewall allows UDP traffic on port 7777.

### Universe 2 colors are shifted
- This is expected behavior - the `map_u2` setting corrects this.
- If still wrong, try different map_u2 values: `[0, 1, 2, 3]` or `[x, 1, x, x]`(try couple variations).

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

## Credits
Powered by [`xled`](https://github.com/scrool/xled) and [`sacn`](https://github.com/Hundemeier/sacn).
