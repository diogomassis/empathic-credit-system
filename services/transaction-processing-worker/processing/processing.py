import json

from pydantic import ValidationError
from configuration.config import logger
from models.models import TransactionEvent
from nats.errors import MsgAlreadyAckdError
from database.database import insert_transaction

async def process_message(msg, db_pool):
    """
    Processes a single transaction event message from NATS.
    """
    data = None
    try:
        payload_str = msg.data.decode()
        data = json.loads(payload_str)
        transaction = TransactionEvent.model_validate(data)
        logger.info(f"Received transaction for userId: {transaction.user_id}")
        async with db_pool.acquire() as conn:
            await insert_transaction(conn, transaction)
        await msg.ack()
        logger.info(f"Transaction successfully processed for userId: {transaction.user_id}")
    except (json.JSONDecodeError, ValidationError) as e:
        logger.error(f"Validation or JSON decoding error: {e}. Message: {msg.data.decode()}")
        await msg.ack()
    except MsgAlreadyAckdError:
        user_id = data.get('userId', 'N/A') if data else 'N/A'
        logger.warning(f"Message for userId {user_id} has already been acknowledged, probably by another replica.")
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await msg.nak(delay=10)
