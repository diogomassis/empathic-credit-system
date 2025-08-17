from pydantic import BaseModel, Field

class EmotionMetrics(BaseModel):
    """
    Represents the core emotional metrics derived from user data.

    Attributes:
        positivity (float): Positivity score ranging from 0.0 (negative) to 1.0 (positive).
        intensity (float): Intensity score representing the strength of the emotion, from 0.0 to 1.0.
        stress_level (float): Stress level score from 0.0 (no stress) to 1.0 (high stress).
    """
    positivity: float = Field(..., ge=0.0, le=1.0, description="Positivity score from 0.0 to 1.0.")
    intensity: float = Field(..., ge=0.0, le=1.0, description="Intensity score from 0.0 to 1.0.")
    stress_level: float = Field(..., ge=0.0, le=1.0, description="Stress level from 0.0 to 1.0.")

class EmotionEventPayload(BaseModel):
    """
    Represents the payload of an emotion event, including the type of analysis and associated metrics.

    Attributes:
        type (str): The type of emotional analysis performed (e.g., 'SENTIMENT_ANALYSIS').
        metrics (EmotionMetrics): The emotional metrics resulting from the analysis.
    """
    type: str = Field(..., description="The type of analysis performed, e.g., 'SENTIMENT_ANALYSIS'.")
    metrics: EmotionMetrics

class EmotionEvent(BaseModel):
    """
    Represents a complete emotion event for a user, including metadata and analysis results.

    Attributes:
        user_id (str): The unique identifier for the user associated with the event.
        timestamp (str): The ISO 8601 timestamp when the event occurred.
        emotion_event (EmotionEventPayload): The payload containing analysis type and metrics.
    """
    user_id: str = Field(..., alias="userId", description="The unique identifier for the user.")
    timestamp: str = Field(..., description="The ISO 8601 timestamp of the event.")
    emotion_event: EmotionEventPayload = Field(..., alias="emotionEvent")
