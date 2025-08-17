import httpx

from pybreaker import CircuitBreaker

from configuration.config import logger, CREDIT_ANALYSIS_SERVICE_URL

ml_service_breaker = CircuitBreaker(fail_max=5, reset_timeout=30)

@ml_service_breaker
async def get_credit_analysis_from_ml_service(http_client: httpx.AsyncClient, feature_vector: dict) -> dict:
    """
    Calls the external credit analysis service to obtain a risk score.
    This function is decorated with a circuit breaker to protect against failures.
    """
    logger.info(f"Calling ML service. Circuit breaker state: {ml_service_breaker.current_state}")
    try:
        response = await http_client.post(CREDIT_ANALYSIS_SERVICE_URL, json=feature_vector)
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        logger.error(f"HTTP request error calling credit analysis service: {e}")
        raise e
