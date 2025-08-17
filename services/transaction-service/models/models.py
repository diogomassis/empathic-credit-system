from pydantic import BaseModel, Field

class TransactionPayload(BaseModel):
    """
    Represents the payload for a transaction event in the transaction service.
    """
    userId: str = Field(..., alias="userId")
    amount: float = Field(..., gt=0)
