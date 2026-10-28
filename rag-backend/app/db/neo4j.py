import logging
from typing import Optional
from neo4j import GraphDatabase, Driver
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_driver: Optional[Driver] = None
_driver_initialized: bool = False

def get_neo4j_driver() -> Optional[Driver]:
    """Lazily initialize and return the Neo4j driver connection pool."""
    global _driver, _driver_initialized
    if not _driver_initialized:
        _driver_initialized = True
        try:
            logger.info(f"[Neo4j] Connecting to instance via URL: {settings.neo4j_uri}")
            _driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_username, settings.neo4j_password)
            )
            # Verify connectivity
            _driver.verify_connectivity()
            logger.info("[Neo4j] Connected and verified successfully to AuraDB.")
        except Exception as e:
            logger.warning(f"[Neo4j] AuraDB connectivity notice: {e}. GraphRAG will fall back to vector search.")
            _driver = None
    return _driver

def close_neo4j_driver():
    """Gracefully close the Neo4j driver connection pool."""
    global _driver
    if _driver is not None:
        try:
            logger.info("[Neo4j] Closing connection pool.")
            _driver.close()
        except Exception:
            pass
        _driver = None

def execute_query(query: str, parameters: Optional[dict] = None) -> list:
    """Helper utility to execute a Cypher query with optional parameters."""
    try:
        driver = get_neo4j_driver()
        if not driver:
            return []
        db_name = getattr(settings, "neo4j_database", "neo4j")
        with driver.session(database=db_name) as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]
    except Exception as query_err:
        logger.warning(f"[Neo4j Query Error] {query_err}")
        return []
