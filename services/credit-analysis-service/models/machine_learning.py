
from pydantic import BaseModel, Field

class FeatureVector(BaseModel):
    transaction_count_30d: int = Field(..., description="Total number of transactions in the last 30 days.")
    avg_transaction_value_30d: float = Field(..., description="Average transaction value in the last 30 days.")
    avg_positivity_7d: float = Field(..., description="Average positivity score from emotional data in the last 7 days.")
    stress_events_30d: int = Field(..., description="Number of detected high-stress events in the last 30 days.")

class PredictionResponse(BaseModel):
    risk_score: float = Field(..., description="The calculated credit risk score, from 0.0 (low risk) to 1.0 (high risk).")
