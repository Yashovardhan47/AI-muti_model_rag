"""Small per-IP limiter; use Redis for shared state when deploying multiple workers."""
import time
from collections import defaultdict, deque
from threading import Lock
from fastapi import HTTPException, Request
from app.core.config import get_settings

_lock = Lock()
_local = defaultdict(deque)


def limit(group: str, count: int):
    def dependency(request: Request):
        key = f"rl:{group}:{request.client.host if request.client else 'unknown'}"
        cfg = get_settings()
        if cfg.redis_url:
            import redis
            try:
                client = redis.Redis.from_url(cfg.redis_url, socket_timeout=2)
                current = client.incr(key)
                if current == 1: client.expire(key, 60)
                if current > count: raise HTTPException(429, "Rate limit exceeded")
            except redis.RedisError as exc:
                raise HTTPException(503, "Rate limiter unavailable") from exc
        else:
            with _lock:
                bucket = _local[key]
                while bucket and bucket[0] < time.monotonic() - 60: bucket.popleft()
                if len(bucket) >= count: raise HTTPException(429, "Rate limit exceeded")
                bucket.append(time.monotonic())
    return dependency
