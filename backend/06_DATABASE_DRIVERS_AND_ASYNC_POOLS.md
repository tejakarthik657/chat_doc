# 06. Database Drivers & Async Connection Pools

> *"A junior engineer opens a new database connection inside every route handler. A senior backend engineer creates an asynchronous connection pool on startup, manages socket lifecycles, and ensures queries never block the event loop."*

---

## 1. Why Synchronous Database Drivers Destroy FastAPI Throughput

In standard Python, `pymongo` and `sqlite3` are **synchronous blocking libraries**:
When `pymongo.find_one(...)` runs, the underlying C socket waits for the database response over the network. During those 20ms, Python's thread is completely locked—no other concurrent requests can be handled on the event loop.

To achieve high concurrency, FastAPI requires **Asynchronous Drivers**:
- **MongoDB**: We use **`Motor` (`motor.motor_asyncio`)**, which wraps the MongoDB C driver in Python `asyncio` coroutines.
- **Relational SQL**: We use **`aiosqlite`** (or `asyncpg` for PostgreSQL), allowing read-only SQL queries to yield control back to the event loop.
- **Qdrant Vector DB**: We use **`AsyncQdrantClient`**, executing HNSW vector searches over non-blocking HTTP/2 or gRPC sockets.

---

## 2. Managing MongoDB Atlas Connection Pools with Motor

In [`rag-backend/app/db/mongodb.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/db/mongodb.py), we initialize the client globally during lifespan startup:

```python
# rag-backend/app/db/mongodb.py
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings
from app.core.logger import logger

# Module-level client holder
_client: AsyncIOMotorClient = None
_db: AsyncIOMotorDatabase = None

async def init_db_client():
    """Initializes the connection pool on application startup."""
    global _client, _db
    try:
        _client = AsyncIOMotorClient(
            settings.mongodb_uri,
            maxPoolSize=50,                  # Max concurrent open sockets
            minPoolSize=10,                  # Keep 10 sockets warm in pool
            serverSelectionTimeoutMS=5000,   # 5-second fast failover
            connectTimeoutMS=10000
        )
        _db = _client[settings.mongodb_db_name]
        
        # Test connection with a quick ping
        await _db.command("ping")
        logger.info("[MongoDB] Connected successfully to Atlas replica set.")
        
        # Ensure compound indexes exist
        await create_indexes()
    except Exception as e:
        logger.error(f"[MongoDB] Failed to connect: {e}")
        raise e

async def close_db_client():
    """Closes all sockets on application shutdown."""
    global _client
    if _client:
        _client.close()
        logger.info("[MongoDB] Connection pool closed cleanly.")
```

---

## 3. The Accessor Factory Pattern

Instead of passing the raw database client around, we write typed collection accessors:

```python
# rag-backend/app/db/mongodb.py
from motor.motor_asyncio import AsyncIOMotorCollection

def get_database() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("Database client is not initialized!")
    return _db

def users_col() -> AsyncIOMotorCollection:
    return get_database()["users"]

def documents_col() -> AsyncIOMotorCollection:
    return get_database()["documents"]

def compliance_audits_col() -> AsyncIOMotorCollection:
    return get_database()["compliance_audits"]
```

### Why this pattern is clean:
1. **Zero Circular Imports**: Route files simply do `from app.db.mongodb import compliance_audits_col`.
2. **Instant Mocking**: During unit tests, you can easily mock `compliance_audits_col()` with an in-memory dictionary without mocking the entire MongoDB wire protocol.

---

## 4. Automated Startup Indexing

A query without an index forces a full collection scan ($O(N)$), locking the database CPU when collection size grows. 

We guarantee indexes exist during startup:

```python
async def create_indexes():
    """Ensures compound and unique indexes exist on application boot."""
    # 1. Unique email index for authentication
    await users_col().create_index("email", unique=True)
    
    # 2. Compound index for project document retrieval
    await documents_col().create_index([("project_id", 1), ("created_at", -1)])
    
    # 3. Compound index for chunk parent-child lookups
    await get_database()["chunks"].create_index([("doc_id", 1), ("chunk_type", 1), ("parent_id", 1)])
    
    # 4. Filtered index for compliance audits
    await compliance_audits_col().create_index([("project_id", 1), ("audit_status", 1)])
```

---

## 5. Inbound Relational EHR Database Connector (`mcp/db_connector.py`)

For querying live hospital patient records, we use SQLite (or PostgreSQL via async connection pools) with built-in AST safety checks:

```python
# rag-backend/app/mcp/db_connector.py
import aiosqlite
import sqlparse

DB_PATH = "./storage/clinical_sample.db"

def validate_ast_safety(sql_query: str) -> bool:
    """Verifies that the generated query is strictly a read-only SELECT statement."""
    parsed = sqlparse.parse(sql_query)
    if not parsed:
        return False
    statement = parsed[0]
    
    # Enforce SELECT only
    if statement.get_type() != "SELECT":
        raise ValueError("Security Violation: Only read-only SELECT queries are permitted.")
        
    # Check for forbidden keywords
    forbidden = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", ";"]
    raw_upper = sql_query.upper()
    for word in forbidden:
        if word in raw_upper and word != "SELECT":
            raise ValueError(f"Forbidden keyword detected: {word}")
    return True

async def execute_clinical_query(sql_query: str) -> list[dict]:
    validate_ast_safety(sql_query)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(sql_query) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
```
This guarantees that operational database reads are fast, asynchronous, and completely immune to destructive SQL injections.
