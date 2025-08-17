import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("emotion_processing_worker")

NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")
NATS_SUBJECT = "user.emotions.topic"
STREAM_NAME = "emotions"
DURABLE_NAME = "processor"

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ecsuser:ecspassword@localhost:5432/ecsdb")
