import asyncio
import os
import nats
import logging
import json
import asyncpg

from datetime import datetime
from nats.js.api import StreamConfig, RetentionPolicy, DiscardPolicy, ConsumerConfig
from nats.errors import MsgAlreadyAckdError
from pydantic import BaseModel, Field
from nats.js.errors import APIError
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ecsuser:ecspassword@localhost:5432/ecsdb")
NATS_SUBJECT = "user.emotions.topic"
STREAM_NAME = "emotions"
DURABLE_NAME = "processor"

class EmotionMetrics(BaseModel):
    """
    Represents the core emotional metrics derived from user data.

    Attributes:
        positivity (float): Positivity score ranging from 0.0 (negative) to 1.0 (positive).
        intensity (float): Intensity score representing the strength of the emotion, from 0.0 to 1.0.
        stress_level (float): Stress level score from 0.0 (no stress) to 1.0 (high stress).
    """
    positivity: float
    intensity: float
    stress_level: float

class EmotionEventPayload(BaseModel):
    """
    Represents the payload of an emotion event, including the type of analysis and associated metrics.

    Attributes:
        type (str): The type of emotional analysis performed (e.g., 'SENTIMENT_ANALYSIS').
        metrics (EmotionMetrics): The emotional metrics resulting from the analysis.
    """
    type: str
    metrics: EmotionMetrics

class EmotionEvent(BaseModel):
    """
    Represents a complete emotion event for a user, including metadata and analysis results.

    Attributes:
        user_id (str): The unique identifier for the user associated with the event.
        timestamp (str): The ISO 8601 timestamp when the event occurred.
        emotion_event (EmotionEventPayload): The payload containing analysis type and metrics.
        trace_id (Optional[str]): Optional trace ID for distributed tracing.
    """
    user_id: str = Field(..., alias="userId")
    timestamp: str
    emotion_event: EmotionEventPayload = Field(..., alias="emotionEvent")
    trace_id: Optional[str] = Field(None, alias="traceId")

async def process_message(msg, db_pool):
    """
    Processes a single emotion event message from NATS JetStream and updates the database summary.

    This function decodes the incoming message, validates its structure, and updates the emotional events summary table in PostgreSQL.
    Handles duplicate acknowledgments, JSON decoding errors, and other exceptions robustly.

    Args:
        msg: The NATS JetStream message containing the emotion event.
        db_pool: The asyncpg connection pool for PostgreSQL database operations.

    Returns:
        None
    """
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
        await msg.ack()
        logging.info(f"Event successfully processed for userId: {event.user_id}, traceId: {event.trace_id}")
    except json.JSONDecodeError as e:
        logging.error(f"JSON decoding error: {e}. Message: {msg.data.decode()}")
        await msg.ack()
    except MsgAlreadyAckdError:
        logging.warning(f"Message with traceId {data.get('traceId', 'N/A')} was already acknowledged, probably by another replica.")
    except Exception as e:
        logging.error(f"Error processing message: {e}")
        await msg.nak(delay=10)

async def main():
    """
    Main entry point for the Emotion Processing Worker service.

    Establishes connections to PostgreSQL and NATS JetStream, subscribes to emotion event topics,
    and processes incoming messages asynchronously. Handles graceful shutdown and error logging.

    Returns:
        None
    """
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

        async def message_handler(msg):
            """
            Handles incoming NATS messages by scheduling their processing asynchronously.

            Args:
                msg: The NATS JetStream message to process.

            Returns:
                None
            """
            asyncio.create_task(process_message(msg, db_pool))

        consumer_config = ConsumerConfig(
            max_ack_pending=800
        )
        _ = await js.subscribe(
            subject=NATS_SUBJECT, 
            queue=DURABLE_NAME, 
            cb=message_handler,
            config=consumer_config
        )
        logging.info(f"Waiting for messages on topic '{NATS_SUBJECT}'...")
        await asyncio.Future()
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
    """
    Script entry point. Runs the main async function and handles manual termination.
    """
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Service manually terminated.")

