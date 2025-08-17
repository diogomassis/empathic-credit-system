import asyncio
import asyncpg
import nats

from nats.js.api import ConsumerConfig
from processing.processing import process_message
from configuration.config import logger, DATABASE_URL, NATS_URL, NATS_SUBJECT, DURABLE_NAME

async def main():
    """
    Main entry point for the Transaction Processing Worker.
    """
    logger.info("Starting Transaction Processing Worker...")
    nats_conn = None
    db_pool = None
    try:
        logger.info("Connecting to PostgreSQL...")
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
        logger.info("PostgreSQL connection established.")

        logger.info(f"Connecting to NATS at {NATS_URL}...")
        nats_conn = await nats.connect(NATS_URL, name="transaction_processing_worker")
        js = nats_conn.jetstream()
        logger.info("NATS connection established.")

        async def message_handler(msg):
            asyncio.create_task(process_message(msg, db_pool))
        consumer_config = ConsumerConfig(max_ack_pending=800)
        await js.subscribe(
            subject=NATS_SUBJECT, 
            queue=DURABLE_NAME, 
            cb=message_handler,
            config=consumer_config
        )
        logger.info(f"Waiting for messages on topic '{NATS_SUBJECT}'...")
        await asyncio.Future()
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
        logger.info("Service manually stopped.")
