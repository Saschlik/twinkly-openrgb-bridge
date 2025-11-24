import xled
import sacn
import time
import socket
import sys
import base64
import json
import os

# ==========================================
# CONFIGURATION LOADER
# ==========================================
CONFIG_FILE = "config.json"

# Default settings (Fallback)
config = {
    "device_ip": "192.168.1.100",
    "num_leds": 210,
    "pad_bytes": 2,
    "map_u1": [0, 1, 2, 3],
    "map_u2": [1, 2, 0, 3]
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
# 1. Authentication & Setup
# ------------------------------------------
try:
    print("Connecting to Twinkly...", end="")
    control = xled.ControlInterface(TWINKLY_IP)
    
    # Force internal login via dummy command
    try: control.set_mode('movie')
    except: pass 
    
    # Retrieve Token
    TOKEN = control.session.access_token
    if not TOKEN:
        try: control.login()
        except: pass
        TOKEN = control.session.access_token
    
    # Decode Token (Handle Base64 or raw bytes)
    if isinstance(TOKEN, str):
        try: REAL_TOKEN = base64.b64decode(TOKEN)
        except: REAL_TOKEN = TOKEN.encode('utf-8')
    else:
        REAL_TOKEN = TOKEN

    if not REAL_TOKEN:
        raise ValueError("Could not retrieve valid authentication token.")

    print(" Success!")
    
    # Switch device to Real-Time mode
    control.set_mode('rt')

except Exception as e:
    print(f"\n[ERROR] Connection failed: {e}")
    print("Tip: Ensure the mobile app is fully closed and the device IP is correct.")
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
            
            # Create input pool: [R, G, B, 0]
            pool = [rgb_buffer[i], rgb_buffer[i+1], rgb_buffer[i+2], 0]
            
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
    while len(data) < 510: data.append(0)
    rgb_buffer[0:510] = data
    send_to_twinkly()

@receiver.listen_on('universe', universe=START_UNIVERSE + 1)
def callback_u2(packet):
    data = list(packet.dmxData)
    offset = 510
    rem = (NUM_LEDS * 3) - offset
    chunk = data[:rem]
    while len(chunk) < rem: chunk.append(0)
    rgb_buffer[offset : offset + len(chunk)] = chunk
    send_to_twinkly()

print(f"Bridge is running. Listening on Universes {START_UNIVERSE} & {START_UNIVERSE+1}...")
receiver.join_multicast(START_UNIVERSE)
receiver.join_multicast(START_UNIVERSE + 1)

try:
    while True: time.sleep(1)
except KeyboardInterrupt:
    print("\nStopping bridge...")
    receiver.stop()
