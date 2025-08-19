import jwt
import uuid
import json
import httpx

from datetime import datetime, timedelta
from passlib.context import CryptContext
from pybreaker import CircuitBreakerError
from dtos.dtos import UserCreateDTO, UserDTO
from configuration.config import logger, SECRET_KEY
from messaging.messaging import publish_offer_acceptance_event
from services.services import get_credit_analysis_from_ml_service
from fastapi import APIRouter, Request, status, Query, HTTPException
from models.models import CreditAnalysisResponse, AcceptOfferPayload, PaginatedOffersResponse, CreditOffer, CreditOfferListItem
from database.database import fetch_paginated_offers, get_user_features, save_credit_offer, validate_offer_for_acceptance, insert_user, find_user_by_email

router = APIRouter()

@router.get("/healthz", status_code=status.HTTP_200_OK, tags=["Monitoring"])
async def health_check():
    return {"status": "ok"}

@router.post("/v1/users/{user_id}/credit-analysis", response_model=CreditAnalysisResponse, tags=["Credit Analysis"])
async def analyze_credit(user_id: str, request: Request):
    logger.info(f"Starting credit analysis for user_id={user_id}")

    redis_client = request.app.state.redis_client
    cache_key = f"user_features:{user_id}"
    feature_vector = None
    try:
        cached_features = await redis_client.get(cache_key)
        if cached_features:
            logger.info(f"Cache HIT for user_id={user_id}")
            feature_vector = json.loads(cached_features)
        else:
            logger.info(f"Cache MISS for user_id={user_id}")
            async with request.app.state.db_pool.acquire() as conn:
                feature_vector = await get_user_features(conn, user_id)
            await redis_client.setex(cache_key, 300, json.dumps(feature_vector))
    except Exception as e:
        logger.error(f"Redis error for user_id={user_id}: {e}. Falling back to database.")
        async with request.app.state.db_pool.acquire() as conn:
            feature_vector = await get_user_features(conn, user_id)
    try:
        ml_cache_key = f"ml_result:{user_id}"
        cached_ml_result = await redis_client.get(ml_cache_key)
        if cached_ml_result:
            logger.info(f"Cache HIT for ML result for user_id={user_id}")
            ml_result = json.loads(cached_ml_result)
        else:
            logger.info(f"Cache MISS for ML result for user_id={user_id}")
            ml_result = await get_credit_analysis_from_ml_service(request.app.state.http_client, feature_vector)
            await redis_client.setex(ml_cache_key, 300, json.dumps(ml_result))
        risk_score = ml_result.get("risk_score")
    except CircuitBreakerError:
        logger.error("Circuit breaker is open. Failing fast for ML service call.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Credit analysis service is temporarily overloaded. Please try again later."
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Credit analysis service is unavailable."
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred calling the ML service: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal error occurred during credit analysis.")
    if risk_score is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid response from analysis service.")
    if risk_score > 0.6:
        logger.info(f"Analysis denied for user_id={user_id} with score={risk_score}")
        return CreditAnalysisResponse(user_id=user_id, approved=False, ml_risk_score=risk_score, reason="High risk score.")
    
    offer_id = uuid.uuid4()
    credit_limit = round(max(1000, (1 - risk_score) * 10000), 2)
    interest_rate = round(5.0 + (risk_score * 15), 2)
    expires_at = datetime.utcnow() + timedelta(days=7)
    
    offer_details = {
        "id": offer_id, "user_id": user_id, "credit_limit": credit_limit, 
        "interest_rate": interest_rate, "credit_type": "SHORT_TERM_PERSONAL_LOAN", "expires_at": expires_at
    }
    
    async with request.app.state.db_pool.acquire() as conn:
        await save_credit_offer(conn, offer_details)
    
    logger.info(f"Offer {offer_id} saved in database for user_id={user_id}")
    return CreditAnalysisResponse(
        user_id=user_id, approved=True, ml_risk_score=risk_score,
        offer=CreditOffer(
            offer_id=str(offer_id), credit_limit=credit_limit, interest_rate=interest_rate,
            credit_type=offer_details['credit_type'], expires_at=expires_at.isoformat()
        )
    )

@router.post("/v1/credit-offers/{offer_id}/accept", status_code=status.HTTP_202_ACCEPTED, tags=["Credit Analysis"])
async def accept_credit_offer(offer_id: str, payload: AcceptOfferPayload, request: Request):
    logger.info(f"User {payload.user_id} attempting to accept offer {offer_id}")
    async with request.app.state.db_pool.acquire() as conn:
        offer_data = await validate_offer_for_acceptance(conn, offer_id, payload.user_id)
    if not offer_data:
        logger.warning(f"Attempt to accept invalid or expired offer {offer_id} by user {payload.user_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found, expired or already processed.")
    await publish_offer_acceptance_event(request.app.state.nats_conn, offer_data)
    return {"status": "offer acceptance is being processed"}

@router.get("/v1/users/{user_id}/offers", response_model=PaginatedOffersResponse, tags=["Credit Offers"])
async def get_user_offers(
    user_id: str,
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page")
):
    logger.info(f"Fetching offers for user_id={user_id}, page={page}, page_size={page_size}")
    offset = (page - 1) * page_size
    async with request.app.state.db_pool.acquire() as conn:
        total_count, records = await fetch_paginated_offers(conn, user_id, page_size, offset)
    items = [
        CreditOfferListItem(
            offer_id=str(r['id']), status=r['status'], credit_limit=r['credit_limit'],
            interest_rate=r['interest_rate'], created_at=r['created_at'], expires_at=r['expires_at']
        ) for r in records
    ]
    return PaginatedOffersResponse(total=total_count, page=page, page_size=page_size, items=items)


auth_router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@auth_router.post("/v1/register", response_model=UserDTO, tags=["Auth"])
async def register_user(payload: UserCreateDTO, request: Request):
    logger.info(f"Attempting to register user: {payload.email}")
    redis_client = request.app.state.redis_client
    cache_key = f"user_email:{payload.email}"
    existing_user = None
    try:
        cached_user = await redis_client.get(cache_key)
        if cached_user:
            logger.info(f"Cache HIT for email={payload.email}")
            existing_user = json.loads(cached_user)
        else:
            logger.info(f"Cache MISS for email={payload.email}")
            async with request.app.state.db_pool.acquire() as conn:
                existing_user = await find_user_by_email(conn, payload.email)
            if existing_user:
                user_dict_for_cache = {k: str(v) if isinstance(v, (uuid.UUID, datetime)) else v for k, v in dict(existing_user).items()}
                await redis_client.setex(cache_key, 300, json.dumps(user_dict_for_cache))
    except Exception as e:
        logger.error(f"Redis error for email={payload.email}: {e}. Falling back to database.")
        async with request.app.state.db_pool.acquire() as conn:
            existing_user = await find_user_by_email(conn, payload.email)
            
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered.")
        
    password_hash = pwd_context.hash(payload.password)
    async with request.app.state.db_pool.acquire() as conn:
        user = await insert_user(conn, payload.email, password_hash)
        
    try:
        # CORREÇÃO: Converte UUID e datetime para string para o novo usuário
        user_dict_for_cache = {k: str(v) if isinstance(v, (uuid.UUID, datetime)) else v for k, v in dict(user).items()}
        await redis_client.setex(cache_key, 300, json.dumps(user_dict_for_cache))
    except Exception as e:
        logger.error(f"Error caching new user: {e}")
        
    return UserDTO(
        id=str(user["id"]),
        email=user["email"],
        created_at=str(user["created_at"]),
        updated_at=str(user["updated_at"]),
    )

@auth_router.post("/v1/login", response_model=object, tags=["Auth"])
async def login_user(payload: UserCreateDTO, request: Request):
    logger.info(f"Attempting login for user: {payload.email}")
    redis_client = request.app.state.redis_client
    cache_key = f"user_email:{payload.email}"
    user = None
    try:
        cached_user = await redis_client.get(cache_key)
        if cached_user:
            logger.info(f"Cache HIT for email={payload.email}")
            user = json.loads(cached_user)
        else:
            logger.info(f"Cache MISS for email={payload.email}")
            async with request.app.state.db_pool.acquire() as conn:
                user = await find_user_by_email(conn, payload.email)
            if user:
                user_dict_for_cache = {k: str(v) if isinstance(v, (uuid.UUID, datetime)) else v for k, v in dict(user).items()}
                await redis_client.setex(cache_key, 300, json.dumps(user_dict_for_cache))
    except Exception as e:
        logger.error(f"Redis error for email={payload.email}: {e}. Falling back to database.")
        async with request.app.state.db_pool.acquire() as conn:
            user = await find_user_by_email(conn, payload.email)

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    
    password_hash_to_verify = user.get("password_hash")
    if not password_hash_to_verify:
        async with request.app.state.db_pool.acquire() as conn:
            db_user = await find_user_by_email(conn, payload.email)
            password_hash_to_verify = db_user["password_hash"] if db_user else None

    if not password_hash_to_verify or not pwd_context.verify(payload.password, password_hash_to_verify):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    
    ALGORITHM = "HS256"
    expire = datetime.utcnow() + timedelta(days=12)
    to_encode = {
        "sub": str(user["id"]),
        "email": user["email"],
        "exp": expire
    }
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}
