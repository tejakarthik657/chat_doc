import os
import re
import httpx
import asyncio
import hashlib
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import trafilatura
from datetime import datetime
from bson import ObjectId
from typing import Set, List, Dict, Any

from app.db.mongodb import projects_col, crawl_jobs_col, crawled_pages_col
from app.core.config import get_settings

settings = get_settings()


def parse_sitemap_urls(xml_content: str) -> list[str]:
    """Parse URLs from <loc> tags in sitemap XML."""
    return re.findall(r"<loc>(.*?)</loc>", xml_content, re.IGNORECASE)


def get_domain(url: str) -> str:
    """Extract primary domain from URL (e.g. kitsw.ac.in)."""
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        return netloc[4:]
    return netloc


def is_same_domain(url: str, seed_domain: str) -> bool:
    """Verify if target URL is within the seed domain."""
    return get_domain(url) == seed_domain or get_domain(url).endswith("." + seed_domain)


def compute_hash(text: str) -> str:
    """Compute SHA-256 hash of a text string."""
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def is_navigation_text(text: str) -> bool:
    """Detect if extracted text is just navigation/link scaffolding with no real content."""
    if not text or len(text.strip()) < 50:
        return True
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return True
    link_pattern_hits = sum(1 for l in lines if re.match(r'^(click here|read more|learn more|view all|\s*\[.*?\]\s*)$', l.lower().strip()))
    if link_pattern_hits > len(lines) * 0.5:
        return True
    nav_ratio = sum(1 for l in lines if len(l.split()) <= 3) / len(lines)
    if nav_ratio > 0.6 and len(lines) < 20:
        return True
    return False


def is_noise_url(url: str) -> bool:
    """Check if the URL points to dynamic or noisy/junk pages that are irrelevant for indexing document content."""
    noise_patterns = [
        "/gallery", "/photo", "/album", "/image", "/video",
        "/news", "/press", "/feed", "/rss",
        "/event", "/calendar", "/announcement", "/notification",
        "/search", "/query", "wp-content", "wp-includes",
        "login", "logout", "signin", "signup"
    ]
    parsed = urlparse(url)
    path_lower = parsed.path.lower()
    query_lower = parsed.query.lower()
    return any(pattern in path_lower or pattern in query_lower for pattern in noise_patterns)


def get_url_priority(url: str, text: str = "") -> int:
    """
    Calculate crawling priority for a given URL (lower number is higher priority).
    """
    url_lower = url.lower()
    text_lower = text.lower()
    
    # Priority 1: Faculty directories, individual profile pages, department pages, placements, syllabus
    high_priority_keywords = [
        "faculty", "profile", "staff", "department", "syllabus", "placement",
        "cse", "ece", "eee", "it", "mech", "civil", "mba", "mca", "member", "teacher"
    ]
    if any(keyword in url_lower or keyword in text_lower for keyword in high_priority_keywords):
        return 1
        
    # Priority 3: Non-academic, heavy/noisy administrative, gallery, or dynamic sub-pages
    low_priority_keywords = [
        "gallery", "admission", "fee", "facility", "hostel", "sports", "library",
        "contact", "about", "feedback", "login", "logout"
    ]
    if any(keyword in url_lower or keyword in text_lower for keyword in low_priority_keywords):
        return 3
        
    # Priority 2: Standard pages
    return 2


