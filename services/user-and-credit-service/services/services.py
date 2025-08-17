import httpx

from configuration.config import logger, CREDIT_ANALYSIS_SERVICE_URL

async def get_credit_analysis_from_ml_service(http_client: httpx.AsyncClient, feature_vector: dict) -> dict:
    """
    Calls the external credit analysis service to obtain a risk score.
    """
    try:
        response = await http_client.post(CREDIT_ANALYSIS_SERVICE_URL, json=feature_vector)
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        logger.error(f"HTTP error when calling the credit analysis service: {e}")
        return None
