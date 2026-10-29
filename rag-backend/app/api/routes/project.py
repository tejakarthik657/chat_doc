import os
import asyncio
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from datetime import datetime
from bson import ObjectId
from typing import List
from pydantic import BaseModel

from app.core.security import get_current_user
from app.core.config import get_settings
from app.db.mongodb import projects_col, crawl_jobs_col, crawled_pages_col
from app.db.qdrant import delete_collection
from app.core.storage_cloudinary import delete_pdf_from_cloudinary
from app.tasks import crawl_website_task as crawl_task
from app.models.schemas import ProjectCreate, ProjectOut, ProjectList, CrawlJobOut

settings = get_settings()
router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("/create", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user)
):
    # Normalize URL
    url = project_in.website_url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        raise HTTPException(
            status_code=400,
            detail="Invalid URL. Website URL must start with http:// or https://"
        )

    # 1. Create Project in MongoDB
    project_id = str(ObjectId())
    now = datetime.utcnow()
    project_doc = {
        "_id": project_id,
        "name": project_in.name,
        "website_url": url,
        "max_pages": project_in.max_pages,
        "use_dynamic_crawl": project_in.use_dynamic_crawl,
        "sitemap_url": project_in.sitemap_url,
        "login_url": project_in.login_url,
        "login_username": project_in.login_username,
        "login_password": project_in.login_password,
        "user_id": user_id,
        "created_at": now,
        "status": "crawling",
        "pages_crawled": 0,
        "docs_found": 0
    }
    await projects_col().insert_one(project_doc)

    # 2. Initialize CrawlJob in MongoDB
    job_id = str(ObjectId())
    job_doc = {
        "_id": job_id,
        "project_id": project_id,
        "status": "pending",
        "urls_found": 0,
        "urls_processed": 0,
        "error_message": None,
        "started_at": None,
        "completed_at": None
    }
    await crawl_jobs_col().insert_one(job_doc)

    # 3. Trigger Crawl Task (Upstash Redis Queue, Celery, or FastAPI BackgroundTasks)
    import json
    from app.db.upstash import get_upstash_client
    upstash = get_upstash_client()
    enqueued_cloud = False

    if upstash.enabled:
        try:
            await upstash.push_event("nexus_crawl_queue", json.dumps({
                "project_id": project_id,
                "job_id": job_id,
                "user_id": user_id
            }))
            print("[Upstash Queue] Enqueued crawl task to Upstash Redis Cloud.")
            enqueued_cloud = True
        except Exception as q_err:
            print(f"[Upstash Queue Warning] {q_err}")

    from app.ingestion.crawler import crawl_website_task as run_crawler
    if background_tasks is not None:
        background_tasks.add_task(run_crawler, project_id, job_id, user_id)
    else:
        asyncio.create_task(run_crawler(project_id, job_id, user_id))

    return ProjectOut(
        id=project_id,
        name=project_in.name,
        website_url=url,
        created_at=now,
        status="crawling",
        pages_crawled=0,
        docs_found=0,
        use_dynamic_crawl=project_in.use_dynamic_crawl,
        sitemap_url=project_in.sitemap_url,
        login_url=project_in.login_url,
        login_username=project_in.login_username,
        login_password=project_in.login_password
    )


