import os
import json
import uuid
import nats
import logging
from nats.js.api import StreamConfig, RetentionPolicy, DiscardPolicy
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status, Header
from pydantic import BaseModel, Field
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("emotion_ingestion_service")

STREAM_NAME = "emotions"
NATS_SUBJECT = "user.emotions.topic"
NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")

class EmotionMetrics(BaseModel):
    positivity: float = Field(..., ge=0.0, le=1.0, description="Positivity score from 0.0 to 1.0.")
    intensity: float = Field(..., ge=0.0, le=1.0, description="Intensity score from 0.0 to 1.0.")
    stress_level: float = Field(..., ge=0.0, le=1.0, description="Stress level from 0.0 to 1.0.")

class EmotionEventPayload(BaseModel):
    type: str = Field(..., description="The type of analysis performed, e.g., 'SENTIMENT_ANALYSIS'.")
    metrics: EmotionMetrics

class EmotionEvent(BaseModel):
    user_id: str = Field(..., alias="userId", description="The unique identifier for the user.")
    timestamp: str = Field(..., description="The ISO 8601 timestamp of the event.")
    emotion_event: EmotionEventPayload = Field(..., alias="emotionEvent")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Connecting to NATS at {NATS_URL}...")
    try:
        nc = await nats.connect(NATS_URL, name="emotion_ingestion_service")
        js = nc.jetstream()
        app.state.nats_connection = nc
        logger.info("Connected to NATS.")

        stream_config = StreamConfig(
            name=STREAM_NAME,
            subjects=[NATS_SUBJECT],
            retention=RetentionPolicy.LIMITS,
            storage=nats.js.api.StorageType.FILE,
            discard=DiscardPolicy.OLD,
            duplicate_window=120,
        )
        logger.info(f"Ensuring stream '{STREAM_NAME}' exists...")
        try:
            await js.add_stream(stream_config)
            logger.info(f"Stream '{STREAM_NAME}' created successfully.")
        except nats.js.errors.StreamNameAlreadyInUseError:
            logger.info(f"Stream '{STREAM_NAME}' already exists, skipping creation.")
        yield

    finally:
        if hasattr(app.state, 'nats_connection') and app.state.nats_connection.is_connected:
            logger.info("Closing NATS connection...")
            await app.state.nats_connection.close()
            logger.info("NATS connection closed.")

app = FastAPI(
    lifespan=lifespan,
    title="Emotion Ingestion Service",
    version="1.1.0"
)

@app.get("/healthz", status_code=status.HTTP_200_OK, tags=["Monitoring"])
async def health_check():
    logger.debug("Health check endpoint called.")
    return {"status": "ok"}

@app.post("/v1/emotions/stream", status_code=status.HTTP_202_ACCEPTED, tags=["Emotions"])
async def publish_emotion_event(
    event: EmotionEvent,
    request: Request,
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID")
):
    trace_id = x_request_id or str(uuid.uuid4())
    logger.info(f"Received emotion event for user_id={event.user_id}, trace_id={trace_id}")
    try:
        nc = request.app.state.nats_connection
        js = nc.jetstream()

        payload_dict = event.model_dump(by_alias=True)
        payload_dict['traceId'] = trace_id
        payload_bytes = json.dumps(payload_dict).encode()
        await js.publish(NATS_SUBJECT, payload_bytes)
        logger.info(f"Published event to NATS subject '{NATS_SUBJECT}' with trace_id={trace_id}")
        return {"status": "event received", "traceId": trace_id}
    except AttributeError:
        logger.error("Service unavailable. Could not connect to the messaging system.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unavailable. Could not connect to the messaging system."
        )
    except Exception as e:
        logger.exception(f"Failed to publish event: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to publish event: {str(e)}"
        )
