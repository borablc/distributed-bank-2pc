import redis

_redis_client = None

def get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(
            host="127.0.0.1",
            port=6379,
            decode_responses=True,
        )
    return _redis_client
