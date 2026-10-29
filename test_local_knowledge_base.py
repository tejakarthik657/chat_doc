import httpx
import time
import sys

BASE_URL = "http://localhost:8000"

# 1. Login
print("=" * 60)
print("[KNOWLEDGE BASE TEST] Authenticating on Render...")
r_login = httpx.post(
    f"{BASE_URL}/api/auth/login",
    json={"email": "karthik1234@gmail.com", "password": "123456789"},
    timeout=15.0
)
if r_login.status_code != 200:
    print("Login failed:", r_login.text)
    sys.exit(1)

token = r_login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("[SUCCESS] Authenticated.")

# 2. Check or Create Project
print("\n[STEP 1] Creating Knowledge Base Project for https://kitsw.ac.in (Limit=50 pages)...")
payload = {
    "name": "KITSW Knowledge Base",
    "website_url": "https://kitsw.ac.in",
    "max_pages": 50,
    "use_dynamic_crawl": False
}

r_proj = httpx.post(f"{BASE_URL}/api/projects/create", headers=headers, json=payload, timeout=20.0)
print(f"Create project status: HTTP {r_proj.status_code}")
if r_proj.status_code not in [200, 201]:
    print("Error creating project:", r_proj.text)
    # Check if project already exists
    r_list = httpx.get(f"{BASE_URL}/api/projects", headers=headers, follow_redirects=True, timeout=15.0)
    projects = r_list.json().get("projects", [])
    kitsw_projs = [p for p in projects if "kitsw" in p.get("website_url", "").lower()]
    if kitsw_projs:
        project_id = kitsw_projs[0]["id"]
        print(f"Using existing project: {project_id}")
    else:
        sys.exit(1)
else:
    project_id = r_proj.json()["id"]
    print(f"Project created with ID: {project_id}")

# 3. Observe Crawling Progress
print(f"\n[STEP 2] Observing Crawl Progress for Project {project_id}...")
start_time = time.time()
crawl_completed = False

for check_no in range(40):
    time.sleep(3.0)
    elapsed = time.time() - start_time
    try:
        r_status = httpx.get(f"{BASE_URL}/api/projects/{project_id}", headers=headers, timeout=10.0)
        if r_status.status_code == 200:
            p_data = r_status.json()
            status = p_data.get("status")
            pages = p_data.get("pages_crawled", 0)
            docs = p_data.get("docs_found", 0)
            print(f"   [T+{elapsed:.1f}s] Status: {status} | Pages Crawled: {pages} | Docs Found: {docs}")
            if status in ["ready", "active", "completed"] and pages > 0:
                crawl_completed = True
                print(f"\n>>> CRAWL SUCCESS! Project is ACTIVE with {pages} pages, {docs} documents.")
                break
            elif status == "failed":
                print(f"Crawl failed: {p_data.get('error_message')}")
                break
    except Exception as e:
        print(f"   [T+{elapsed:.1f}s] Poll notice: {e}")

# 4. Chat with Knowledge Base
print(f"\n[STEP 3] Testing Project Intelligence / Knowledge Base Q&A...")
project_questions = [
    "What degree programs and departments are offered at KITSW?",
    "Who is the Principal of Kakatiya Institute of Technology & Science?",
    "What facilities and infrastructure are available on the KITSW campus?"
]

for idx, q in enumerate(project_questions, 1):
    print(f"\n--- Question {idx}: '{q}' ---")
    t0 = time.time()
    try:
        r_chat = httpx.post(
            f"{BASE_URL}/api/projects/{project_id}/chat",
            headers=headers,
            json={"question": q, "strict_mode": False},
            timeout=30.0
        )
        print(f"Response in {time.time()-t0:.2f}s | HTTP {r_chat.status_code}")
        if r_chat.status_code == 200:
            c_res = r_chat.json()
            print("Answer:", c_res.get("answer"))
            print("Grounded:", c_res.get("grounded"))
            sources = [s.get("source") for s in c_res.get("sources", [])]
            print("Sources:", sources[:3])
        else:
            print("Chat response:", r_chat.text[:300])
    except Exception as chat_err:
        print("Chat request error:", chat_err)

print("\n" + "=" * 60)
print("[ALL TESTS COMPLETED]")
