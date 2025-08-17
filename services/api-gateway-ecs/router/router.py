import httpx

from configuration.config import SERVICE_URLS, logger
from fastapi import APIRouter, Request, Response, Depends, HTTPException
from security.security import validate_api_key, validate_internal_api_key

router = APIRouter()
http_client = httpx.AsyncClient()

async def forward(service_name: str, path: str, request: Request):
    """Generic function to forward a request to an internal service."""
    if not service_name or service_name not in SERVICE_URLS:
        raise HTTPException(status_code=404, detail="Endpoint not found.")

    downstream_url = f"{SERVICE_URLS[service_name]}/{path}"
    headers = dict(request.headers)
    headers["host"] = httpx.URL(downstream_url).host
    body = await request.body()

    try:
        response = await http_client.request(
            method=request.method,
            url=downstream_url,
            headers=headers,
            params=request.query_params,
            content=body,
            timeout=10.0
        )
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers)
        )
    except httpx.RequestError as e:
        logger.error(f"Could not connect to service {service_name}: {e}")
        raise HTTPException(status_code=503, detail=f"Service '{service_name}' unavailable.")

@router.get("/healthz")
async def health_check():
    """
    Health check endpoint for the API Gateway.
    """
    return {"status": "ok"}

@router.post("/v1/emotions/stream")
async def forward_emotion_request(request: Request, _=Depends(validate_internal_api_key)):
    """
    Forwards requests to the emotions service, requiring an internal API key.
    """
    return await forward("emotion_service", "v1/emotions/stream", request)

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def forward_user_request(request: Request, path: str, _=Depends(validate_api_key)):
    """
    Forwards all other requests, requiring a user API key.
    """
    PATH_TO_SERVICE_MAP = {
        "/v1/transactions": "transaction_service",
        "/v1/users": "user_credit_service",
        "/v1/credit-offers": "user_credit_service",
    }

    service_name = None
    full_path = f"/{path}"

    for prefix, name in PATH_TO_SERVICE_MAP.items():
        if full_path.startswith(prefix):
            service_name = name
            break
    
    return await forward(service_name, path, request)
