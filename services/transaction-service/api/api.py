import json

from models.models import TransactionPayload
from messaging.messaging import publish_to_nats
from configuration.config import logger, NATS_SUBJECT
from fastapi import APIRouter, Request, status, BackgroundTasks, HTTPException

router = APIRouter()

@router.get("/healthz", status_code=status.HTTP_200_OK, tags=["Monitoring"])
async def health_check():
    """
    Health check endpoint to monitor the service status.
    """
    return {"status": "ok"}

@router.post("/v1/transactions", status_code=status.HTTP_202_ACCEPTED, tags=["Transactions"])
async def create_transaction(
    transaction: TransactionPayload,
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Publishes a transaction event to NATS JetStream asynchronously.
    """
    logger.info(f"Received transaction for userId={transaction.userId}")
    try:
        nc = request.app.state.nats_connection
        payload_dict = transaction.model_dump(by_alias=True)
        payload_bytes = json.dumps(payload_dict).encode()

        background_tasks.add_task(publish_to_nats, nc, NATS_SUBJECT, payload_bytes)
        
        return {"status": "event received", "userId": transaction.userId}
    except AttributeError:
        logger.error("Service unavailable. Could not connect to messaging system.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unavailable. Could not connect to messaging system."
        )
    except Exception as e:
        logger.exception(f"Failed to process event: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process event: {str(e)}"
        )
