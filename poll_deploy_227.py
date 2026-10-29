import requests
import time
import sys

URL = "https://chat-doc-sgdz.onrender.com/health"
print("Waiting for Render to deploy version 2.2.7...")

start_time = time.time()
while time.time() - start_time < 360:
    try:
        r = requests.get(URL, timeout=8)
        if r.status_code == 200:
            data = r.json()
            ver = data.get("version")
            elapsed = int(time.time() - start_time)
            print(f"[{elapsed}s] Status: {r.status_code}, Version: {ver}")
            if ver == "2.2.7":
                print("SUCCESS: Deployed version 2.2.7 is now active!")
                sys.exit(0)
    except Exception as e:
        elapsed = int(time.time() - start_time)
        print(f"[{elapsed}s] Connecting... ({e})")
    time.sleep(6)

print("TIMEOUT waiting for deployment.")
sys.exit(1)
