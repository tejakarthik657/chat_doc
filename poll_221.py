import time
import requests

URL = "https://chat-doc-sgdz.onrender.com/health"
print("Waiting for Render to deploy version 2.2.1...")

start = time.time()
while time.time() - start < 300:
    try:
        r = requests.get(URL, timeout=5)
        if r.status_code == 200:
            data = r.json()
            ver = data.get("version")
            print(f"[{int(time.time() - start)}s] Status: {r.status_code}, Version: {ver}")
            if ver == "2.2.1":
                print("SUCCESS: Deployed version 2.2.1 is now active!")
                break
        else:
            print(f"[{int(time.time() - start)}s] HTTP {r.status_code}")
    except Exception as e:
        print(f"[{int(time.time() - start)}s] Waiting: {e}")
    time.sleep(5)
