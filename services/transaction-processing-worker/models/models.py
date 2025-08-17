from pydantic import BaseModel, Field

class TransactionEvent(BaseModel):
    """
    Represents a transaction event received from NATS JetStream.
    """
    user_id: str = Field(..., alias="userId")
    amount: float
