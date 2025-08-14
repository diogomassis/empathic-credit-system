import asyncio
import os
import nats
import logging
import json

from pydantic import BaseModel, Field
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")
NATS_SUBJECT = "user.emotions.topic"
DURABLE_NAME = "processor" 

class EmotionMetrics(BaseModel):
    positivity: float
    intensity: float
    stress_level: float

class EmotionEventPayload(BaseModel):
    type: str
    metrics: EmotionMetrics

class EmotionEvent(BaseModel):
    user_id: str = Field(..., alias="userId")
    timestamp: str
    emotion_event: EmotionEventPayload = Field(..., alias="emotionEvent")
    trace_id: Optional[str] = Field(None, alias="traceId")

async def main():
    logging.info(f"Connecting to NATS at {NATS_URL}...")
    nc = None
    try:
        nc = await nats.connect(NATS_URL, name="emotion_processing_worker")
        js = nc.jetstream()
        logging.info("Connection to NATS established.")
        sub = await js.subscribe(
            subject=NATS_SUBJECT,
            durable=DURABLE_NAME
        )
        logging.info(f"Waiting for messages on topic '{NATS_SUBJECT}'...")
        async for msg in sub.messages:
            try:
                payload_str = msg.data.decode()
                data = json.loads(payload_str)
                event = EmotionEvent.model_validate(data)
                logging.info(f"Received and deserialized event for userId: {event.user_id} with traceId: {event.trace_id}")               
                await msg.ack()
            except json.JSONDecodeError as e:
                logging.error(f"Error decoding JSON: {e}. Message: {msg.data.decode()}")
            except Exception as e:
                logging.error(f"Error processing message: {e}")

    except Exception as e:
        logging.critical(f"A critical error occurred: {e}")
    finally:
        if nc and nc.is_connected:
            logging.info("Closing connection to NATS...")
            await nc.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Service terminated.")
