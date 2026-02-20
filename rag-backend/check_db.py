import sys
import os
sys.path.append(os.getcwd())

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import get_settings

async def check():
    settings = get_settings()
    print(f"URL: {settings.mongodb_url}")
    print(f"DB: {settings.db_name}")
    
    try:
        client = AsyncIOMotorClient(settings.mongodb_url)
        # Force a connection
        await client.admin.command('ping')
        print("✅ Connection Successful!")
        
        db = client[settings.db_name]
        cols = await db.list_collection_names()
        print(f"Collections: {cols}")
        
    except Exception as e:
        print(f"❌ Connection Failed: {e}")

if __name__ == "__main__":
    asyncio.run(check())
