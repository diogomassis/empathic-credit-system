import json

from configuration.config import logger
from models.models import CreditOfferAcceptedEvent
from database.database import activate_credit_offer
from messaging.messaging import send_activation_notification

async def process_message(msg, db_pool, nats_conn):
    """
    Processes a single credit offer acceptance message.
    """
    event = None
    try:
        data = json.loads(msg.data.decode())
        event = CreditOfferAcceptedEvent.model_validate(data)
        logger.info(f"Processing acceptance for offerId: {event.offer_id}, userId: {event.user_id}")

        async with db_pool.acquire() as conn:
            was_activated = await activate_credit_offer(conn, event.offer_id, event.user_id)
            if was_activated:
                await send_activation_notification(nats_conn, event.user_id)
        await msg.ack()
    except Exception as e:
        offer_id = event.offer_id if event else 'N/A'
        logger.error(f"Failed to process message for offerId {offer_id}: {e}")
        await msg.nak(delay=10)
