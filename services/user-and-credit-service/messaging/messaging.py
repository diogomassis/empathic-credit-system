import json
import nats

from datetime import datetime
from configuration.config import logger, NATS_ACCEPT_SUBJECT

async def publish_offer_acceptance_event(nats_conn: nats.aio.client.Client, offer_data):
    """
    Publishes an offer acceptance event to NATS.
    """
    event_data = {
        "offerId": str(offer_data['id']),
        "userId": str(offer_data['user_id']),
        "creditLimit": float(offer_data['credit_limit']),
        "interestRate": offer_data['interest_rate'],
        "creditType": offer_data['credit_type'],
        "acceptedAt": datetime.utcnow().isoformat()
    }
    await nats_conn.publish(NATS_ACCEPT_SUBJECT, json.dumps(event_data).encode())
    logger.info(f"Acceptance event for offer {offer_data['id']} published to NATS topic '{NATS_ACCEPT_SUBJECT}'")
