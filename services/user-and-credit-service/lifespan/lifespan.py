import asyncpg
import httpx
import nats
import redis.asyncio as redis

from fastapi import FastAPI
from contextlib import asynccontextmanager
from configuration.config import logger, DATABASE_URL, NATS_URL, REDIS_URL

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager for service connections.
    """
    logger.info("Initializing service connections...")
    try:
        app.state.db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
        app.state.http_client = httpx.AsyncClient(timeout=5.0)
        app.state.nats_conn = await nats.connect(NATS_URL, name="user_credit_service")
        app.state.redis_client = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
        await app.state.redis_client.ping()
        logger.info("All connections were successfully established.")
        yield
    finally:
        logger.info("Closing service connections...")
        if hasattr(app.state, 'db_pool'):
            await app.state.db_pool.close()
        if hasattr(app.state, 'http_client'):
            await app.state.http_client.aclose()
        if hasattr(app.state, 'nats_conn') and app.state.nats_conn.is_connected:
            await app.state.nats_conn.close()
        if hasattr(app.state, 'redis_client'):
            await app.state.redis_client.close()
        logger.info("All connections have been closed.")
