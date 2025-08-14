import asyncio
import os
import nats
import logging
import json
import asyncpg
from datetime import datetime
from nats.js.api import StreamConfig, RetentionPolicy, DiscardPolicy
from pydantic import BaseModel, Field
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/ecsdb")
NATS_SUBJECT = "user.emotions.topic"
STREAM_NAME = "emotions"
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

async def process_message(msg, db_pool):
    try:
        payload_str = msg.data.decode()
        data = json.loads(payload_str)
        event = EmotionEvent.model_validate(data)
        
        logging.info(f"Received event for userId: {event.user_id}, traceId: {event.trace_id}")

        date_string = event.timestamp.split("T")[0]
        summary_date = datetime.strptime(date_string, "%Y-%m-%d").date()
        
        metrics = event.emotion_event.metrics
        
        query = """
        INSERT INTO emotional_events_summary (user_id, summary_date, avg_positivity_score, avg_intensity_score, avg_stress_level, event_count, updated_at)
        VALUES ($1, $2, $3, $4, $5, 1, NOW())
        ON CONFLICT (user_id, summary_date)
        DO UPDATE SET
            avg_positivity_score = (emotional_events_summary.avg_positivity_score * emotional_events_summary.event_count + EXCLUDED.avg_positivity_score) / (emotional_events_summary.event_count + 1),
            avg_intensity_score = (emotional_events_summary.avg_intensity_score * emotional_events_summary.event_count + EXCLUDED.avg_intensity_score) / (emotional_events_summary.event_count + 1),
            avg_stress_level = (emotional_events_summary.avg_stress_level * emotional_events_summary.event_count + EXCLUDED.avg_stress_level) / (emotional_events_summary.event_count + 1),
            event_count = emotional_events_summary.event_count + 1,
            updated_at = NOW();
        """
        
        async with db_pool.acquire() as conn:
            await conn.execute(
                query, 
                event.user_id, 
                summary_date,
                metrics.positivity, 
                metrics.intensity, 
                metrics.stress_level
            )
        logging.info(f"Event processed successfully for userId: {event.user_id}, traceId: {event.trace_id}")
        await msg.ack()
    except json.JSONDecodeError as e:
        logging.error(f"JSON decoding error: {e}. Message: {msg.data.decode()}")
        await msg.ack()
    except Exception as e:
        logging.error(f"Error processing message: {e}")
        await msg.nak(delay=10)

async def main():
    logging.info("Starting Emotion Processing Worker...")
    nc = None
    db_pool = None
    
    try:
        logging.info("Connecting to PostgreSQL...")
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
        logging.info("PostgreSQL connection established.")

        logging.info(f"Connecting to NATS at {NATS_URL}...")
        nc = await nats.connect(NATS_URL, name="emotion_processing_worker")
        js = nc.jetstream()
        logging.info("NATS connection established.")

        logging.info(f"Ensuring stream '{STREAM_NAME}' exists...")
        try:
            await js.add_stream(
                name=STREAM_NAME,
                subjects=[NATS_SUBJECT],
                config=StreamConfig(
                    retention=RetentionPolicy.LIMITS,
                    storage=nats.js.api.StorageType.FILE,
                    discard=DiscardPolicy.OLD,
                    duplicate_window=120,
                )
            )
            logging.info(f"Stream '{STREAM_NAME}' created.")
        except nats.js.errors.StreamNameAlreadyInUseError:
            logging.info(f"Stream '{STREAM_NAME}' already exists.")

        sub = await js.subscribe(subject=NATS_SUBJECT, queue=DURABLE_NAME)
        logging.info(f"Waiting for messages on topic '{NATS_SUBJECT}'...")
        
        async for msg in sub.messages:
            await process_message(msg, db_pool)

    except Exception as e:
        logging.critical(f"A critical error occurred, shutting down worker: {e}")
    finally:
        if nc and nc.is_connected:
            logging.info("Closing NATS connection...")
            await nc.close()
        if db_pool:
            logging.info("Closing PostgreSQL connection...")
            await db_pool.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Service manually terminated.")

