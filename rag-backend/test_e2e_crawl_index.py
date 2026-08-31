import os
import sys

# Prevent OpenMP conflicts/deadlocks on load
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import asyncio
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Add project path to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.ingestion.crawler import crawl_website_task
from app.ingestion.pipeline import process_project_crawled_data
from app.rag.engine import answer_project_question
from app.db.mongodb import get_client, projects_col, crawl_jobs_col, crawled_pages_col

async def run_e2e_test():
    print("--- STARTING E2E CRAWL AND INDEX TEST WITH PLAYWRIGHT ---")
    load_dotenv()
    
    # 1. Connect to MongoDB
    mongo_url = os.getenv("MONGODB_URL")
    if not mongo_url:
        print("[ERROR] MONGODB_URL not found. Aborting.")
        return
        
    client = AsyncIOMotorClient(mongo_url)
    db_name = os.getenv("DB_NAME", "rag_db")
    db = client[db_name]
    
    # Get a dummy/test user
    user = await db.users.find_one()
    if not user:
        user_id = str(ObjectId())
        await db.users.insert_one({
            "_id": user_id,
            "email": "e2e_crawler_test@example.com",
            "hashed_password": "dummy_password",
            "storage_used_mb": 0.0,
            "plan": "free"
        })
        print(f"Created dummy user: e2e_crawler_test@example.com (ID: {user_id})")
    else:
        user_id = user["_id"]
        print(f"Using existing user: {user.get('email')} (ID: {user_id})")
        
    # 2. Create Project
    project_id = str(ObjectId())
    job_id = str(ObjectId())
    
    print(f"Creating project ID: {project_id}")
    project_doc = {
        "_id": project_id,
        "name": "E2E Wiki Test PW",
        "website_url": "https://en.wikipedia.org/wiki/Digital_health",
        "max_pages": 1,
        "use_dynamic_crawl": True, # Enable Playwright!
        "user_id": user_id,
        "created_at": datetime.utcnow(),
        "status": "crawling",
        "pages_crawled": 0,
        "docs_found": 0
    }
    await db.projects.insert_one(project_doc)
    
    print(f"Creating crawl job ID: {job_id}")
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
    await db.crawl_jobs.insert_one(job_doc)
    
    try:
        # 3. Crawl Website
        print("Executing crawler task...")
        await crawl_website_task(project_id, job_id, user_id)
        
        # Verify crawl results
        job = await db.crawl_jobs.find_one({"_id": job_id})
        print(f"Crawl job finished status: {job.get('status')}")
        if job.get("status") == "failed":
            print(f"[ERROR] Crawl job failed. Error: {job.get('error_message')}")
            return
            
        crawled_count = await db.crawled_pages.count_documents({"project_id": project_id})
        print(f"Pages crawled successfully: {crawled_count}")
        if crawled_count == 0:
            print("[ERROR] No pages crawled. Aborting.")
            return
            
        # List pages crawled
        pages = await db.crawled_pages.find({"project_id": project_id}).to_list(10)
        for idx, page in enumerate(pages):
            print(f"  Page {idx+1}: {page.get('url')} (type: {page.get('page_type')}, size: {len(page.get('text_content', ''))} chars)")
            
        # 4. Ingest and Index
        print("Executing indexing pipeline...")
        await process_project_crawled_data(project_id, user_id, force_recreate=True)
        
        project = await db.projects.find_one({"_id": project_id})
        print(f"Project status after indexing: {project.get('status')}")
        
        # 5. RAG Engine Query
        print("Executing RAG Query...")
        question = "What is digital health?"
        print(f"Question: '{question}'")
        
        response = await answer_project_question(
            question=question,
            project_id=project_id,
            user_id=user_id,
            strict_mode=False
        )
        
        print("\n--- RAG ANSWER ---")
        print(response.answer)
        print("------------------")
        print(f"Grounded: {response.grounded}")
        print(f"Sources cited: {response.sources}")
        
        if response.grounded and len(response.sources) > 0:
            print("[SUCCESS] RAG pipeline verified successfully!")
        else:
            print("[WARNING] RAG pipeline did not cite sources or was ungrounded.")
            
    except Exception as e:
        print(f"[ERROR] Test encountered error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 6. Cleanup
        print("Cleaning up database...")
        await db.projects.delete_one({"_id": project_id})
        await db.crawl_jobs.delete_many({"project_id": project_id})
        await db.crawled_pages.delete_many({"project_id": project_id})
        
        # Delete Qdrant collection
        from app.db.qdrant import delete_collection
        try:
            delete_collection(f"project_{project_id}")
            print(f"Deleted Qdrant collection project_{project_id}")
        except Exception as q_err:
            print(f"Qdrant cleanup warning: {q_err}")
            
        print("E2E Test complete!")

if __name__ == "__main__":
    asyncio.run(run_e2e_test())
