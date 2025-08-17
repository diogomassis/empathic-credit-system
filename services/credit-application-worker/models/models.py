import uuid

from pydantic import BaseModel, Field

class CreditOfferAcceptedEvent(BaseModel):
    """
    Represents an event indicating that a credit offer has been accepted by a user.
    """
    offer_id: uuid.UUID = Field(..., alias="offerId")
    user_id: uuid.UUID = Field(..., alias="userId")
    accepted_at: str = Field(..., alias="acceptedAt")
