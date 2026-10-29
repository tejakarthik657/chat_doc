import httpx
import time

url = 'https://chat-doc-sgdz.onrender.com/health'
print('Waiting for Render deployment of version 2.2.0...')
start = time.time()
while time.time() - start < 300:
    try:
        r = httpx.get(url, timeout=5.0)
        if r.status_code == 200:
            data = r.json()
            ver = data.get('version')
            print(f'[{time.strftime("%X")}] HTTP 200 | version: {ver}', flush=True)
            if ver == '2.2.0':
                print('[SUCCESS] Deployment succeeded! Version 2.2.0 is live.', flush=True)
                break
        else:
            print(f'[{time.strftime("%X")}] HTTP {r.status_code}', flush=True)
    except Exception as e:
        print(f'[{time.strftime("%X")}] Waiting... ({e.__class__.__name__})', flush=True)
    time.sleep(5)
