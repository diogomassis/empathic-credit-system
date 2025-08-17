from typing import List
from datetime import datetime
from pydantic import BaseModel, Field

class CreditOffer(BaseModel):
    """Represents a credit offer made to a user."""
    offer_id: str
    credit_limit: float
    interest_rate: float
    credit_type: str
    expires_at: str

class CreditAnalysisResponse(BaseModel):
    """Represents the response of a credit analysis for a user."""
    user_id: str
    approved: bool
    ml_risk_score: float
    offer: CreditOffer | None = None
    reason: str | None = None

class AcceptOfferPayload(BaseModel):
    """Represents the payload to accept a credit offer."""
    user_id: str = Field(..., alias="userId")

class CreditOfferListItem(BaseModel):
    """Represents a single item in the paginated list of credit offers."""
    offer_id: str
    status: str
    credit_limit: float
    interest_rate: float
    created_at: datetime
    expires_at: datetime

class PaginatedOffersResponse(BaseModel):
    """Represents a paginated response for a user's credit offers."""
    total: int
    page: int
    page_size: int
    items: List[CreditOfferListItem]