@router.get("/", response_model=ProjectList)
async def list_projects(user_id: str = Depends(get_current_user)):
    projects = await projects_col().find(
        {"user_id": user_id},
        {
            "_id": 1, "name": 1, "website_url": 1, "created_at": 1,
            "status": 1, "pages_crawled": 1, "docs_found": 1,
            "use_dynamic_crawl": 1, "sitemap_url": 1, "login_url": 1,
            "login_username": 1, "login_password": 1
        }
    ).to_list(length=100)
    return ProjectList(
        projects=[
            ProjectOut(
                id=p["_id"],
                name=p["name"],
                website_url=p["website_url"],
                created_at=p["created_at"],
                status=p["status"],
                pages_crawled=p.get("pages_crawled", 0),
                docs_found=p.get("docs_found", 0),
                use_dynamic_crawl=p.get("use_dynamic_crawl", False),
                sitemap_url=p.get("sitemap_url"),
                login_url=p.get("login_url"),
                login_username=p.get("login_username"),
                login_password=p.get("login_password")
            )
            for p in projects
        ]
    )


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: str, user_id: str = Depends(get_current_user)):
    project = await projects_col().find_one({"_id": project_id, "user_id": user_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    
    return ProjectOut(
        id=project["_id"],
        name=project["name"],
        website_url=project["website_url"],
        created_at=project["created_at"],
        status=project["status"],
        pages_crawled=project.get("pages_crawled", 0),
        docs_found=project.get("docs_found", 0),
        use_dynamic_crawl=project.get("use_dynamic_crawl", False),
        sitemap_url=project.get("sitemap_url"),
        login_url=project.get("login_url"),
        login_username=project.get("login_username"),
        login_password=project.get("login_password")
    )


@router.get("/{project_id}/crawl-status", response_model=CrawlJobOut)
async def get_crawl_status(project_id: str, user_id: str = Depends(get_current_user)):
    # Verify project ownership
    project = await projects_col().find_one({"_id": project_id, "user_id": user_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    # Get latest crawl job
    job = await crawl_jobs_col().find_one(
        {"project_id": project_id},
        sort=[("started_at", -1)]
    )
    if not job:
        raise HTTPException(status_code=404, detail="No crawl jobs found for this project.")

    return CrawlJobOut(
        id=str(job["_id"]),
        project_id=str(job["project_id"]),
        status=job["status"],
        urls_found=job.get("urls_found", 0),
        urls_processed=job.get("urls_processed", 0),
        pages_crawled=job.get("pages_crawled", 0),
        docs_found=job.get("docs_found", 0),
        error_message=job.get("error_message"),
        started_at=job.get("started_at"),
        completed_at=job.get("completed_at")
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: str, user_id: str = Depends(get_current_user)):
    from fastapi import Response
    from app.db.mongodb import chunks_col

    # Verify project ownership
    project = await projects_col().find_one({"_id": project_id, "user_id": user_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    # 1. Delete Qdrant vector collection
    try:
        delete_collection(f"project_{project_id}")
    except Exception as e:
        print(f"[Qdrant Cleanup] [WARNING] Failed to drop collection: {e}")

    # 2. Clean up durable crawled PDFs and legacy local files
    crawled_pdfs = await crawled_pages_col().find(
        {"project_id": project_id, "page_type": "pdf"},
        {"storage_public_id": 1, "file_path": 1},
    ).to_list(length=1000)
    for pdf in crawled_pdfs:
        delete_pdf_from_cloudinary(pdf.get("storage_public_id", ""))
        legacy_path = pdf.get("file_path", "")
        if legacy_path and os.path.exists(legacy_path):
            try:
                os.remove(legacy_path)
            except OSError as cleanup_error:
                print(f"[Cleanup] [WARNING] Failed to remove legacy PDF {legacy_path}: {cleanup_error}")

    project_download_dir = os.path.join(settings.storage_dir, "uploads", user_id, "projects", project_id)
    if os.path.exists(project_download_dir):
        try:
            for file in os.listdir(project_download_dir):
                os.remove(os.path.join(project_download_dir, file))
            os.rmdir(project_download_dir)
        except Exception as e:
            print(f"[Cleanup] [WARNING] Failed to clear project directory {project_download_dir}: {e}")

    # 3. Delete MongoDB documents & chunks
    await projects_col().delete_one({"_id": project_id})
    await crawl_jobs_col().delete_many({"project_id": project_id})
    await crawled_pages_col().delete_many({"project_id": project_id})
    await chunks_col().delete_many({"doc_id": project_id})
    await chunks_col().delete_many({"project_id": project_id})

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{project_id}/inventory")
async def get_project_inventory(project_id: str, user_id: str = Depends(get_current_user)):
    # Verify project ownership
    project = await projects_col().find_one({"_id": project_id, "user_id": user_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    pages = await crawled_pages_col().find(
        {"project_id": project_id},
        {"url": 1, "title": 1, "page_type": 1}
    ).to_list(length=1000)

    web_pages = [
        {"url": p["url"], "title": p.get("title", p["url"])}
        for p in pages
        if p.get("page_type") == "html"
    ]
    
    pdfs = [
        {"url": p["url"], "title": p.get("title", p["url"])}
        for p in pages
        if p.get("page_type") == "pdf"
    ]

    return {"web_pages": web_pages, "pdfs": pdfs}


@router.post("/{project_id}/re-ingest")
async def re_ingest_project(
    project_id: str,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user)
):
    """
    Re-index all crawled pages with the current pipeline.
    Drops the Qdrant collection and rebuilds vectors (parent_id, contextual_text, etc.).
    """
    project = await projects_col().find_one({"_id": project_id, "user_id": user_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    if project.get("status") in ("crawling", "indexing"):
        raise HTTPException(
            status_code=400,
            detail="Project is still crawling or indexing. Pause or wait before re-ingesting.",
        )

    page_count = await crawled_pages_col().count_documents({"project_id": project_id})
    if page_count == 0:
        raise HTTPException(status_code=400, detail="No crawled pages to re-ingest.")

    await crawled_pages_col().update_many(
        {"project_id": project_id},
        {"$set": {"status": "pending"}, "$unset": {"error_message": ""}},
    )
    await projects_col().update_one(
        {"_id": project_id},
        {"$set": {"status": "indexing"}},
    )

    from app.celery_app import is_celery_worker_active
    if is_celery_worker_active():
        try:
            from app.tasks import process_project_crawled_data_task as index_task
            index_task.delay(project_id, user_id, True)
            print("[Celery] Successfully enqueued re-indexing task.")
        except Exception as celery_err:
            print(f"[Celery] Connection failed, falling back to FastAPI BackgroundTasks: {celery_err}")
            from app.ingestion.pipeline import process_project_crawled_data
            background_tasks.add_task(process_project_crawled_data, project_id, user_id, True)
    else:
        print("[Celery] No active workers detected, falling back to FastAPI BackgroundTasks.")
        from app.ingestion.pipeline import process_project_crawled_data
        background_tasks.add_task(process_project_crawled_data, project_id, user_id, True)

    return {
        "status": "indexing",
        "message": f"Re-ingest started for {page_count} pages.",
        "pages_queued": page_count,
    }


@router.post("/{project_id}/pause")
async def pause_project_crawl(project_id: str, user_id: str = Depends(get_current_user)):
    # Verify project ownership
    project = await projects_col().find_one({"_id": project_id, "user_id": user_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    # Update status to paused
    await projects_col().update_one(
        {"_id": project_id},
        {"$set": {"status": "paused"}}
    )
    # Get latest running crawl job and mark it as paused
    await crawl_jobs_col().update_one(
        {"project_id": project_id, "status": "running"},
        {"$set": {"status": "paused"}}
    )
    return {"status": "paused"}


@router.post("/{project_id}/resume", response_model=CrawlJobOut)
async def resume_project_crawl(
    project_id: str,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user)
):
    # Verify project ownership
    project = await projects_col().find_one({"_id": project_id, "user_id": user_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    # If the project status is stuck in "indexing", allow resuming indexing directly
    if project.get("status") == "indexing":
        # Find latest completed or running job
        job = await crawl_jobs_col().find_one(
            {"project_id": project_id},
            sort=[("started_at", -1)]
        )
        if job:
            job_id = job["_id"]
            # Trigger indexing Celery task
            from app.celery_app import is_celery_worker_active
            if is_celery_worker_active():
                try:
                    from app.tasks import process_project_crawled_data_task as index_task
                    index_task.delay(project_id, user_id)
                    print("[Celery] Successfully enqueued resume indexing task.")
                except Exception as celery_err:
                    print(f"[Celery] Connection failed, falling back to FastAPI BackgroundTasks: {celery_err}")
                    from app.ingestion.pipeline import process_project_crawled_data
                    background_tasks.add_task(process_project_crawled_data, project_id, user_id)
            else:
                print("[Celery] No active workers detected, falling back to FastAPI BackgroundTasks.")
                from app.ingestion.pipeline import process_project_crawled_data
                background_tasks.add_task(process_project_crawled_data, project_id, user_id)
            return CrawlJobOut(
                id=str(job_id),
                project_id=str(project_id),
                status="running",
                urls_found=job.get("urls_found", 0),
                urls_processed=job.get("urls_processed", 0),
                pages_crawled=job.get("pages_crawled", 0),
                docs_found=job.get("docs_found", 0),
                error_message=job.get("error_message"),
                started_at=job.get("started_at"),
                completed_at=job.get("completed_at")
            )

    # Find latest paused, pending, or failed job to resume
    job = await crawl_jobs_col().find_one(
        {"project_id": project_id, "status": {"$in": ["paused", "pending", "failed"]}},
        sort=[("started_at", -1)]
    )
    if not job:
        raise HTTPException(status_code=400, detail="No paused, pending, or failed crawl job found to resume.")

    job_id = job["_id"]
    # Update job and project status back to running/crawling
    await crawl_jobs_col().update_one(
        {"_id": job_id},
        {"$set": {"status": "running"}}
    )
    await projects_col().update_one(
        {"_id": project_id},
        {"$set": {"status": "crawling"}}
    )

    # Trigger crawl background task via Celery (FastAPI BackgroundTasks fallback if Redis is down or worker offline)
    from app.celery_app import is_celery_worker_active
    if is_celery_worker_active():
        try:
            crawl_task.delay(project_id, job_id, user_id)
            print("[Celery] Successfully enqueued resume crawl task.")
        except Exception as celery_err:
            print(f"[Celery] Connection failed, falling back to FastAPI BackgroundTasks: {celery_err}")
            from app.ingestion.crawler import crawl_website_task as run_crawler
            background_tasks.add_task(run_crawler, project_id, job_id, user_id)
    else:
        print("[Celery] No active workers detected, falling back to FastAPI BackgroundTasks.")
        from app.ingestion.crawler import crawl_website_task as run_crawler
        background_tasks.add_task(run_crawler, project_id, job_id, user_id)

    return CrawlJobOut(
        id=str(job_id),
        project_id=str(project_id),
        status="running",
        urls_found=job.get("urls_found", 0),
        urls_processed=job.get("urls_processed", 0),
        pages_crawled=job.get("pages_crawled", 0),
        docs_found=job.get("docs_found", 0),
        error_message=job.get("error_message"),
        started_at=job.get("started_at"),
        completed_at=job.get("completed_at")
    )


_GRAPH_CACHE: dict[str, tuple[float, dict]] = {}
GRAPH_CACHE_TTL = 600  # 10 minutes

@router.get("/{project_id}/graph")
async def get_project_graph(project_id: str, user_id: str = Depends(get_current_user)):
    from app.db.mongodb import chunks_col, crawled_pages_col
    import asyncio

    # 0. Check in-memory fast cache first
    now_ts = datetime.utcnow().timestamp()
    if project_id in _GRAPH_CACHE:
        cached_ts, cached_data = _GRAPH_CACHE[project_id]
        if now_ts - cached_ts < GRAPH_CACHE_TTL:
            return cached_data

    project = await projects_col().find_one({"_id": project_id, "user_id": user_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    p_name = project.get("name", "Project")

    # 1. Check if cached in MongoDB project record
    if project.get("cached_graph") and isinstance(project["cached_graph"], dict) and len(project["cached_graph"].get("nodes", [])) > 1:
        _GRAPH_CACHE[project_id] = (now_ts, project["cached_graph"])
        return project["cached_graph"]

    # 2. Try Neo4j if driver is connected
    try:
        from app.db.neo4j import get_neo4j_driver
        driver = get_neo4j_driver()
        if driver is not None:
            nodes = []
            links = []
            node_ids = set()

            with driver.session() as session:
                result = session.run(
                    "MATCH (p:Project {id: $project_id})-[r:HAS_ENTITY]->(e:Entity) "
                    "RETURN p.name as p_name, e.name as e_name, e.type as e_type",
                    {"project_id": project_id}
                )
                nodes.append({"id": p_name, "type": "Project", "group": 1})
                node_ids.add(p_name)

                for record in result:
                    e_name = record["e_name"]
                    e_type = record["e_type"]
                    if e_name not in node_ids:
                        nodes.append({"id": e_name, "type": e_type, "group": 2})
                        node_ids.add(e_name)
                    links.append({"source": p_name, "target": e_name, "type": "HAS_ENTITY", "value": 1})

            if len(nodes) > 1:
                graph_res = {"nodes": nodes, "links": links}
                _GRAPH_CACHE[project_id] = (now_ts, graph_res)
                return graph_res
    except Exception as e:
        print(f"[Neo4j] Graph query skipped or notice: {e}")

    # 3. High-Speed Hierarchical Knowledge Graph Generator (pure Python & MongoDB - runs in <15ms)
    try:
        pages = await crawled_pages_col().find(
            {"project_id": project_id},
            {"title": 1, "url": 1, "page_type": 1, "department": 1, "document_type": 1}
        ).limit(100).to_list(length=100)

        nodes = [{"id": p_name, "type": "Project", "group": 1}]
        links = []
        seen_nodes = {p_name}

        # Categories grouping
        category_map = {
            "Alumni": {"group": 2},
            "Academics & Syllabus": {"group": 2},
            "Examinations": {"group": 2},
            "Donations & Funds": {"group": 2},
            "Reports & Documents": {"group": 2},
            "Portal & Admissions": {"group": 2},
        }

        # Add top-level category nodes
        for cat_name, cat_meta in category_map.items():
            if cat_name not in seen_nodes:
                seen_nodes.add(cat_name)
                nodes.append({"id": cat_name, "type": "Category", "group": cat_meta["group"]})
                links.append({"source": p_name, "target": cat_name, "type": "HAS_CATEGORY", "value": 2})

        # Add page nodes under relevant category
        for p in pages:
            raw_title = p.get("title") or p.get("url") or "Page"
            clean_title = raw_title.split("|")[0].split("-")[0].strip()[:30]
            if not clean_title or clean_title in seen_nodes:
                continue

            url_lower = p.get("url", "").lower()
            target_cat = "Portal & Admissions"
            if "alumni" in url_lower:
                target_cat = "Alumni"
            elif "academic" in url_lower or "syllabus" in url_lower or "curriculum" in url_lower:
                target_cat = "Academics & Syllabus"
            elif "exam" in url_lower:
                target_cat = "Examinations"
            elif "fund" in url_lower or "donat" in url_lower:
                target_cat = "Donations & Funds"
            elif p.get("page_type") == "pdf" or ".pdf" in url_lower or "report" in url_lower:
                target_cat = "Reports & Documents"

            seen_nodes.add(clean_title)
            nodes.append({"id": clean_title, "type": "Page", "group": 3})
            links.append({"source": target_cat, "target": clean_title, "type": "CONTAINS", "value": 1})

        # Also pull top extracted named entities from chunks if available
        chunks = await chunks_col().find({"doc_id": project_id}, {"text": 1, "department": 1, "document_type": 1}).limit(20).to_list(length=20)
        entity_keywords = ["KITSWAA", "NAAC", "AICTE", "Autonomous", "Governing Body", "Controller of Examinations", "Kakatiya University", "B.Tech", "M.Tech", "MBA"]
        for kw in entity_keywords:
            if kw not in seen_nodes and any(kw.lower() in c.get("text", "").lower() for c in chunks):
                seen_nodes.add(kw)
                nodes.append({"id": kw, "type": "Entity", "group": 4})
                links.append({"source": p_name, "target": kw, "type": "HAS_ENTITY", "value": 1})

        graph_data = {"nodes": nodes, "links": links}
        _GRAPH_CACHE[project_id] = (now_ts, graph_data)

        # Persist to project doc so it's instantly available on reload
        try:
            await projects_col().update_one({"_id": project_id}, {"$set": {"cached_graph": graph_data}})
        except Exception as cache_save_err:
            print(f"[Graph Cache Notice] {cache_save_err}")

        return graph_data
    except Exception as err:
        print(f"[Graph Generator Error] {err}")
        return {
            "nodes": [{"id": p_name, "type": "Project", "group": 1}],
            "links": []
        }


# ── Feature 4: Causal "What-If?" Simulation on Knowledge Graph ───────────────

class GraphSimulateRequest(BaseModel):
    perturbed_node: str
    scenario: str


@router.post("/{project_id}/graph/simulate")
async def simulate_graph_scenario(
    project_id: str,
    body: GraphSimulateRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Feature 4: Causal What-If Simulation.
    Simulates perturbation ripples across the project's knowledge graph dependencies.
    """
    import asyncio
    import json
    import re
    from app.core.llm_groq import _get_or_init_groq_client

    project = await projects_col().find_one({"_id": project_id, "user_id": user_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    # Retrieve current graph
    cached_graph = project.get("cached_graph") or {}
    nodes = [n.get("id") for n in cached_graph.get("nodes", [])]
    links = cached_graph.get("links", [])

    # Identify depth 1 and depth 2 neighbors
    target = body.perturbed_node
    depth_1 = set()
    for l in links:
        src = l.get("source") if isinstance(l.get("source"), str) else l.get("source", {}).get("id")
        tgt = l.get("target") if isinstance(l.get("target"), str) else l.get("target", {}).get("id")
        if src == target and tgt:
            depth_1.add(tgt)
        elif tgt == target and src:
            depth_1.add(src)

    depth_2 = set()
    for l in links:
        src = l.get("source") if isinstance(l.get("source"), str) else l.get("source", {}).get("id")
        tgt = l.get("target") if isinstance(l.get("target"), str) else l.get("target", {}).get("id")
        if src in depth_1 and tgt and tgt != target and tgt not in depth_1:
            depth_2.add(tgt)
        elif tgt in depth_1 and src and src != target and src not in depth_1:
            depth_2.add(src)

    connected_context = f"Root Perturbed Entity: {target}\nDirect Connected Neighbors (Depth 1): {list(depth_1)}\nSecondary Cascading Neighbors (Depth 2): {list(depth_2)}"

    client = _get_or_init_groq_client()
    sim_prompt = f"""You are a Systems & Causal Knowledge Graph Risk Engine.
Perform a dynamic failure-cascade simulation for the following scenario:

Project: {project.get('name', 'System')}
Perturbed Entity: {target}
Scenario Condition: {body.scenario}
Topological Graph Neighborhood:
{connected_context}

Predict the downstream impact ripples across the graph.
Respond STRICTLY with a valid JSON object matching this schema:
{{
  "perturbed_node": "{target}",
  "scenario": "{body.scenario}",
  "impacted_nodes": {{
    "{target}": {{
      "risk_level": "CRITICAL",
      "ripple_depth": 0,
      "failure_probability": 0.95,
      "impact": "Point of origin perturbation."
    }}
  }},
  "cascade_chain": [
    {{
      "source": "{target}",
      "target": "Neighbor Name",
      "impact": "Causal consequence"
    }}
  ],
  "executive_summary": "Two sentence executive summary of systemic resilience and vulnerability.",
  "mitigations": [
    "Actionable mitigation 1",
    "Actionable mitigation 2"
  ]
}}
Ensure every node in Direct Connected Neighbors has an entry in impacted_nodes with risk_level ("CRITICAL", "HIGH", "MEDIUM", or "LOW").
"""

    try:
        raw = await asyncio.to_thread(
            client.chat_completion,
            messages=[
                {"role": "system", "content": "You are a causal graph simulation engine. Respond only with JSON."},
                {"role": "user", "content": sim_prompt}
            ],
            model="qwen/qwen3.8-27b",
            temperature=0.3,
            max_tokens=850
        )
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            return data
    except Exception as e:
        print(f"[Graph Simulator Error] {e}")

    # Fallback simulation if LLM is unavailable
    impacted = {
        target: {
            "risk_level": "CRITICAL",
            "ripple_depth": 0,
            "failure_probability": 0.95,
            "impact": f"Directly affected by scenario: {body.scenario}"
        }
    }
    chain = []
    for d1 in list(depth_1)[:5]:
        impacted[d1] = {
            "risk_level": "HIGH",
            "ripple_depth": 1,
            "failure_probability": 0.70,
            "impact": f"Cascading dependency risk from {target}."
        }
        chain.append({"source": target, "target": d1, "impact": "Secondary dependency stress"})

    for d2 in list(depth_2)[:3]:
        impacted[d2] = {
            "risk_level": "MEDIUM",
            "ripple_depth": 2,
            "failure_probability": 0.40,
            "impact": "Indirect peripheral exposure."
        }
        chain.append({"source": list(depth_1)[0] if depth_1 else target, "target": d2, "impact": "Indirect buffer depletion"})

    return {
        "perturbed_node": target,
        "scenario": body.scenario,
        "impacted_nodes": impacted,
        "cascade_chain": chain,
        "executive_summary": f"Perturbation to {target} triggers immediate secondary strain across {len(depth_1)} connected nodes.",
        "mitigations": [
            f"Introduce redundant fallback paths around {target}.",
            "Isolate non-critical downstream dependencies to prevent systemic propagation."
        ]
    }
