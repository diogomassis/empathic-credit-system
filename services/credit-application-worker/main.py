import asyncio
import asyncpg
import nats

from processing.processing import process_message
from configuration.config import logger, DATABASE_URL, NATS_URL, NATS_CONSUME_SUBJECT, DURABLE_NAME

async def main():
    """
    Main entry point for the Credit Application Worker service.
    """
    logger.info("Starting Credit Application Worker...")
    nats_conn = None
    db_pool = None
    try:
        logger.info("Connecting to PostgreSQL...")
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
        logger.info("PostgreSQL connection established.")

        logger.info(f"Connecting to NATS at {NATS_URL}...")
        nats_conn = await nats.connect(NATS_URL, name="credit_application_worker")
        js = nats_conn.jetstream()
        logger.info("NATS connection established.")

        sub = await js.subscribe(subject=NATS_CONSUME_SUBJECT, durable=DURABLE_NAME)
        logger.info(f"Waiting for messages on topic '{NATS_CONSUME_SUBJECT}'...")
        
        async for msg in sub.messages:
            await process_message(msg, db_pool, nats_conn)

    except Exception as e:
        logger.critical(f"A critical error occurred, shutting down the worker: {e}")
    finally:
        if nats_conn and nats_conn.is_connected:
            logger.info("Closing NATS connection...")
            await nats_conn.close()
        if db_pool:
            logger.info("Closing PostgreSQL connection...")
            await db_pool.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service manually terminated.")

