import json
import uuid

from configuration.config import logger, NATS_NOTIFY_SUBJECT

async def send_activation_notification(nats_conn, user_id: uuid.UUID):
    """
    Publishes a credit activation notification for the user to NATS.

    Args:
        nats_conn: The active NATS connection.
        user_id: The ID of the user to be notified.
    """
    notification_payload = {
        "userId": str(user_id),
        "type": "CREDIT_LIMIT_APPLIED",
        "title": "Credit Limit Active!",
        "message": "Your new credit limit is now available for use."
    }
    await nats_conn.publish(NATS_NOTIFY_SUBJECT, json.dumps(notification_payload).encode())
    logger.info(f"Notification event for user {user_id} published to '{NATS_NOTIFY_SUBJECT}'.")
