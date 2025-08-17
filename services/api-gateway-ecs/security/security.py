from fastapi.security import APIKeyHeader
from fastapi import Security, HTTPException, status
from configuration.config import API_SECRET_TOKEN, INTERNAL_SERVICE_API_KEY

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
internal_api_key_header = APIKeyHeader(name="X-Internal-Key", auto_error=False)

async def validate_api_key(api_key: str = Security(api_key_header)):
    """Validates the API token for external clients."""
    if not api_key or api_key != API_SECRET_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key."
        )
    return api_key

async def validate_internal_api_key(internal_api_key: str = Security(internal_api_key_header)):
    """Validates the API token for internal communication between services."""
    if not internal_api_key or internal_api_key != INTERNAL_SERVICE_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing internal API key."
        )
    return internal_api_key
