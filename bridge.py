import xled
import sacn
import time
import socket
import sys
import base64
import json
import os
import subprocess

# ==========================================
# CONFIGURATION LOADER
# ==========================================
CONFIG_FILE = "config.json"

# Default settings (Fallback)
config = {
    "device_ip": "192.168.1.100",
    "num_leds": 210,
    "pad_bytes": 0,
    "map_u1": [0, 1, 2, 3],
    "map_u2": [2, 1, 3, 0]
}

# Load config from file if it exists
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, 'r') as f:
            config.update(json.load(f))
        print(f"Loaded configuration from {CONFIG_FILE}")
    except Exception as e:
        print(f"Error loading config.json: {e}")

TWINKLY_IP = config["device_ip"]
NUM_LEDS = config["num_leds"]
PAD_BYTES = config["pad_bytes"]
MAP_U1 = config["map_u1"]
MAP_U2 = config["map_u2"]
START_UNIVERSE = 1

print(f"--- Twinkly Bridge (OpenRGB to UDP) ---")
print(f"Target: {TWINKLY_IP} | LEDs: {NUM_LEDS}")
print(f"Fixes Applied: Shift={PAD_BYTES} | U1={MAP_U1} | U2={MAP_U2}")

# ------------------------------------------
# Helper: Check if device is reachable
# ------------------------------------------
def is_device_reachable(ip, timeout=2):
    """Check if device responds to ping."""
    try:
        result = subprocess.run(
            ['ping', '-c', '1', '-W', str(timeout), ip],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return result.returncode == 0
    except:
        # Fallback: Try socket connection
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((ip, 80))
            sock.close()
            return True
        except:
            return False

# ------------------------------------------
# 1. Authentication & Setup (with Retry)
# ------------------------------------------
MAX_RETRIES = 5
RETRY_DELAY = 10

for attempt in range(1, MAX_RETRIES + 1):
    try:
        print(f"\nAttempt {attempt}/{MAX_RETRIES}: Checking device connectivity...", end="")
        
        # Pre-check: Is device reachable?
        if not is_device_reachable(TWINKLY_IP):
            raise ConnectionError(f"Device at {TWINKLY_IP} is not reachable (no ping response)")
        
        print(" OK")
        print("Connecting to Twinkly...", end="")
        control = xled.ControlInterface(TWINKLY_IP)
        
        # Force internal login via dummy command
        try: 
            control.set_mode('movie')
        except: 
            pass 
        
        # Retrieve Token
        TOKEN = control.session.access_token
        if not TOKEN:
            try: 
                control.login()
                TOKEN = control.session.access_token
            except Exception as login_err:
                raise ValueError(f"Login failed: {login_err}")
        
        # Decode Token (Handle Base64 or raw bytes)
        if isinstance(TOKEN, str):
            try: 
                REAL_TOKEN = base64.b64decode(TOKEN)
            except: 
                REAL_TOKEN = TOKEN.encode('utf-8')
        else:
            REAL_TOKEN = TOKEN

        if not REAL_TOKEN:
            raise ValueError("Could not retrieve valid authentication token")

        print(" Success!")
        
        # Switch device to Real-Time mode
        control.set_mode('rt')
        print("Device switched to Real-Time mode.")
        break  # Connection successful, exit retry loop

    except Exception as e:
        print(f" Failed!")
        print(f"[ERROR] {e}")
        
        if attempt < MAX_RETRIES:
            print(f"Retrying in {RETRY_DELAY} seconds...")
            time.sleep(RETRY_DELAY)
        else:
            print(f"\n" + "="*60)
            print(f"[FATAL] Connection failed after {MAX_RETRIES} attempts.")
            print(f"\nTroubleshooting checklist:")
            print(f"  1. Is the Twinkly device powered ON?")
            print(f"  2. Is the device connected to the network?")
            print(f"  3. Is the IP address correct? (Current: {TWINKLY_IP})")
            print(f"     → Check IP in the Twinkly mobile app")
            print(f"  4. Is the Twinkly mobile app fully CLOSED?")
            print(f"     → The app blocks Real-Time mode")
            print(f"  5. Is your firewall blocking UDP port 7777?")
            print(f"\nFor autostart issues (systemd):")
            print(f"  - Device may not be ready at boot time")
            print(f"  - Consider increasing RestartSec in service file")
            print(f"  - See README.md for recommended service configuration")
            print("="*60)
            sys.exit(1)

# ------------------------------------------
# 2. E1.31 Receiver Setup
# ------------------------------------------
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
receiver = sacn.sACNreceiver()
receiver.start()
rgb_buffer = [0] * (NUM_LEDS * 3) # Buffer for RGB data (3 channels per LED)

def send_to_twinkly():
    """
    Constructs the raw UDP packet with header, padding, and mapped pixel data,
    then sends it to the device.
    """
    try:
        final_data = bytearray()
        
        # Apply Global Shift (Padding)
        for _ in range(PAD_BYTES): final_data.append(0)

        # Process pixels
        for i in range(0, len(rgb_buffer), 3):
            if i + 2 >= len(rgb_buffer): break
            
            # Create input pool for RGBW Gen 2: [G, W, B, R]
            # This fixes the color channel interpretation issue
            pool = [rgb_buffer[i+1], 0, rgb_buffer[i+2], rgb_buffer[i]]
            
            # Determine which Universe map to use
            if (i // 3) < 170:
                mapping = MAP_U1
            else:
                mapping = MAP_U2
            
            # Construct pixel based on mapping
            pixel = []
            for idx in mapping:
                pixel.append(pool[idx])
            
            final_data.extend(pixel)

        # Construct V1 Header with Token
        header = b'\x01' + REAL_TOKEN 
        
        # Send UDP packet
        udp_sock.sendto(header + final_data, (TWINKLY_IP, 7777))
    except Exception as e:
        pass

# ------------------------------------------
# 3. Callbacks
# ------------------------------------------
@receiver.listen_on('universe', universe=START_UNIVERSE)
def callback_u1(packet):
    data = list(packet.dmxData[:510])
    data.extend([0] * (510 - len(data)))
    rgb_buffer[0:510] = data
    send_to_twinkly()

@receiver.listen_on('universe', universe=START_UNIVERSE + 1)
def callback_u2(packet):
    data = list(packet.dmxData)
    offset = 510
    rem = (NUM_LEDS * 3) - offset
    chunk = data[:rem]
    chunk.extend([0] * (rem - len(chunk)))
    rgb_buffer[offset : offset + len(chunk)] = chunk
    send_to_twinkly()

print(f"\nBridge is running. Listening on Universes {START_UNIVERSE} & {START_UNIVERSE+1}...")
receiver.join_multicast(START_UNIVERSE)
receiver.join_multicast(START_UNIVERSE + 1)

try:
    while True: time.sleep(1)
except KeyboardInterrupt:
    print("\nStopping bridge...")
    receiver.stop()