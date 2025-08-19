from jose import JWTError, jwt
from fastapi import Security, HTTPException, status
from configuration.config import SECRET_KEY, INTERNAL_SERVICE_API_KEY
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

internal_api_key_header = APIKeyHeader(name="X-Internal-Key", auto_error=False)

bearer_scheme = HTTPBearer(auto_error=False)

async def validate_api_key(credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)):
    """Validates the JWT Bearer token for external clients."""
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authorization header."
        )
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token."
        )
    return payload

async def validate_internal_api_key(internal_api_key: str = Security(internal_api_key_header)):
    """Validates the API token for internal communication between services."""
    if not internal_api_key or internal_api_key != INTERNAL_SERVICE_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing internal API key."
        )
    return internal_api_key
