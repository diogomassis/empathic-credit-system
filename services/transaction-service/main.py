import os
import logging
import aio_pika

from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Request, status, BackgroundTasks
from contextlib import asynccontextmanager

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

async def publish_to_rabbitmq(channel: aio_pika.Channel, routing_key: str, message_body: bytes):
    try:
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=message_body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=routing_key
        )
        logging.info(f"Background task: Transaction published to queue '{routing_key}'")
    except Exception as e:
        logging.error(f"Background task error: Failed to publish to RabbitMQ. Error: {e}")

@app.get("/healthz", status_code=status.HTTP_200_OK, tags=["Monitoring"])
async def health_check():
    return {"status": "ok"}

@app.post("/v1/transactions", status_code=status.HTTP_202_ACCEPTED, tags=["Transactions"])
async def create_transaction(transaction: TransactionPayload, request: Request, background_tasks: BackgroundTasks):
    logging.info(f"Received transaction for userId: {transaction.userId}")
    try:
        channel = request.app.state.rabbitmq_channel
        message_body = transaction.model_dump_json().encode()
        background_tasks.add_task(publish_to_rabbitmq, channel, TRANSACTION_QUEUE, message_body)
        return {"status": "transaction received"}
    except Exception as e:
        logging.error(f"Failed to schedule transaction publishing: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The service is temporarily unavailable."
        )
