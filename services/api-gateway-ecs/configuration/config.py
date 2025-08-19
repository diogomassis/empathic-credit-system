import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("api_gateway")

SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-and-long-api-token")
INTERNAL_SERVICE_API_KEY = os.getenv("INTERNAL_SERVICE_API_KEY", "a-different-secret-for-internal-services")

SERVICE_URLS = {
    "emotion_service": os.getenv("EMOTION_SERVICE_URL", "http://emotion-ingestion-service:8000"),
    "transaction_service": os.getenv("TRANSACTION_SERVICE_URL", "http://transaction-service:8000"),
    "user_credit_service": os.getenv("USER_CREDIT_SERVICE_URL", "http://user-and-credit-service:8000"),
}
