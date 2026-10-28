"""
Upstash Redis Cloud Integration.
Provides serverless, firewall-safe distributed caching and event streaming via REST API.
No local Redis daemon required.
"""
import logging
from typing import Optional, Any
import httpx
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class UpstashRedisClient:
    def __init__(self, rest_url: Optional[str] = None, token: Optional[str] = None):
        self.url = (rest_url or settings.upstash_redis_rest_url or "").rstrip("/")
        self.token = token or settings.upstash_redis_rest_token or ""
        self.headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        self.enabled = bool(self.url and self.token)
        self._async_client: Optional[httpx.AsyncClient] = None
        self._sync_client: Optional[httpx.Client] = None
        self._consecutive_errors: int = 0
        if self.enabled:
            logger.info(f"[Upstash Redis] Configured with endpoint: {self.url}")

    def _get_async_client(self) -> httpx.AsyncClient:
        import asyncio
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if self._async_client is not None:
            client_loop = getattr(self._async_client, "_loop", None)
            if self._async_client.is_closed or (client_loop and current_loop and client_loop != current_loop):
                self._async_client = None

        if self._async_client is None:
            limits = httpx.Limits(max_keepalive_connections=10, max_connections=20, keepalive_expiry=60.0)
            timeout = httpx.Timeout(timeout=10.0, connect=5.0)
            self._async_client = httpx.AsyncClient(
                headers=self.headers,
                limits=limits,
                timeout=timeout,
            )
            self._async_client._loop = current_loop
        return self._async_client

    def _get_sync_client(self) -> httpx.Client:
        if self._sync_client is None or self._sync_client.is_closed:
            limits = httpx.Limits(max_keepalive_connections=10, max_connections=20, keepalive_expiry=60.0)
            timeout = httpx.Timeout(timeout=10.0, connect=5.0)
            self._sync_client = httpx.Client(
                headers=self.headers,
                limits=limits,
                timeout=timeout,
            )
        return self._sync_client

    async def execute_async(self, *command: Any) -> Any:
        """Execute any Redis command asynchronously over Upstash REST with connection pooling and retries."""
        if not self.enabled:
            return None
        for attempt in range(2):
            client = self._get_async_client()
            try:
                res = await client.post(self.url, json=list(command))
                if res.status_code == 200:
                    if self._consecutive_errors > 0:
                        logger.info("[Upstash Redis] Connection restored successfully.")
                        self._consecutive_errors = 0
                    return res.json().get("result")
                else:
                    logger.warning(f"[Upstash] Command failed: {res.status_code} - {res.text}")
                    return None
            except Exception as e:
                self._consecutive_errors += 1
                if isinstance(e, (httpx.ConnectError, httpx.ConnectTimeout, httpx.RemoteProtocolError, httpx.TransportError)):
                    try:
                        await client.aclose()
                    except Exception:
                        pass
                    self._async_client = None

                if attempt == 0:
                    import asyncio
                    await asyncio.sleep(0.3)
                    continue

                err_msg = str(e).strip() or type(e).__name__
                if self._consecutive_errors <= 3 or self._consecutive_errors % 20 == 0:
                    logger.warning(f"[Upstash Error] {type(e).__name__}: {err_msg}")
                return None
        return None

    def execute_sync(self, *command: Any) -> Any:
        """Execute any Redis command synchronously over Upstash REST with connection pooling and retries."""
        if not self.enabled:
            return None
        for attempt in range(2):
            client = self._get_sync_client()
            try:
                res = client.post(self.url, json=list(command))
                if res.status_code == 200:
                    if self._consecutive_errors > 0:
                        logger.info("[Upstash Redis] Connection restored successfully.")
                        self._consecutive_errors = 0
                    return res.json().get("result")
                else:
                    logger.warning(f"[Upstash] Command failed: {res.status_code} - {res.text}")
                    return None
            except Exception as e:
                self._consecutive_errors += 1
                if isinstance(e, (httpx.ConnectError, httpx.ConnectTimeout, httpx.RemoteProtocolError, httpx.TransportError)):
                    try:
                        client.close()
                    except Exception:
                        pass
                    self._sync_client = None

                if attempt == 0:
                    import time
                    time.sleep(0.3)
                    continue

                err_msg = str(e).strip() or type(e).__name__
                if self._consecutive_errors <= 3 or self._consecutive_errors % 20 == 0:
                    logger.warning(f"[Upstash Error] {type(e).__name__}: {err_msg}")
                return None
        return None

    async def aclose(self):
        """Close asynchronous client session cleanly."""
        if self._async_client and not self._async_client.is_closed:
            try:
                await self._async_client.aclose()
            except Exception:
                pass
            self._async_client = None

    def close(self):
        """Close synchronous client session cleanly."""
        if self._sync_client and not self._sync_client.is_closed:
            try:
                self._sync_client.close()
            except Exception:
                pass
            self._sync_client = None

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        cmd = ["SET", key, value]
        if ex:
            cmd.extend(["EX", str(ex)])
        res = await self.execute_async(*cmd)
        return res == "OK"

    async def get(self, key: str) -> Optional[str]:
        return await self.execute_async("GET", key)

    async def delete(self, key: str) -> bool:
        res = await self.execute_async("DEL", key)
        return bool(res)

    async def push_event(self, queue_name: str, payload_json: str) -> bool:
        """Enqueue task/event to a list."""
        res = await self.execute_async("LPUSH", queue_name, payload_json)
        return bool(res)

    async def pop_event(self, queue_name: str) -> Optional[str]:
        """Dequeue task/event from a list."""
        return await self.execute_async("RPOP", queue_name)


_upstash_instance: Optional[UpstashRedisClient] = None

def get_upstash_client() -> UpstashRedisClient:
    global _upstash_instance
    if _upstash_instance is None:
        _upstash_instance = UpstashRedisClient()
    return _upstash_instance
