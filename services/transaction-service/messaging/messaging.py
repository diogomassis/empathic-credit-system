import nats

from configuration.config import logger

async def publish_to_nats(nc: nats.aio.client.Client, subject: str, payload: bytes):
    """
    Publishes a message to a NATS JetStream topic asynchronously.
    """
    try:
        js = nc.jetstream()
        await js.publish(subject, payload)
        logger.info(f"Background task: Event published to NATS topic '{subject}'")
    except Exception as e:
        logger.error(f"Background task error: Failed to publish to NATS. Error: {e}")
