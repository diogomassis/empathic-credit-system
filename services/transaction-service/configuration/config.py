import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("transaction_service")

NATS_SUBJECT = "transactions.topic"
NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")
