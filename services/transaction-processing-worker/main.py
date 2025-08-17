import asyncio
import os
import nats
import logging
import json
import asyncpg

from nats.js.api import ConsumerConfig
from nats.errors import MsgAlreadyAckdError
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ecsuser:ecspassword@localhost:5432/ecsdb")
DURABLE_NAME = "processor"
NATS_SUBJECT = "transactions.topic"

class TransactionCommand(BaseModel):
    """
    Represents a transaction command event received from NATS JetStream.

    Attributes:
        user_id (str): The unique identifier for the user associated with the transaction.
        amount (float): The transaction amount.
    """
    user_id: str = Field(..., alias="userId")
    amount: float

async def process_message(msg, db_pool):
    """
    Processes a single transaction event message from NATS JetStream and inserts it into the database.

    This function decodes the incoming message, validates its structure, and inserts a transaction record into PostgreSQL.
    Handles duplicate acknowledgments, JSON decoding errors, and other exceptions robustly.

    Args:
        msg: The NATS JetStream message containing the transaction event.
        db_pool: The asyncpg connection pool for PostgreSQL database operations.

    Returns:
        None
    """
    try:
        payload_str = msg.data.decode()
        data = json.loads(payload_str)
        transaction = TransactionCommand.model_validate(data)
        logging.info(f"Received transaction for userId: {transaction.user_id}")
        query = """
        INSERT INTO transactions (user_id, amount, created_at) VALUES ($1, $2, NOW());
        """
        async with db_pool.acquire() as conn:
            await conn.execute(
                query, 
                transaction.user_id,
                transaction.amount
            )
        await msg.ack()
        logging.info(f"Transaction successfully processed for userId: {transaction.user_id}")
    except json.JSONDecodeError as e:
        logging.error(f"JSON decoding error: {e}. Message: {msg.data.decode()}")
        await msg.ack()
    except MsgAlreadyAckdError:
        logging.warning(f"Message has already been acknowledged, probably by another replica.")
    except Exception as e:
        logging.error(f"Error processing message: {e}")
        await msg.nak(delay=10)

async def main():
    """
    Main entry point for the Transaction Processing Worker service.

    Establishes connections to PostgreSQL and NATS JetStream, subscribes to transaction event topics,
    and processes incoming messages asynchronously. Handles graceful shutdown and error logging.

    Returns:
        None
    """
    logging.info("Starting Transaction Processing Worker...")
    nc = None
    db_pool = None
    try:
        logging.info("Connecting to PostgreSQL...")
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
        logging.info("Connection to PostgreSQL established.")

        logging.info(f"Connecting to NATS at {NATS_URL}...")
        nc = await nats.connect(NATS_URL, name="transaction_processing_worker")
        js = nc.jetstream()
        logging.info("Connection to NATS established.")

        async def message_handler(msg):
            """
            Handles incoming NATS messages by scheduling their processing asynchronously.

            Args:
                msg: The NATS JetStream message to process.

            Returns:
                None
            """
            asyncio.create_task(process_message(msg, db_pool))

        consumer_config = ConsumerConfig(
            max_ack_pending=800
        )
        _ = await js.subscribe(
            subject=NATS_SUBJECT, 
            queue=DURABLE_NAME, 
            cb=message_handler,
            config=consumer_config
        )
        logging.info(f"Waiting for messages on topic '{NATS_SUBJECT}'...")
        await asyncio.Future()
    except Exception as e:
        logging.critical(f"A critical error occurred, shutting down the worker: {e}")
    finally:
        if nc and nc.is_connected:
            logging.info("Closing connection to NATS...")
            await nc.close()
        if db_pool:
            logging.info("Closing PostgreSQL connection...")
            await db_pool.close()

if __name__ == '__main__':
    """
    Script entry point. Runs the main async function and handles manual termination.
    """
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Service manually terminated.")
