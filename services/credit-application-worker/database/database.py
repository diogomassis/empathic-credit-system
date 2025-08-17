import uuid

from configuration.config import logger

async def activate_credit_offer(db_conn, offer_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """
    Updates the status of a credit offer to 'active' in the database.

    Args:
        db_conn: An active asyncpg pool connection.
        offer_id: The ID of the offer to be activated.
        user_id: The ID of the user associated with the offer.

    Returns:
        True if the offer was successfully activated, False otherwise.
    """
    update_query = """
    UPDATE credit_limits
    SET status = 'active', activated_at = NOW(), updated_at = NOW()
    WHERE id = $1 AND user_id = $2 AND status = 'offered';
    """
    result = await db_conn.execute(update_query, offer_id, user_id)
    
    if result.strip() == "UPDATE 1":
        logger.info(f"Offer {offer_id} successfully activated for user {user_id} in the database.")
        return True
    
    logger.warning(f"Offer {offer_id} for user {user_id} was not in a valid state to be activated.")
    return False
