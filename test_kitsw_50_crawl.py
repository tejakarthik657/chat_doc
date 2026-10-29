import httpx
import time
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "https://chat-doc-sgdz.onrender.com"

print("=" * 60)
print("[STEP 1] Authenticating on Render Production...")
r_login = httpx.post(
    f"{BASE_URL}/api/auth/login",
    json={"email": "karthik1234@gmail.com", "password": "123456789"},
    timeout=20.0
)
if r_login.status_code != 200:
    print("Login failed:", r_login.text)
    sys.exit(1)

token = r_login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("[SUCCESS] Logged in successfully.")

# STEP 2: Create Project with max_pages=50
print("\n[STEP 2] Creating Knowledge Base project for https://kitsw.ac.in (Limit: 50 pages)...")
payload = {
    "name": "KITSW Main Portal (50 Pages)",
    "website_url": "https://kitsw.ac.in",
    "max_pages": 50,
    "use_dynamic_crawl": False
}

r_proj = httpx.post(f"{BASE_URL}/api/projects/create", headers=headers, json=payload, timeout=25.0)
print(f"Project creation status: HTTP {r_proj.status_code}")
if r_proj.status_code not in [200, 201]:
    print("Error creating project:", r_proj.text)
    sys.exit(1)

project_data = r_proj.json()
project_id = project_data["id"]
print(f"[SUCCESS] Created Project ID: {project_id}")

# STEP 3: Observe Crawl Progress
print(f"\n[STEP 3] Observing Crawl & Indexing Progress for Project {project_id}...")
start_time = time.time()
completed = False

for iteration in range(60):
    time.sleep(5.0)
    elapsed = time.time() - start_time
    try:
        r_status = httpx.get(f"{BASE_URL}/api/projects/{project_id}", headers=headers, timeout=12.0)
        if r_status.status_code == 200:
            p = r_status.json()
            st = p.get("status")
            pages = p.get("pages_crawled", 0)
            docs = p.get("docs_found", 0)
            print(f"   [T+{elapsed:.1f}s] Status: {st.upper():<10} | Pages Crawled: {pages:<3} | Docs Found: {docs}")
            if st in ["active", "completed", "ready"] and (pages > 0 or docs > 0):
                completed = True
                print(f"\n>>> CRAWL AND INDEXING SUCCESSFUL in {elapsed:.1f}s! Status: {st}")
                break
            elif st == "failed":
                print(f"\n[Crawl Notice] Status reached 'failed': {p.get('error_message')}")
                break
        else:
            print(f"   [T+{elapsed:.1f}s] Poll notice HTTP {r_status.status_code}")
    except Exception as poll_err:
        print(f"   [T+{elapsed:.1f}s] Poll warning: {poll_err}")

# STEP 4: Chat with Newly Crawled Knowledge Base
print(f"\n[STEP 4] Testing Knowledge Base Chat on Project {project_id}...")
test_questions = [
    "What is the vision, mission, and accreditation status of KITSW?",
    "What engineering branches and courses are offered at KITSW?",
    "Where is Kakatiya Institute of Technology & Science located and how can someone contact them?"
]

for idx, q in enumerate(test_questions, 1):
    print(f"\n--- Question {idx}: '{q}' ---")
    t0 = time.time()
    try:
        r_chat = httpx.post(
            f"{BASE_URL}/api/chat/project/{project_id}",
            headers=headers,
            json={"question": q, "strict_mode": False},
            timeout=50.0
        )
        dur = time.time() - t0
        print(f"Response in {dur:.2f}s | HTTP {r_chat.status_code}")
        if r_chat.status_code == 200:
            c_res = r_chat.json()
            print("Answer:", c_res.get("answer")[:350], "...")
            print("Grounded:", c_res.get("grounded"))
            sources = [s.get("source") or s.get("url") for s in c_res.get("sources", [])]
            print("Sources:", sources[:3])
        else:
            print("Chat response error:", r_chat.text[:200])
    except Exception as chat_err:
        print("Chat request error:", chat_err)

print("\n" + "=" * 60)
print("[VERIFICATION COMPLETED]")
