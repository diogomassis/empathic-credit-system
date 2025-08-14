from pydantic import BaseModel, Field
from typing import Optional

class TransactionPayload(BaseModel):
    userId: str = Field(..., alias="userId")
    amount: float = Field(..., gt=0)
