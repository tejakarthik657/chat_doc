import logging
from typing import Optional
from neo4j import GraphDatabase, Driver
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_driver: Optional[Driver] = None

def get_neo4j_driver() -> Driver:
    """Lazily initialize and return the Neo4j driver connection pool."""
    global _driver
    if _driver is None:
        try:
            logger.info(f"[Neo4j] Connecting to instance via URL: {settings.neo4j_uri}")
            _driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_username, settings.neo4j_password)
            )
            # Verify connectivity immediately
            _driver.verify_connectivity()
            logger.info("[Neo4j] Connected and verified successfully.")
        except Exception as e:
            logger.error(f"[Neo4j] Failed to initialize driver: {e}")
            _driver = None
            raise
    return _driver

def close_neo4j_driver():
    """Gracefully close the Neo4j driver connection pool."""
    global _driver
    if _driver is not None:
        logger.info("[Neo4j] Closing connection pool.")
        _driver.close()
        _driver = None

def execute_query(query: str, parameters: Optional[dict] = None) -> list:
    """Helper utility to execute a Cypher query with optional parameters."""
    driver = get_neo4j_driver()
    with driver.session() as session:
        result = session.run(query, parameters or {})
        return [record.data() for record in result]
