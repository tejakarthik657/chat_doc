import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

async def check():
    print("--- Starting DB Check ---")
    load_dotenv()
    
    mongo_url = os.getenv("MONGODB_URL")
    if not mongo_url:
        print("❌ MONGODB_URL not found in environment")
        return
    
    try:
        client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=5000)
        db_name = os.getenv("DB_NAME", "rag_db")
        db = client[db_name]
        
        users = await db.users.find().to_list(100)
        print(f"Users found: {len(users)}")
        for u in users:
            print(f"  User ID: {u['_id']}, Email: {u.get('email')}")
            
        projects = await db.projects.find().to_list(100)
        print(f"Projects found: {len(projects)}")
        for p in projects:
            print(f"  Project ID: {p['_id']}, Name: {p.get('name')}, URL: {p.get('website_url')}, Status: {p.get('status')}")
            
        docs = await db.documents.find().to_list(100)
        print(f"Documents found: {len(docs)}")
        for d in docs:
            print(f"  Doc ID: {d['_id']}, Name: {d.get('filename')}, Status: {d.get('status')}")
            
    except Exception as e:
        print(f"❌ Connection Failed: {e}")

if __name__ == "__main__":
    asyncio.run(check())
