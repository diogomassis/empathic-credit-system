from pydantic import BaseModel, Field

class EmotionMetrics(BaseModel):
    """
    Represents the main emotional metrics derived from user data.
    """
    positivity: float = Field(..., ge=0.0, le=1.0, description="Positivity score from 0.0 to 1.0.")
    intensity: float = Field(..., ge=0.0, le=1.0, description="Intensity score from 0.0 to 1.0.")
    stress_level: float = Field(..., ge=0.0, le=1.0, description="Stress level from 0.0 to 1.0.")

class EmotionEventPayload(BaseModel):
    """
    Represents the payload of an emotion event.
    """
    type: str = Field(..., description="The type of analysis performed, e.g., 'SENTIMENT_ANALYSIS'.")
    metrics: EmotionMetrics

class EmotionEvent(BaseModel):
    """
    Represents a complete emotion event for a user.
    """
    user_id: str = Field(..., alias="userId", description="The unique identifier for the user.")
    timestamp: str = Field(..., description="The ISO 8601 timestamp of the event.")
    emotion_event: EmotionEventPayload = Field(..., alias="emotionEvent")
