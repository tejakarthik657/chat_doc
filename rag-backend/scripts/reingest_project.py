"""One-off script to re-ingest a project with the current pipeline."""
import asyncio
import os
import sys

# Allow running as: python scripts/reingest_project.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import get_settings
from app.ingestion.pipeline import process_project_crawled_data


async def main(project_id: str, user_id: str) -> None:
    settings = get_settings()
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.db_name]

    result = await db.crawled_pages.update_many(
        {"project_id": project_id},
        {"$set": {"status": "pending"}, "$unset": {"error_message": ""}},
    )
    print(f"Marked {result.modified_count} pages as pending")

    await db.projects.update_one({"_id": project_id}, {"$set": {"status": "indexing"}})
    await process_project_crawled_data(project_id, user_id, force_recreate=True)
    print("Re-ingest complete")


if __name__ == "__main__":
    pid = sys.argv[1] if len(sys.argv) > 1 else "6a3828baab2b33968331ac56"
    uid = sys.argv[2] if len(sys.argv) > 2 else "6a37fd62aef3c526e5f74f9f"
    asyncio.run(main(pid, uid))
