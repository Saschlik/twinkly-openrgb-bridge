import xled
import time
import socket
import sys
import base64
import json
import os

# ==========================================
# CONFIGURATION
# ==========================================
# Load from config.json if available, otherwise use placeholder
CONFIG_FILE = "config.json"
TWINKLY_IP = "CHANGE_ME" 
NUM_LEDS = 210

if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, 'r') as f:
            data = json.load(f)
            TWINKLY_IP = data.get("device_ip", TWINKLY_IP)
            NUM_LEDS = data.get("num_leds", NUM_LEDS)
    except: pass

if "CHANGE_ME" in TWINKLY_IP or "192.168" not in TWINKLY_IP:
    print("ERROR: Please set your IP in config.json or edit scanner.py")
    sys.exit(1)

print("--- Twinkly Diagnostic Scanner ---")
print(f"Target: {TWINKLY_IP}")
print("This tool cycles through byte-shifts and color orders to find the correct protocol.")
print("Connecting...", end="")

try:
    control = xled.ControlInterface(TWINKLY_IP)
    try: control.set_mode('movie')
    except: pass
    TOKEN = control.session.access_token
    if not TOKEN:
        try: control.login()
        except: pass
    TOKEN = control.session.access_token
    if isinstance(TOKEN, str):
        try: REAL_TOKEN = base64.b64decode(TOKEN)
        except: REAL_TOKEN = TOKEN.encode('utf-8')
    else: REAL_TOKEN = TOKEN
    control.set_mode('rt')
    print(" Success!")
except:
    print(" Login failed. Check IP.")
    sys.exit(1)

udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Create a fake buffer that is purely RED
fake_input_red = [255, 0, 0] * NUM_LEDS

def send_frame(pad, order):
    final_data = bytearray()
    # Apply padding
    for _ in range(pad): final_data.append(0)
    
    for i in range(0, len(fake_input_red), 3):
        r, g, b = fake_input_red[i], fake_input_red[i+1], fake_input_red[i+2]
        
        # Apply simple ordering
        if order == 'RGB': pixel = [r, g, b, 0]
        elif order == 'GRB': pixel = [g, r, b, 0]
        elif order == 'RBG': pixel = [r, b, g, 0]
        elif order == 'BGR': pixel = [b, g, r, 0]
        
        final_data.extend(pixel)
        
    header = b'\x01' + REAL_TOKEN 
    udp_sock.sendto(header + final_data, (TWINKLY_IP, 7777))

print("\nSTARTING SCAN... Watch your lights!")
print("Look for the moment when the lights turn FULLY RED.")

orders = ['RGB', 'GRB', 'RBG']
pads = [0, 1, 2, 3]

while True:
    for order in orders:
        for pad in pads:
            print(f"\n>>> TESTING: Order={order} | Shift={pad} <<<")
            # Burst send to ensure visibility
            for _ in range(10):
                send_frame(pad, order)
                time.sleep(0.05)
            
            print("   (Do the lights appear RED?)")
            time.sleep(1.5)
