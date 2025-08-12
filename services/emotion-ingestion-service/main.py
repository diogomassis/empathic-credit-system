import os
import json
import uuid
import nats
from nats.js.api import StreamConfig, RetentionPolicy, DiscardPolicy
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status, Header, BackgroundTasks
from fastapi.responses import ORJSONResponse
from typing import Optional

from logs.log import logger
from messaging.nats import publish_to_nats
from models.emotion import EmotionEvent

STREAM_NAME = "emotions"
NATS_SUBJECT = "user.emotions.topic"
NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Connecting to NATS at {NATS_URL}...")
    try:
        nc = await nats.connect(NATS_URL, name="emotion_ingestion_service")
        js = nc.jetstream()
        app.state.nats_connection = nc
        logger.info("✅ Connected to NATS.")

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
            logger.info(f"✅ Stream '{STREAM_NAME}' created successfully.")
        except nats.js.errors.StreamNameAlreadyInUseError:
            logger.info(f"ℹ️  Stream '{STREAM_NAME}' already exists, skipping creation.")
        
        yield
    finally:
        if hasattr(app.state, 'nats_connection') and app.state.nats_connection.is_connected:
            logger.info("Closing connection to NATS...")
            await app.state.nats_connection.close()
            logger.info("Connection to NATS closed.")

app = FastAPI(
    lifespan=lifespan,
    title="Emotion Ingestion Service",
    version="1.1.0",
    default_response_class=ORJSONResponse 
)

@app.get("/healthz", status_code=status.HTTP_200_OK, tags=["Monitoring"])
async def health_check():
    return {"status": "ok"}

@app.post("/v1/emotions/stream", status_code=status.HTTP_202_ACCEPTED, tags=["Emotions"])
async def publish_emotion_event(
    event: EmotionEvent,
    request: Request,
    background_tasks: BackgroundTasks,
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID")
):
    trace_id = x_request_id or str(uuid.uuid4())
    logger.info(f"Received emotion event for user_id={event.user_id}, trace_id={trace_id}")
    try:
        nc = request.app.state.nats_connection
        payload_dict = event.model_dump(by_alias=True)
        payload_dict['traceId'] = trace_id
        payload_bytes = json.dumps(payload_dict).encode()

        background_tasks.add_task(publish_to_nats, nc, NATS_SUBJECT, payload_bytes)
        
        return {"status": "event received", "traceId": trace_id}
    except AttributeError:
        logger.error("Service unavailable. Could not connect to the messaging system.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unavailable. Could not connect to the messaging system."
        )
    except Exception as e:
        logger.exception(f"Failed to process event: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process event: {str(e)}"
        )
