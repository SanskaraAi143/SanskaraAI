import redis
import json
import logging
from functools import wraps
from config import REDIS_URL, REDIS_CACHE_ENABLED

# --- Redis Client Initialization ---
redis_client = None
if REDIS_CACHE_ENABLED:
    try:
        # The `decode_responses=True` argument ensures that Redis returns strings, not bytes.
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        # Check if the connection is alive
        redis_client.ping()
        logging.info(f"Successfully connected to Redis at {REDIS_URL}")
    except redis.exceptions.ConnectionError as e:
        logging.error(f"Could not connect to Redis at {REDIS_URL}: {e}. Caching will be disabled.")
        redis_client = None
        REDIS_CACHE_ENABLED = False

# --- Cache Helper Functions ---

def get_from_cache(key: str):
    """
    Retrieves an item from the cache.
    Returns None if the item is not found or if caching is disabled.
    """
    if not REDIS_CACHE_ENABLED or not redis_client:
        return None
    try:
        cached_value = redis_client.get(key)
        if cached_value:
            logging.debug(f"Cache HIT for key: {key}")
            return json.loads(cached_value)
        logging.debug(f"Cache MISS for key: {key}")
        return None
    except (redis.exceptions.RedisError, json.JSONDecodeError) as e:
        logging.error(f"Error retrieving from cache for key {key}: {e}")
        return None

def set_to_cache(key: str, value: any, ttl: int = 3600):
    """
    Sets an item in the cache with a time-to-live (TTL).
    Does nothing if caching is disabled.
    """
    if not REDIS_CACHE_ENABLED or not redis_client:
        return
    try:
        # Serialize Python objects to a JSON string for storage in Redis
        serialized_value = json.dumps(value)
        redis_client.setex(key, ttl, serialized_value)
        logging.debug(f"Cached value for key: {key} with TTL: {ttl}s")
    except (redis.exceptions.RedisError, TypeError) as e:
        logging.error(f"Error setting cache for key {key}: {e}")

def invalidate_cache(key: str):
    """
    Deletes an item from the cache.
    """
    if not REDIS_CACHE_ENABLED or not redis_client:
        return
    try:
        redis_client.delete(key)
        logging.debug(f"Invalidated cache for key: {key}")
    except redis.exceptions.RedisError as e:
        logging.error(f"Error invalidating cache for key {key}: {e}")

# --- Cache Decorator (Optional, for more advanced usage) ---

def cache_result(ttl: int = 3600):
    """
    A decorator to automatically cache the results of a function.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create a unique cache key from the function name and arguments
            key = f"{func.__name__}:{json.dumps(args)}:{json.dumps(kwargs)}"

            cached_value = get_from_cache(key)
            if cached_value:
                return cached_value

            result = await func(*args, **kwargs)

            set_to_cache(key, result, ttl)

            return result
        return wrapper
    return decorator