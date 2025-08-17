
from pydantic import BaseModel, Field

class FeatureVector(BaseModel):
    """
    Represents the set of features used for credit risk prediction in the empathic credit system.

    Attributes:
        transaction_count_30d (int): Total number of transactions performed by the user in the last 30 days.
        avg_transaction_value_30d (float): Average value of transactions in the last 30 days.
        avg_positivity_7d (float): Average positivity score derived from emotional data in the last 7 days.
        stress_events_30d (int): Number of high-stress events detected in the last 30 days.
    """
    transaction_count_30d: int = Field(..., description="Total number of transactions in the last 30 days.")
    avg_transaction_value_30d: float = Field(..., description="Average transaction value in the last 30 days.")
    avg_positivity_7d: float = Field(..., description="Average positivity score from emotional data in the last 7 days.")
    stress_events_30d: int = Field(..., description="Number of detected high-stress events in the last 30 days.")

class PredictionResponse(BaseModel):
    """
    Represents the response of the credit risk prediction model.

    Attributes:
        risk_score (float): The calculated credit risk score, ranging from 0.0 (low risk) to 1.0 (high risk).
    """
    risk_score: float = Field(..., description="The calculated credit risk score, from 0.0 (low risk) to 1.0 (high risk).")
