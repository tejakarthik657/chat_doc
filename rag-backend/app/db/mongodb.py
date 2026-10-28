try:
    import dns.resolver
    dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
    dns.resolver.default_resolver.nameservers = ['8.8.8.8', '8.8.4.4', '1.1.1.1']
except Exception:
    pass

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import get_settings

settings = get_settings()

_client: AsyncIOMotorClient = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        mongo_url = os.environ.get("MONGODB_URI") or os.environ.get("MONGODB_URL") or settings.mongodb_url
        if "localhost" in mongo_url:
            mongo_url = mongo_url.replace("localhost", "127.0.0.1")
        _client = AsyncIOMotorClient(
            mongo_url,
            maxPoolSize=50,
            minPoolSize=5,
            serverSelectionTimeoutMS=30000,   # 30s timeout for Atlas TLS replica set discovery
            connectTimeoutMS=20000,           # 20s initial handshake timeout
            socketTimeoutMS=45000,
            waitQueueTimeoutMS=10000,
        )
    return _client


def get_db():
    return get_client()[settings.db_name]


# Collection accessors
def users_col():
    return get_db()["users"]

def documents_col():
    return get_db()["documents"]

def chunks_col():
    return get_db()["chunks"]

def chat_history_col():
    return get_db()["chat_history"]

def memory_col():
    return get_db()["conversation_memory"]

def analytics_col():
    return get_db()["question_analytics"]

def projects_col():
    return get_db()["projects"]

def crawl_jobs_col():
    return get_db()["crawl_jobs"]

def crawled_pages_col():
    return get_db()["crawled_pages"]

def nexus_memories_col():
    return get_db()["nexus_memories"]


async def create_indexes():
    """Run once at startup with automatic retry to handle Atlas cold handshakes."""
    import asyncio
    for attempt in range(3):
        try:
            await users_col().create_index("email", unique=True)
            await documents_col().create_index([("user_id", 1), ("_id", 1)])
            await chat_history_col().create_index([("user_id", 1), ("doc_id", 1)])
            await chat_history_col().create_index([("doc_id", 1), ("timestamp", -1)])
            await chunks_col().create_index([("doc_id", 1), ("embedding_id", 1)])
            await analytics_col().create_index([("user_id", 1), ("timestamp", -1)])
            await memory_col().create_index([("doc_id", 1), ("user_id", 1)], unique=True)
            await nexus_memories_col().create_index([("user_id", 1), ("project_id", 1)])

            # Projects & Crawlers
            await projects_col().create_index([("user_id", 1), ("_id", 1)])
            await crawl_jobs_col().create_index([("project_id", 1), ("_id", 1)])
            await crawled_pages_col().create_index([("project_id", 1), ("url", 1)], unique=True)
            print("[MongoDB Atlas] Production indexes verified successfully.")
            return
        except Exception as e:
            if attempt < 2:
                print(f"[MongoDB Atlas] Replica set initializing (attempt {attempt+1}/3: {e}). Retrying in 2s...")
                await asyncio.sleep(2)
            else:
                print(f"[MongoDB Atlas Warning] Index creation notice: {e}. App continuing normally.")
