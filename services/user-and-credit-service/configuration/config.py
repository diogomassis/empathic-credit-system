import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("user_credit_service")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ecsuser:ecspassword@localhost:5432/ecsdb")

CREDIT_ANALYSIS_SERVICE_URL = os.getenv("CREDIT_ANALYSIS_SERVICE_URL", "http://credit-analysis-service:8000/v1/predict")

NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")
NATS_ACCEPT_SUBJECT = "credit.offers.approved"
