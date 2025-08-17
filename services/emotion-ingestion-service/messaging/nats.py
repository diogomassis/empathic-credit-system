import nats
from logs.log import logger

async def publish_to_nats(nc: nats.aio.client.Client, subject: str, payload: bytes):
    """
    Publishes a message to a specified NATS JetStream subject asynchronously.

    This function sends the provided payload to the given subject using the JetStream API. It logs success and error events for monitoring purposes.

    Args:
        nc (nats.aio.client.Client): An active NATS client connection.
        subject (str): The NATS subject (topic) to publish the message to.
        payload (bytes): The message payload to be published.

    Returns:
        None

    Raises:
        Logs errors if publishing fails, but does not propagate exceptions.
    """
    try:
        js = nc.jetstream()
        await js.publish(subject, payload)
        logger.info(f"Background task: Event published to NATS topic '{subject}'")
    except Exception as e:
        logger.error(f"Background task error: Failed to publish to NATS. Error: {e}")
