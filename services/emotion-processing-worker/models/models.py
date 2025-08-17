from typing import Optional
from pydantic import BaseModel, Field

class EmotionMetrics(BaseModel):
    """
    Represents the main emotional metrics derived from user data.
    """
    positivity: float
    intensity: float
    stress_level: float

class EmotionEventPayload(BaseModel):
    """
    Represents the payload of an emotion event.
    """
    type: str
    metrics: EmotionMetrics

class EmotionEvent(BaseModel):
    """
    Represents a complete emotion event for a user.
    """
    user_id: str = Field(..., alias="userId")
    timestamp: str
    emotion_event: EmotionEventPayload = Field(..., alias="emotionEvent")
    trace_id: Optional[str] = Field(None, alias="traceId")
