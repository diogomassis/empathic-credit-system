import nats

from fastapi import FastAPI
from contextlib import asynccontextmanager
from configuration.config import logger, NATS_URL

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle manager for NATS connection.
    """
    logger.info(f"Connecting to NATS at {NATS_URL}...")
    try:
        nc = await nats.connect(NATS_URL, name="transaction_service")
        app.state.nats_connection = nc
        logger.info("Connected to NATS.")
        yield
    finally:
        if hasattr(app.state, 'nats_connection') and app.state.nats_connection.is_connected:
            logger.info("Closing NATS connection...")
            await app.state.nats_connection.close()
            logger.info("NATS connection closed.")
