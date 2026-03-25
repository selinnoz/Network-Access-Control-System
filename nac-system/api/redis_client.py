import redis.asyncio as redis
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

# Redis bağlantı havuzu
redis_pool = redis.ConnectionPool.from_url(REDIS_URL, decode_responses=True)

def get_redis():
    return redis.Redis(connection_pool=redis_pool)

# ------------------------------------------------
# Rate Limiting
# ------------------------------------------------
RATE_LIMIT_MAX    = 5    # maksimum başarısız deneme
RATE_LIMIT_WINDOW = 300  # saniye (5 dakika)

async def check_rate_limit(username: str) -> bool:
    """True dönerse giriş engellendi demek."""
    r = get_redis()
    key = f"ratelimit:{username}"
    count = await r.get(key)
    return int(count) >= RATE_LIMIT_MAX if count else False

async def increment_failed_attempts(username: str):
    r = get_redis()
    key = f"ratelimit:{username}"
    pipe = r.pipeline()
    await pipe.incr(key)
    await pipe.expire(key, RATE_LIMIT_WINDOW)
    await pipe.execute()

async def reset_failed_attempts(username: str):
    r = get_redis()
    await r.delete(f"ratelimit:{username}")

# ------------------------------------------------
# Aktif Oturum Cache
# ------------------------------------------------
SESSION_TTL = 86400  # 24 saat

async def cache_session(session_id: str, data: dict):
    r = get_redis()
    key = f"session:{session_id}"
    await r.hset(key, mapping={k: str(v) for k, v in data.items()})
    await r.expire(key, SESSION_TTL)

async def get_session(session_id: str) -> dict | None:
    r = get_redis()
    data = await r.hgetall(f"session:{session_id}")
    return data if data else None

async def delete_session(session_id: str):
    r = get_redis()
    await r.delete(f"session:{session_id}")

async def get_all_active_sessions() -> list[dict]:
    r = get_redis()
    keys = await r.keys("session:*")
    sessions = []
    for key in keys:
        data = await r.hgetall(key)
        if data:
            sessions.append(data)
    return sessions

async def check_redis_connection() -> bool:
    try:
        r = get_redis()
        await r.ping()
        return True
    except Exception:
        return False