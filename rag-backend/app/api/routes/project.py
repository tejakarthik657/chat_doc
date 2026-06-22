import os
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from datetime import datetime
from bson import ObjectId
from typing import List

from app.core.security import get_current_user
from app.core.config import get_settings
from app.db.mongodb import projects_col, crawl_jobs_col, crawled_pages_col
from app.db.qdrant import delete_collection
from app.ingestion.crawler import crawl_website_task
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

    # 3. Trigger Crawl Background Task
    background_tasks.add_task(crawl_website_task, project_id, job_id, user_id)

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
    projects = await projects_col().find({"user_id": user_id}).to_list(length=100)
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
    # Verify project ownership
    project = await projects_col().find_one({"_id": project_id, "user_id": user_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    # 1. Delete Qdrant vector collection
    delete_collection(f"project_{project_id}")

    # 2. Clean up downloaded PDF files
    project_download_dir = os.path.join(settings.storage_dir, "uploads", user_id, "projects", project_id)
    if os.path.exists(project_download_dir):
        try:
            for file in os.listdir(project_download_dir):
                os.remove(os.path.join(project_download_dir, file))
            os.rmdir(project_download_dir)
        except Exception as e:
            print(f"[Cleanup] [WARNING] Failed to clear project directory {project_download_dir}: {e}")

    # 3. Delete MongoDB documents
    await projects_col().delete_one({"_id": project_id})
    await crawl_jobs_col().delete_many({"project_id": project_id})
    await crawled_pages_col().delete_many({"project_id": project_id})

    return status.HTTP_204_NO_CONTENT


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
            # Trigger indexing background task on FastAPI server context
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

    # Find latest paused job
    job = await crawl_jobs_col().find_one(
        {"project_id": project_id, "status": "paused"},
        sort=[("started_at", -1)]
    )
    if not job:
        raise HTTPException(status_code=400, detail="No paused crawl job found to resume.")

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

    # Trigger crawl background task
    background_tasks.add_task(crawl_website_task, project_id, job_id, user_id)

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
