import sys
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

# Manually load env to avoid dependency issues with app.core.config if that's broken
from dotenv import load_dotenv

logging_file = "db_test_log.txt"

def log(msg):
    print(msg)
    with open(logging_file, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

async def check():
    log("--- Starting DB Check ---")
    load_dotenv()
    
    mongo_url = os.getenv("MONGODB_URL")
    if not mongo_url:
        log("❌ MONGODB_URL not found in environment")
        return

    # Mask password for logging
    safe_url = mongo_url.split("@")[-1] if "@" in mongo_url else "..."
    log(f"Attempting connection to @{safe_url}")
    
    try:
        # Set serverSelectionTimeoutMS to 5000 (5 seconds) to fail fast
        client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=5000)
        
        log("Client created. Sending ping...")
        await client.admin.command('ping')
        log("✅ Connection Successful! Ping returned.")
        
        db_name = os.getenv("DB_NAME", "rag_db")
        db = client[db_name]
        cols = await db.list_collection_names()
        log(f"Collections in {db_name}: {cols}")
        
    except Exception as e:
        log(f"❌ Connection Failed: {type(e).__name__}: {e}")
        import traceback
        log(traceback.format_exc())

if __name__ == "__main__":
    # Clear log file
    with open(logging_file, "w") as f:
        f.write("")
    
    try:
        asyncio.run(check())
    except Exception as e:
        log(f"❌ Script Crash: {e}")
