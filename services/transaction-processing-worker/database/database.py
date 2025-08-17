from models.models import TransactionEvent

async def insert_transaction(db_conn, transaction: TransactionEvent):
    """
    Inserts a new transaction record into the database.
    """
    query = """
    INSERT INTO transactions (user_id, amount, created_at) VALUES ($1, $2, NOW());
    """
    await db_conn.execute(
        query, 
        transaction.user_id,
        transaction.amount
    )