async def crawl_website_task(project_id: str, job_id: str, user_id: str):
    """Background task to crawl a website recursively, saving pages/PDFs to MongoDB. Supports pause/resume and concurrent tasks."""
    project = await projects_col().find_one({"_id": project_id})
    if not project:
        print(f"[Crawler] Project {project_id} not found. Aborting.")
        return

    # Check if there is an existing job with saved state (Pause/Resume support)
    job = await crawl_jobs_col().find_one({"_id": job_id})
    if job and "to_visit" in job and "visited" in job:
        print(f"[Crawler] Resuming crawl for Project={project_id}, Job={job_id}")
        initial_to_visit = job["to_visit"]
        initial_visited = set(job["visited"])
        pages_indexed = job.get("pages_crawled", 0)
        docs_found = job.get("docs_found", 0)
        skip_sitemap = True
    else:
        seed_url = project["website_url"]
        initial_to_visit = [seed_url]
        initial_visited = set()
        pages_indexed = 0
        docs_found = 0
        skip_sitemap = False

    max_pages = project.get("max_pages", 50)
    seed_url = project["website_url"]
    seed_domain = get_domain(seed_url)

    use_dynamic_crawl = project.get("use_dynamic_crawl", False)
    sitemap_url = project.get("sitemap_url")
    login_url = project.get("login_url")
    login_username = project.get("login_username")
    login_password = project.get("login_password")

    print(f"[Crawler] Starting crawl for Project={project_id}, Seed={seed_url}, Limit={max_pages} pages")

    # Update job status to running
    await crawl_jobs_col().update_one(
        {"_id": job_id},
        {"$set": {"status": "running", "started_at": datetime.utcnow()}}
    )
    await projects_col().update_one(
        {"_id": project_id},
        {"$set": {"status": "crawling"}}
    )

    # Ensure local directory for downloaded PDFs exists
    project_download_dir = os.path.join(settings.storage_dir, "uploads", user_id, "projects", project_id)
    os.makedirs(project_download_dir, exist_ok=True)

    # 1. Sitemap Discovery (Skip if resuming)
    if not skip_sitemap:
        if not sitemap_url:
            sitemap_url = urljoin(seed_url, "/sitemap.xml")

        print(f"[Crawler] Checking sitemap at: {sitemap_url}")
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
                headers = {"User-Agent": "IDRSEnterpriseCrawler/1.0 (+https://github.com/idrs)"}
                sitemap_res = await client.get(sitemap_url, headers=headers)
                if sitemap_res.status_code == 200:
                    sitemap_urls = parse_sitemap_urls(sitemap_res.text)
                    print(f"[Crawler] Found {len(sitemap_urls)} URLs in sitemap.")
                    for s_url in sitemap_urls:
                        s_url_clean = s_url.strip()
                        if is_same_domain(s_url_clean, seed_domain):
                            parsed_s = urlparse(s_url_clean)
                            clean_s = parsed_s._replace(fragment="").geturl()
                            if clean_s not in initial_to_visit and not is_noise_url(clean_s):
                                initial_to_visit.append(clean_s)
                else:
                    print(f"[Crawler] Sitemap check returned status {sitemap_res.status_code}")
        except Exception as sitemap_err:
            print(f"[Crawler] [WARNING] Failed to parse sitemap: {sitemap_err}")

    # 2. Playwright Initialization
    playwright_available = False
    playwright_context = None
    playwright_instance = None
    browser = None
    cookies_dict = {}

    if use_dynamic_crawl:
        try:
            from playwright.async_api import async_playwright
            playwright_available = True
        except ImportError:
            print("[Crawler] [WARNING] Playwright is not installed. Falling back to HTTPX.")
            playwright_available = False

    if playwright_available and use_dynamic_crawl:
        try:
            playwright_instance = await async_playwright().start()
            browser = await playwright_instance.chromium.launch(headless=True)
            playwright_context = await browser.new_context(
                user_agent="IDRSEnterpriseCrawler/1.0 (+https://github.com/idrs)",
                viewport={"width": 1280, "height": 800}
            )
            async def block_assets(route):
                if route.request.resource_type in ["image", "stylesheet", "font", "media", "manifest", "other"]:
                    await route.abort()
                else:
                    await route.continue_()
            await playwright_context.route("**/*", block_assets)
            print("[Crawler] Playwright Chromium launched with asset-blocking optimizer enabled.")
        except Exception as pw_launch_err:
            print(f"[Crawler] [WARNING] Failed to launch Playwright: {pw_launch_err}. Falling back to HTTPX.")
            playwright_context = None
            if browser:
                await browser.close()
            if playwright_instance:
                await playwright_instance.stop()
            playwright_instance = None
            browser = None

    # 3. Portal Authentication Login
    if playwright_context and login_url and login_username and login_password:
        print(f"[Crawler] Attempting login at: {login_url}")
        try:
            login_page = await playwright_context.new_page()
            await login_page.goto(login_url, wait_until="networkidle", timeout=30000)
            
            # Find and fill username field
            username_selectors = [
                "input[type='text'][name*='user']",
                "input[type='text'][name*='email']",
                "input[type='email']",
                "input[name*='user']",
                "input[name*='email']",
                "input[id*='user']",
                "input[id*='email']",
                "input[placeholder*='User']",
                "input[placeholder*='Email']",
                "input[placeholder*='Login']",
                "input[type='text']"
            ]
            username_filled = False
            for selector in username_selectors:
                try:
                    el = await login_page.query_selector(selector)
                    if el and await el.is_visible():
                        await el.fill(login_username)
                        username_filled = True
                        break
                except Exception:
                    continue
            
            # Find and fill password field
            password_selectors = [
                "input[type='password']",
                "input[name*='pass']",
                "input[id*='pass']",
                "input[placeholder*='Password']",
                "input[placeholder*='pass']"
            ]
            password_filled = False
            for selector in password_selectors:
                try:
                    el = await login_page.query_selector(selector)
                    if el and await el.is_visible():
                        await el.fill(login_password)
                        password_filled = True
                        break
                except Exception:
                    continue
            
            if username_filled and password_filled:
                # Find and click login button
                submit_selectors = [
                    "button[type='submit']",
                    "input[type='submit']",
                    "button:has-text('Login')",
                    "button:has-text('Sign In')",
                    "button:has-text('Submit')",
                    "button",
                    "[class*='login']",
                    "[id*='login']",
                    "[class*='submit']",
                    "[id*='submit']"
                ]
                submit_clicked = False
                for selector in submit_selectors:
                    try:
                        el = await login_page.query_selector(selector)
                        if el and await el.is_visible():
                            await el.click()
                            submit_clicked = True
                            break
                    except Exception:
                        continue
                
                await login_page.wait_for_load_state("networkidle", timeout=15000)
                print("[Crawler] Completed login sequence. Capturing cookies.")
                cookies = await playwright_context.cookies()
                cookies_dict = {c['name']: c['value'] for c in cookies}
            else:
                print("[Crawler] [WARNING] Could not locate username or password fields.")
            
            await login_page.close()
        except Exception as login_err:
            print(f"[Crawler] [WARNING] Login attempt failed: {login_err}")

    # Set up asyncio Queue and enqueued set
    enqueued = set(initial_visited) | set(initial_to_visit)
    queue = asyncio.PriorityQueue()
    
    # Filter initial_to_visit to ensure we don't enqueue duplicates or already visited ones
    unique_initial_to_visit = [u for u in initial_to_visit if u not in initial_visited]
    seen_init = set()
    deduped_initial = []
    for u in unique_initial_to_visit:
        if u not in seen_init:
            seen_init.add(u)
            deduped_initial.append(u)
            
    for s_url in deduped_initial:
        queue.put_nowait((get_url_priority(s_url), s_url))

    visited = initial_visited
    
    # Concurrent stats tracking
    stats = {
        "pages_indexed": pages_indexed,
        "docs_found": docs_found,
        "urls_found": len(enqueued)
    }

    # Worker Task function
    async def worker(worker_id: int, client: httpx.AsyncClient):
        while True:
            # Check limits
            if len(visited) >= max_pages:
                break

            # Check if job was paused
            job_check = await crawl_jobs_col().find_one({"_id": job_id})
            if job_check and job_check.get("status") == "paused":
                break

            try:
                priority, current_url = await asyncio.wait_for(queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                if queue.empty():
                    break
                continue

            parsed_current = urlparse(current_url)
            clean_url = parsed_current._replace(fragment="").geturl()

            if clean_url in visited or len(visited) >= max_pages:
                queue.task_done()
                continue
            
            visited.add(clean_url)

            # Polite delay between requests per worker
            await asyncio.sleep(0.3)

            # Update DB with progress
            await crawl_jobs_col().update_one(
                {"_id": job_id},
                {"$set": {
                    "urls_found": stats["urls_found"],
                    "urls_processed": len(visited),
                    "pages_crawled": stats["pages_indexed"],
                    "docs_found": stats["docs_found"]
                }}
            )
            await projects_col().update_one(
                {"_id": project_id},
                {"$set": {
                    "pages_crawled": stats["pages_indexed"],
                    "docs_found": stats["docs_found"]
                }}
            )

            try:
                path_lower = parsed_current.path.lower()
                if path_lower.endswith(".pdf"):
                    print(f"[Crawler Worker {worker_id}] Downloading PDF: {clean_url}")
                    try:
                        response = await client.get(clean_url, cookies=cookies_dict, timeout=10.0)
                        if response.status_code == 200:
                            content = response.content
                            file_hash = compute_hash(str(content))
                            filename = os.path.basename(parsed_current.path)
                            if not filename:
                                filename = f"document_{hashlib.md5(clean_url.encode()).hexdigest()[:8]}.pdf"
                            
                            file_path = os.path.join(project_download_dir, f"{ObjectId()}_{filename}")
                            with open(file_path, "wb") as f:
                                f.write(content)

                            await crawled_pages_col().update_one(
                                {"project_id": project_id, "url": clean_url},
                                {"$set": {
                                    "title": filename,
                                    "file_path": file_path,
                                    "content_hash": file_hash,
                                    "page_type": "pdf",
                                    "status": "pending",
                                    "crawled_at": datetime.utcnow()
                                }},
                                upsert=True
                            )
                            stats["docs_found"] += 1
                            
                            # Extract links from PDF page to enqueue them
                            try:
                                import fitz
                                doc = fitz.open(file_path)
                                for page in doc:
                                    for link in page.get_links():
                                        if link.get("kind") == 2:  # fitz.LINK_URI
                                            uri = link.get("uri")
                                            if uri:
                                                full_link = urljoin(clean_url, uri)
                                                parsed_link = urlparse(full_link)
                                                if is_same_domain(full_link, seed_domain):
                                                    extension = os.path.splitext(parsed_link.path)[1].lower()
                                                    if extension not in [".jpg", ".jpeg", ".png", ".gif", ".svg", ".zip", ".tar", ".gz", ".mp4", ".mp3"]:
                                                        clean_link = parsed_link._replace(fragment="").geturl()
                                                        if not is_noise_url(clean_link):
                                                            if clean_link not in enqueued:
                                                                enqueued.add(clean_link)
                                                                queue.put_nowait((get_url_priority(clean_link), clean_link))
                                                                stats["urls_found"] += 1
                                doc.close()
                            except Exception as pdf_link_err:
                                print(f"[Crawler Worker {worker_id}] [WARNING] Failed to extract links from PDF {clean_url}: {pdf_link_err}")
                    except Exception as pdf_err:
                        print(f"[Crawler Worker {worker_id}] Failed to download PDF {clean_url}: {pdf_err}")
                    queue.task_done()
                    continue

                html_content = None
                extracted_preview = None
                
                # Fast-Path HTTPX
                try:
                    headers = {"User-Agent": "IDRSEnterpriseCrawler/1.0 (+https://github.com/idrs)"}
                    response = await client.get(clean_url, headers=headers, cookies=cookies_dict, timeout=8.0)
                    if response.status_code == 200:
                        content_type = response.headers.get("content-type", "").lower()
                        if "text/html" in content_type:
                            temp_html = response.text
                            
                            # Quick quality check on extracted text
                            extracted_preview = trafilatura.extract(temp_html, include_comments=False, include_tables=True)
                            if not extracted_preview or len(extracted_preview.strip()) < 200:
                                temp_soup = BeautifulSoup(temp_html, "html.parser")
                                for tag in temp_soup(["script", "style", "iframe", "footer", "header", "nav"]):
                                    tag.decompose()
                                extracted_preview = temp_soup.get_text(separator="\n")
                            
                            text_is_quality = bool(extracted_preview) and not is_navigation_text(extracted_preview)
                            
                            # Check for accordion/collapse patterns that hide content
                            has_dynamic_content = False
                            accordion_patterns = ["accordion", "collapse", "toggle", "aria-expanded", "tabpanel", "role=\"tab\"", "aria-controls"]
                            html_lower = temp_html.lower()
                            if any(pat in html_lower for pat in accordion_patterns):
                                has_dynamic_content = True
                            
                            # Decide: use HTTPX directly only if content is high quality and static
                            if text_is_quality and not has_dynamic_content:
                                html_content = temp_html
                                print(f"[Crawler Worker {worker_id}] Fast-Path HTTPX success for {clean_url} (chars={len(extracted_preview)})")
                            elif not playwright_context:
                                html_content = temp_html
                                print(f"[Crawler Worker {worker_id}] Fast-Path HTTPX forced (no Playwright) for {clean_url}")
                            else:
                                reason = "navigation text" if not text_is_quality else "dynamic content"
                                print(f"[Crawler Worker {worker_id}] Fast-Path bypassed for {clean_url} ({reason}). Need Playwright rendering.")
                        elif "text/" in content_type or "xml" in content_type:
                            html_content = response.text
                    else:
                        print(f"[Crawler Worker {worker_id}] HTTPX fast-path returned status {response.status_code} for {clean_url}")
                except Exception as httpx_err:
                    print(f"[Crawler Worker {worker_id}] HTTPX fast-path error for {clean_url}: {httpx_err}")

                # Slow-Path Playwright Fallback
                if not html_content and playwright_context:
                    print(f"[Crawler Worker {worker_id}] Running Slow-Path Playwright (aggressive) for {clean_url}")
                    try:
                        page = await playwright_context.new_page()
                        try:
                            await page.goto(clean_url, wait_until="networkidle", timeout=15000)
                        except Exception as goto_err:
                            print(f"[Crawler Worker {worker_id}] Playwright networkidle timeout, using domcontentloaded: {goto_err}")
                            try:
                                await page.goto(clean_url, wait_until="domcontentloaded", timeout=10000)
                            except Exception:
                                pass
                        
                        # Expand ALL dynamic content aggressively
                        expand_selectors = [
                            "[aria-expanded='false']",
                            "[class*='accordion']",
                            "[class*='collapse']",
                            "[class*='expand']",
                            "[class*='toggle']",
                            "[class*='dropdown']",
                            "button:has-text('Read More')",
                            "button:has-text('Expand')",
                            "button:has-text('View More')",
                            "button:has-text('Show More')",
                            "[data-expanded='false']",
                            "[data-toggle='collapse']",
                            "details:not([open])",
                            ".nav-tabs [data-toggle='tab']",
                        ]
                        for selector in expand_selectors:
                            try:
                                el_list = await page.query_selector_all(selector)
                                for el in el_list:
                                    tag_name = await el.evaluate("e => e.tagName.toLowerCase()")
                                    if tag_name == "a":
                                        continue
                                    if await el.is_visible():
                                        await el.click()
                                        await asyncio.sleep(0.05)
                            except Exception:
                                pass
                        
                        # Wait for any lazy-loaded content
                        await asyncio.sleep(0.5)
                        
                        # Scroll to trigger lazy loading
                        try:
                            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                            await asyncio.sleep(0.3)
                            await page.evaluate("window.scrollTo(0, 0)")
                        except Exception:
                            pass
                        
                        html_content = await page.content()
                        await page.close()
                    except Exception as page_pw_err:
                        print(f"[Crawler Worker {worker_id}] Playwright error for {clean_url}: {page_pw_err}")
                        html_content = None

                if html_content:
                    soup = BeautifulSoup(html_content, "html.parser")
                    title = clean_url
                    if soup.title and soup.title.string:
                        title = soup.title.string.strip()

                    extracted_text = trafilatura.extract(html_content, include_comments=False, include_tables=True)
                    if not extracted_text or len(extracted_text.strip()) < 200:
                        cleaner_soup = BeautifulSoup(html_content, "html.parser")
                        for tag in cleaner_soup(["script", "style", "iframe", "footer", "header", "nav"]):
                            tag.decompose()
                        extracted_text = cleaner_soup.get_text(separator="\n")
                    
                    lines = (line.strip() for line in extracted_text.splitlines())
                    chunks = (phrase for line in lines for phrase in line.split("  "))
                    clean_text = "\n".join(chunk for chunk in chunks if chunk)

                    # Disabling secondary re-extraction loop for production efficiency. 
                    # Playwright already expands all accordion selectors in the primary slow-path loop.
                    pass

                    if clean_text:
                        content_hash = compute_hash(clean_text)
                        existing_page = await crawled_pages_col().find_one({"project_id": project_id, "url": clean_url})
                        is_changed = True
                        if existing_page and existing_page.get("content_hash") == content_hash:
                            is_changed = False
                            print(f"[Crawler Worker {worker_id}] Skipping unchanged page: {clean_url}")
                        
                        if is_changed:
                            await crawled_pages_col().update_one(
                                {"project_id": project_id, "url": clean_url},
                                {"$set": {
                                    "title": title,
                                    "text_content": clean_text,
                                    "content_hash": content_hash,
                                    "page_type": "html",
                                    "status": "pending",
                                    "crawled_at": datetime.utcnow()
                                }},
                                upsert=True
                            )
                            stats["pages_indexed"] += 1

                        for link in soup.find_all("a", href=True):
                            href = link["href"]
                            full_link = urljoin(clean_url, href)
                            parsed_link = urlparse(full_link)
                            if is_same_domain(full_link, seed_domain):
                                extension = os.path.splitext(parsed_link.path)[1].lower()
                                if extension not in [".jpg", ".jpeg", ".png", ".gif", ".svg", ".zip", ".tar", ".gz", ".mp4", ".mp3"]:
                                    clean_link = parsed_link._replace(fragment="").geturl()
                                    if not is_noise_url(clean_link):
                                        if clean_link not in enqueued:
                                            enqueued.add(clean_link)
                                            queue.put_nowait((get_url_priority(clean_link, link.get_text() or ""), clean_link))
                                            stats["urls_found"] += 1
            except Exception as e:
                print(f"[Crawler Worker {worker_id}] [ERROR] Failed to fetch {clean_url}: {e}")
            finally:
                queue.task_done()

    # Determine worker pool count dynamically based on engine mode
    is_js_crawl = playwright_context and use_dynamic_crawl
    num_workers = 5 if is_js_crawl else 12
    print(f"[Crawler] Spawning {num_workers} parallel workers (Mode: {'Playwright JS' if is_js_crawl else 'Standard HTTP'}).")

    limits = httpx.Limits(max_keepalive_connections=num_workers, max_connections=num_workers * 3)
    try:
        async with httpx.AsyncClient(limits=limits, follow_redirects=True, timeout=10.0) as client:
            workers = [asyncio.create_task(worker(i, client)) for i in range(num_workers)]
            await asyncio.gather(*workers)
    finally:
        if browser:
            try:
                await browser.close()
            except Exception:
                pass
        if playwright_instance:
            try:
                await playwright_instance.stop()
            except Exception:
                pass

    # Check final job status (whether it was paused or finished)
    current_job = await crawl_jobs_col().find_one({"_id": job_id})
    if current_job and current_job.get("status") == "paused":
        # Capture remaining queue items to resume from later
        remaining_to_visit = []
        while not queue.empty():
            try:
                priority, url = queue.get_nowait()
                remaining_to_visit.append(url)
                queue.task_done()
            except Exception:
                break

        await crawl_jobs_col().update_one(
            {"_id": job_id},
            {"$set": {
                "to_visit": remaining_to_visit,
                "visited": list(visited),
                "pages_crawled": stats["pages_indexed"],
                "docs_found": stats["docs_found"]
            }}
        )
        await projects_col().update_one(
            {"_id": project_id},
            {"$set": {
                "status": "paused",
                "pages_crawled": stats["pages_indexed"],
                "docs_found": stats["docs_found"]
            }}
        )
        print(f"[Crawler] Crawl Job {job_id} paused. Stored {len(remaining_to_visit)} remaining URLs in queue.")
        return # Terminate task without proceeding to indexing pipeline

    print(f"[Crawler] Finished crawling. Ingested/Updated {stats['pages_indexed']} pages and {stats['docs_found']} PDFs.")

    # Update crawl job in database
    await crawl_jobs_col().update_one(
        {"_id": job_id},
        {"$set": {
            "status": "completed",
            "urls_processed": len(visited),
            "completed_at": datetime.utcnow()
        }}
    )
    
    # Update project status
    await projects_col().update_one(
        {"_id": project_id},
        {"$set": {
            "status": "indexing",
            "pages_crawled": stats["pages_indexed"],
            "docs_found": stats["docs_found"]
        }}
    )

    # Trigger indexing of the crawled pages
    from app.ingestion.pipeline import process_project_crawled_data
    await process_project_crawled_data(project_id, user_id)
