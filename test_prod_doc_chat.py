import httpx
import fitz
import time
import os
import sys

BASE_URL = 'https://chat-doc-sgdz.onrender.com'

# 1. Login
print("=" * 60)
print("[STEP 1] Authenticating as karthik1234@gmail.com on Render...")
r_login = httpx.post(
    f'{BASE_URL}/api/auth/login',
    json={'email': 'karthik1234@gmail.com', 'password': '123456789'},
    timeout=15.0
)
if r_login.status_code != 200:
    print("Login failed:", r_login.text)
    sys.exit(1)

token = r_login.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}
print("[SUCCESS] Logged in. Token received.")

# 2. Create Real Academic/Engineering PDF
pdf_path = "KITSW_Computer_Science_Curriculum.pdf"
doc = fitz.open()

# Page 1: Department & Faculty
p1 = doc.new_page()
p1.insert_text(
    (50, 60),
    "KAKATIYA INSTITUTE OF TECHNOLOGY & SCIENCE, WARANGAL (KITSW)\n"
    "Department of Computer Science & Engineering (CSE)\n"
    "Academic Year: 2025-2026\n\n"
    "Faculty Directory:\n"
    "1. Prof. K. Ashoka Reddy - Principal & Senior Professor\n"
    "2. Dr. V. Shankar - Professor & Head of the Department (HoD), CSE\n"
    "3. Dr. P. Niranjan - Professor, Systems Architecture & AI\n"
    "4. Dr. S. Narasimha Reddy - Associate Professor, Cloud Computing\n"
    "5. Mrs. M. Preethi - Assistant Professor, Machine Learning & NLP\n\n"
    "Vision of the Department:\n"
    "To achieve excellence in providing educational opportunities and cutting-edge research in Computer Science and Engineering."
)

# Page 2: Grading System & Regulations
p2 = doc.new_page()
p2.insert_text(
    (50, 60),
    "KITSW Autonomous Regulations - B.Tech CSE Evaluation Scheme\n\n"
    "Grading Scale and Credit System:\n"
    "- Outstanding (O Grade): 90% and above, Grade Points = 10\n"
    "- Excellent (A+ Grade): 80% to 89%, Grade Points = 9\n"
    "- Very Good (A Grade): 70% to 79%, Grade Points = 8\n"
    "- Good (B+ Grade): 60% to 69%, Grade Points = 7\n"
    "- Above Average (B Grade): 50% to 59%, Grade Points = 6\n"
    "- Pass (C Grade): 40% to 49%, Grade Points = 5\n"
    "- Fail (F Grade): Below 40%, Grade Points = 0\n\n"
    "Attendance Requirements:\n"
    "A student must secure a minimum aggregate attendance of 75% in all registered courses to be eligible for end semester examinations.\n"
    "Condonation for medical reasons is permitted between 65% and 74% subject to approval by the Academic Council."
)

# Page 3: Placement Highlights
p3 = doc.new_page()
p3.insert_text(
    (50, 60),
    "KITSW Training & Placement Cell - Placement Statistics\n\n"
    "Campus Recruitment Highlights:\n"
    "- Highest CTC Offered: 31.0 LPA (Amazon Web Services)\n"
    "- Average CTC: 7.2 LPA across all CSE branches\n"
    "- Total Offers Received: Over 850 offers for eligible students\n"
    "- Top Recruiting Companies: Oracle, Cisco, Amazon, Cognizant, TCS Digital, Infosys, Tech Mahindra\n\n"
    "Internship Policy:\n"
    "All final year students must undertake a mandatory 6-month industry capstone project or internship during the VIII semester."
)

doc.save(pdf_path)
doc.close()
print(f"[SUCCESS] Created test PDF: {pdf_path} (3 pages)")

# 3. Upload to Render
print("\n[STEP 2] Uploading PDF to Production...")
t_up_start = time.time()
with open(pdf_path, "rb") as f:
    r_up = httpx.post(
        f'{BASE_URL}/api/documents/upload',
        headers=headers,
        files={'file': (pdf_path, f, 'application/pdf')},
        timeout=30.0
    )

t_up_dur = time.time() - t_up_start
print(f"Upload completed in {t_up_dur:.2f}s | HTTP {r_up.status_code}")
if r_up.status_code != 202:
    print("Upload error:", r_up.text)
    sys.exit(1)

doc_id = r_up.json()['id']
print(f"Document ID: {doc_id}")

# 4. Poll Status
print("\n[STEP 3] Monitoring Ingestion Progress in Production...")
poll_start = time.time()
ready = False
for attempt in range(25):
    time.sleep(1.0)
    r_check = httpx.get(f'{BASE_URL}/api/documents/{doc_id}', headers=headers, timeout=10.0)
    if r_check.status_code != 200:
        print(f"   Poll error HTTP {r_check.status_code}: {r_check.text}")
        continue
    data = r_check.json()
    status = data.get("status")
    elapsed = time.time() - poll_start
    print(f"   [T+{elapsed:.1f}s] Document status: {status} | pages={data.get('page_count')}")
    if status == "ready":
        ready = True
        print(f"\n>>> INGESTION SUCCESS in {elapsed:.1f}s! Document is READY for chat.")
        break
    elif status == "error":
        print(f"Ingestion failed: {data.get('error_message')}")
        break

if not ready:
    print("FAILED: Document did not become ready in time.")
    sys.exit(1)

# 5. Ask Questions in Document Chat
print("\n[STEP 4] Testing Document Q&A / Chat in Production...")
questions = [
    "Who is the Head of the Department (HoD) of CSE at KITSW?",
    "What is the minimum attendance percentage required for end semester examinations?",
    "What was the highest salary package (CTC) offered and which company offered it?"
]

with httpx.Client(base_url=BASE_URL, headers=headers, timeout=30.0) as client:
    for idx, q in enumerate(questions, 1):
        print(f"\n--- Question {idx}: '{q}' ---")
        t_q_start = time.time()
        r_chat = client.post(
            f"/api/chat/{doc_id}",
            json={"question": q, "strict_mode": False}
        )
        t_q_dur = time.time() - t_q_start
        print(f"Response received in {t_q_dur:.2f}s | HTTP {r_chat.status_code}")
        if r_chat.status_code == 200:
            chat_res = r_chat.json()
            print("Answer:", chat_res.get("answer"))
            print("Grounded:", chat_res.get("grounded"))
            citations = [f"[Page {s.get('page')}] {s.get('text', '')[:60]}..." for s in chat_res.get("sources", [])]
            print("Citations:", citations)
        else:
            print("Chat error:", r_chat.text)

print("\n[STEP 5] Verification Complete!")
