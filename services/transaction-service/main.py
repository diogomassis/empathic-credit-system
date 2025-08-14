import os
import json
import logging
import aio_pika

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost/")
TRANSACTION_QUEUE = "transactions_queue"

class TransactionPayload(BaseModel):
    userId: str = Field(..., alias="userId")
    amount: float = Field(..., gt=0)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Connecting to RabbitMQ...")
    try:
        connection = await aio_pika.connect_robust(RABBITMQ_URL)
        channel = await connection.channel()
        await channel.declare_queue(TRANSACTION_QUEUE, durable=True)
        app.state.rabbitmq_connection = connection
        app.state.rabbitmq_channel = channel
        logging.info("RabbitMQ connection established.")
        yield
    finally:
        if hasattr(app.state, 'rabbitmq_connection'):
            logging.info("Closing RabbitMQ connection...")
            await app.state.rabbitmq_connection.close()
            logging.info("RabbitMQ connection closed.")

app = FastAPI(
    lifespan=lifespan,
    title="Transaction Service",
    version="1.0.0"
)

@app.get("/healthz", status_code=status.HTTP_200_OK, tags=["Monitoring"])
async def health_check():
    return {"status": "ok"}

@app.post("/v1/transactions", status_code=status.HTTP_202_ACCEPTED, tags=["Transactions"])
async def create_transaction(transaction: TransactionPayload, request: Request):
    logging.info(f"Received transaction for userId: {transaction.user_id}")
    try:
        channel = request.app.state.rabbitmq_channel
        message_body = transaction.model_dump_json().encode()
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=message_body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=TRANSACTION_QUEUE
        )
        logging.info(f"Transaction for userId: {transaction.user_id} published to queue '{TRANSACTION_QUEUE}'")
        return {"status": "transaction received"}
    except Exception as e:
        logging.error(f"Failed to publish transaction to RabbitMQ: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service is temporarily unavailable."
        )
