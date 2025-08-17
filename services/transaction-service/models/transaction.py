from pydantic import BaseModel, Field
from typing import Optional

class TransactionPayload(BaseModel):
    """
    Represents the payload for a transaction event in the transaction service.

    Attributes:
        userId (str): The unique identifier for the user associated with the transaction.
        amount (float): The transaction amount, must be greater than zero.
    """
    userId: str = Field(..., alias="userId")
    amount: float = Field(..., gt=0)
