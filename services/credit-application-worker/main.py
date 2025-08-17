import os
import json
import logging
import asyncio
import nats
import asyncpg
import uuid

from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

DURABLE_NAME = "processor"
NATS_NOTIFY_SUBJECT = "user.notifications"
NATS_CONSUME_SUBJECT = "credit.offers.approved"
NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ecsuser:ecspassword@localhost:5432/ecsdb")

class CreditOfferAcceptedEvent(BaseModel):
    """
    Represents an event indicating that a credit offer has been accepted by a user.

    Attributes:
        offer_id (uuid.UUID): Unique identifier for the credit offer.
        user_id (uuid.UUID): Unique identifier for the user who accepted the offer.
        accepted_at (str): ISO 8601 timestamp of when the offer was accepted.
    """
    offer_id: uuid.UUID = Field(..., alias="offerId")
    user_id: uuid.UUID = Field(..., alias="userId")
    accepted_at: str = Field(..., alias="acceptedAt")

async def process_message(msg, db_pool, nats_conn):
    """
    Processes a single credit offer acceptance message from NATS JetStream.

    This function validates the incoming message, updates the corresponding credit offer status in the database,
    sends a notification to the user, and acknowledges the message. If an error occurs, the message is negatively acknowledged for retry.

    Args:
        msg: The NATS JetStream message containing the credit offer acceptance event.
        db_pool: The asyncpg connection pool for PostgreSQL database operations.
        nats_conn: The NATS connection object for publishing notifications.

    Returns:
        None
    """
    event = None
    try:
        data = json.loads(msg.data.decode())
        event = CreditOfferAcceptedEvent.model_validate(data)
        logging.info(f"Processing acceptance for offerId: {event.offer_id}, userId: {event.user_id}")

        async with db_pool.acquire() as conn:
            update_query = """
            UPDATE credit_limits
            SET status = 'active', activated_at = NOW(), updated_at = NOW()
            WHERE id = $1 AND user_id = $2 AND status = 'offered';
            """
            result = await conn.execute(update_query, event.offer_id, event.user_id)
            if result.strip() == "UPDATE 0":
                logging.warning(f"Offer {event.offer_id} for user {event.user_id} was not in a valid state to be activated. Acknowledging to avoid retries.")
                await msg.ack()
                return
        logging.info(f"Offer {event.offer_id} successfully activated for user {event.user_id} in the database.")
        notification_payload = {
            "userId": str(event.user_id),
            "type": "CREDIT_LIMIT_APPLIED",
            "title": "Credit Limit Active!",
            "message": "Your new credit limit is now available for use."
        }
        await nats_conn.publish(NATS_NOTIFY_SUBJECT, json.dumps(notification_payload).encode())
        logging.info(f"Notification event for user {event.user_id} published to '{NATS_NOTIFY_SUBJECT}'.")
        await msg.ack()
    except Exception as e:
        logging.error(f"Failed to process message for offerId {event.offer_id if event else 'N/A'}: {e}")
        await msg.nak(delay=10)

async def main():
    """
    Main entry point for the Credit Application Worker service.

    Establishes connections to PostgreSQL and NATS JetStream, subscribes to credit offer approval events,
    and processes incoming messages in an asynchronous loop. Handles graceful shutdown and error logging.

    Returns:
        None
    """
    logging.info("Starting Credit Application Worker...")
    nc = None
    db_pool = None
    try:
        logging.info("Connecting to PostgreSQL...")
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
        logging.info("PostgreSQL connection established.")

        logging.info(f"Connecting to NATS at {NATS_URL}...")
        nc = await nats.connect(NATS_URL, name="credit_application_worker")
        js = nc.jetstream()
        logging.info("NATS connection established.")

        sub = await js.subscribe(subject=NATS_CONSUME_SUBJECT, durable=DURABLE_NAME)
        logging.info(f"Waiting for messages on subject '{NATS_CONSUME_SUBJECT}'...")
        
        async for msg in sub.messages:
            await process_message(msg, db_pool, nc)
    except Exception as e:
        logging.critical(f"A critical error occurred, shutting down worker: {e}")
    finally:
        if nc and nc.is_connected:
            logging.info("Closing NATS connection...")
            await nc.close()
        if db_pool:
            logging.info("Closing PostgreSQL connection...")
            await db_pool.close()

if __name__ == "__main__":
    """
    Script entry point. Runs the main async function and handles manual termination.
    """
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Service manually terminated.")
