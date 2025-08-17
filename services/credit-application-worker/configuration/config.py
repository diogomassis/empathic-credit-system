import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("credit_application_worker")

NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")
NATS_CONSUME_SUBJECT = "credit.offers.approved"
NATS_NOTIFY_SUBJECT = "user.notifications"
DURABLE_NAME = "processor"

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ecsuser:ecspassword@localhost:5432/ecsdb")
