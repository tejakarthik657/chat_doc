from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import get_settings

settings = get_settings()

_client: AsyncIOMotorClient = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(
            settings.mongodb_url,
            maxPoolSize=10,
            minPoolSize=2,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            socketTimeoutMS=30000,
            waitQueueTimeoutMS=5000,
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


async def create_indexes():
    """Run once at startup to ensure fast queries."""
    await users_col().create_index("email", unique=True)
    await documents_col().create_index([("user_id", 1), ("_id", 1)])
    await chat_history_col().create_index([("user_id", 1), ("doc_id", 1)])
    await chunks_col().create_index([("doc_id", 1), ("embedding_id", 1)])
    await analytics_col().create_index([("user_id", 1), ("timestamp", -1)])

    # Projects & Crawlers
    await projects_col().create_index([("user_id", 1), ("_id", 1)])
    await crawl_jobs_col().create_index([("project_id", 1), ("_id", 1)])
    await crawled_pages_col().create_index([("project_id", 1), ("url", 1)], unique=True)
