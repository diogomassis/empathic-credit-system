import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("emotion_ingestion_service")

NATS_SUBJECT = "user.emotions.topic"
NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")
