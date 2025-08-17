import os
import json
import uuid
import nats
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status, Header, BackgroundTasks
from fastapi.responses import ORJSONResponse
from typing import Optional

from logs.log import logger
from messaging.nats import publish_to_nats
from models.transaction import TransactionPayload

NATS_SUBJECT = "transactions.topic"
NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager for managing NATS connection.

    Establishes a connection to NATS JetStream when the FastAPI app starts and ensures proper cleanup on shutdown.

    Args:
        app (FastAPI): The FastAPI application instance.

    Yields:
        None
    """
    logger.info(f"Connecting to NATS at {NATS_URL}...")
    try:
        nc = await nats.connect(NATS_URL, name="transaction_service")
        app.state.nats_connection = nc
        logger.info("Connected to NATS.")
        yield
    finally:
        if hasattr(app.state, 'nats_connection') and app.state.nats_connection.is_connected:
            logger.info("Closing connection to NATS...")
            await app.state.nats_connection.close()
            logger.info("Connection to NATS closed.")

app = FastAPI(
    lifespan=lifespan,
    title="Transaction Service",
    version="1.0.0",
    default_response_class=ORJSONResponse 
)

@app.get("/healthz", status_code=status.HTTP_200_OK, tags=["Monitoring"])
async def health_check():
    """
    Health check endpoint for monitoring service status.

    Returns:
        dict: A dictionary containing the status of the service.
    """
    return {"status": "ok"}

@app.post("/v1/transactions", status_code=status.HTTP_202_ACCEPTED, tags=["Transactions"])
async def create_transaction(transaction: TransactionPayload, request: Request, background_tasks: BackgroundTasks):
    """
    Publishes a transaction event to NATS JetStream asynchronously.

    This endpoint receives a transaction payload, schedules the event for background publishing to NATS,
    and returns a status response. Handles connection errors and logs all relevant actions for observability.

    Args:
        transaction (TransactionPayload): The transaction event payload to be published.
        request (Request): The FastAPI request object, used to access app state.
        background_tasks (BackgroundTasks): FastAPI background task manager for asynchronous publishing.

    Returns:
        dict: Status and userId of the received event.

    Raises:
        HTTPException: 503 if messaging system is unavailable, 500 for other errors.
    """
    logger.info(f"Received emotion event for userId={transaction.userId}")
    try:
        nc = request.app.state.nats_connection
        payload_dict = transaction.model_dump(by_alias=True)
        payload_bytes = json.dumps(payload_dict).encode()

        background_tasks.add_task(publish_to_nats, nc, NATS_SUBJECT, payload_bytes)
        
        return {"status": "event received", "userId": transaction.userId}
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
