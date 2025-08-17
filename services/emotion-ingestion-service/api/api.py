import json
import uuid

from typing import Optional
from models.models import EmotionEvent
from messaging.messaging import publish_to_nats
from configuration.config import logger, NATS_SUBJECT
from fastapi import APIRouter, Request, status, Header, BackgroundTasks, HTTPException

router = APIRouter()

@router.get("/healthz", status_code=status.HTTP_200_OK, tags=["Monitoring"])
async def health_check():
    """
    Health check endpoint to monitor the service status.
    """
    return {"status": "ok"}

@router.post("/v1/emotions/stream", status_code=status.HTTP_202_ACCEPTED, tags=["Emotions"])
async def publish_emotion_event(
    event: EmotionEvent,
    request: Request,
    background_tasks: BackgroundTasks,
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID")
):
    """
    Publishes a user emotion event to NATS JetStream asynchronously.
    """
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
