import json

from pydantic import ValidationError
from models.models import EmotionEvent
from configuration.config import logger
from nats.errors import MsgAlreadyAckdError
from database.database import update_emotional_summary

async def process_message(msg, db_pool):
    """
    Processes a single emotion event message from NATS.
    """
    data = None
    try:
        payload_str = msg.data.decode()
        data = json.loads(payload_str)
        event = EmotionEvent.model_validate(data)
        
        logger.info(f"Received event for userId: {event.user_id}, traceId: {event.trace_id}")

        async with db_pool.acquire() as conn:
            await update_emotional_summary(conn, event)
        
        await msg.ack()
        logger.info(f"Event successfully processed for userId: {event.user_id}, traceId: {event.trace_id}")

    except (json.JSONDecodeError, ValidationError) as e:
        logger.error(f"Validation or JSON decoding error: {e}. Message: {msg.data.decode()}")
        await msg.ack()

    except MsgAlreadyAckdError:
        trace_id = data.get('traceId', 'N/A') if data else 'N/A'
        logger.warning(f"Message with traceId {trace_id} has already been acknowledged, probably by another replica.")

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await msg.nak(delay=10)
