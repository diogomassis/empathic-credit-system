import os
import httpx
import asyncpg
import logging
import nats
import json
import uuid

from datetime import datetime, timedelta
from typing import List

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status, Query
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ecsuser:ecspassword@localhost:5432/ecsdb")
CREDIT_ANALYSIS_SERVICE_URL = os.getenv("CREDIT_ANALYSIS_SERVICE_URL", "http://credit-analysis-service:8000/v1/predict")
NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")
NATS_ACCEPT_SUBJECT = "credit.offers.approved"

class CreditOffer(BaseModel):
    offer_id: str = Field(..., description="Unique ID for the credit offer.")
    credit_limit: float = Field(..., description="The approved credit limit.")
    interest_rate: float = Field(..., description="The annual interest rate.")
    credit_type: str = Field(..., description="Type of credit (e.g., SHORT_TERM_PERSONAL_LOAN).")
    expires_at: str = Field(..., description="Offer expiration date in ISO 8601 format.")

class CreditAnalysisResponse(BaseModel):
    user_id: str
    approved: bool
    ml_risk_score: float
    offer: CreditOffer | None = None
    reason: str | None = None

class AcceptOfferPayload(BaseModel):
    user_id: str = Field(..., alias="userId")

class CreditOfferListItem(BaseModel):
    offer_id: str
    status: str
    credit_limit: float
    interest_rate: float
    created_at: datetime
    expires_at: datetime

class PaginatedOffersResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[CreditOfferListItem]

@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Initializing service connections...")
    try:
        app.state.db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
        app.state.http_client = httpx.AsyncClient(timeout=5.0)
        app.state.nats_conn = await nats.connect(NATS_URL, name="user_credit_service")
        logging.info("All connections established successfully.")
        yield
    finally:
        logging.info("Closing service connections...")
        if hasattr(app.state, 'db_pool'):
            await app.state.db_pool.close()
        if hasattr(app.state, 'http_client'):
            await app.state.http_client.aclose()
        if hasattr(app.state, 'nats_conn') and app.state.nats_conn.is_connected:
            await app.state.nats_conn.close()
        logging.info("All connections closed.")

app = FastAPI(
    lifespan=lifespan,
    title="User & Credit Service",
    version="1.0.0"
)

@app.get("/healthz", status_code=status.HTTP_200_OK, tags=["Monitoring"])
async def health_check():
    return {"status": "ok"}

@app.post("/v1/users/{user_id}/credit-analysis", response_model=CreditAnalysisResponse, tags=["Credit Analysis"])
async def analyze_credit(user_id: str, request: Request):
    logging.info(f"Starting credit analysis for user_id={user_id}")
    
    async with request.app.state.db_pool.acquire() as conn:
        emotional_query = """
        SELECT AVG(avg_positivity_score) as avg_positivity, SUM(event_count) as stress_events
        FROM emotional_events_summary 
        WHERE user_id = $1 AND summary_date >= NOW() - INTERVAL '7 days';
        """
        emotional_data = await conn.fetchrow(emotional_query, user_id)

        transactional_query = """
        SELECT COUNT(*) as tx_count, AVG(amount) as avg_tx_value
        FROM transactions 
        WHERE user_id = $1 AND created_at >= NOW() - INTERVAL '30 days';
        """
        transactional_data = await conn.fetchrow(transactional_query, user_id)

    feature_vector = {
        "transaction_count_30d": transactional_data['tx_count'] if transactional_data else 0,
        "avg_transaction_value_30d": float(transactional_data['avg_tx_value'] or 0.0),
        "avg_positivity_7d": emotional_data['avg_positivity'] if emotional_data and emotional_data['avg_positivity'] is not None else 0.5,
        "stress_events_30d": emotional_data['stress_events'] if emotional_data else 0
    }

    http_client = request.app.state.http_client
    try:
        response = await http_client.post(CREDIT_ANALYSIS_SERVICE_URL, json=feature_vector)
        response.raise_for_status()
        ml_result = response.json()
        risk_score = ml_result.get("risk_score")
    except httpx.RequestError as e:
        logging.error(f"HTTP error calling credit analysis service: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Credit analysis service is unavailable.")

    if risk_score is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid response from analysis service.")
    if risk_score > 0.6:
        logging.info(f"Analysis denied for user_id={user_id} with score={risk_score}")
        return CreditAnalysisResponse(
            user_id=user_id, approved=False, ml_risk_score=risk_score, reason="High risk score."
        )
    else:
        offer_id = uuid.uuid4()
        credit_limit = round(max(1000, (1 - risk_score) * 10000), 2)
        interest_rate = round(5.0 + (risk_score * 15), 2)
        credit_type = "SHORT_TERM_PERSONAL_LOAN"
        expires_at = datetime.utcnow() + timedelta(days=7)
        async with request.app.state.db_pool.acquire() as conn:
            insert_query = """
            INSERT INTO credit_limits (id, user_id, status, credit_limit, interest_rate, credit_type, expires_at)
            VALUES ($1, $2, 'offered', $3, $4, $5, $6)
            """
            await conn.execute(insert_query, offer_id, user_id, credit_limit, interest_rate, credit_type, expires_at)
        logging.info(f"Offer {offer_id} saved to database for user_id={user_id}")
        return CreditAnalysisResponse(
            user_id=user_id,
            approved=True,
            ml_risk_score=risk_score,
            offer=CreditOffer(
                offer_id=str(offer_id),
                credit_limit=credit_limit,
                interest_rate=interest_rate,
                credit_type=credit_type,
                expires_at=expires_at.isoformat()
            )
        )

@app.post("/v1/credit-offers/{offer_id}/accept", status_code=status.HTTP_202_ACCEPTED, tags=["Credit Analysis"])
async def accept_credit_offer(offer_id: str, payload: AcceptOfferPayload, request: Request):
    logging.info(f"User {payload.user_id} attempting to accept offer {offer_id}")
    
    async with request.app.state.db_pool.acquire() as conn:
        validation_query = """
        SELECT id, user_id, credit_limit, interest_rate, credit_type 
        FROM credit_limits 
        WHERE id = $1 AND user_id = $2 AND status = 'offered' AND expires_at > NOW()
        """
        offer_data = await conn.fetchrow(validation_query, uuid.UUID(offer_id), payload.user_id)
    if not offer_data:
        logging.warning(f"Invalid or expired offer acceptance attempt for offer {offer_id} by user {payload.user_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found, expired, or already processed.")
    nc = request.app.state.nats_conn
    event_data = {
        "offerId": str(offer_data['id']),
        "userId": str(offer_data['user_id']),
        "creditLimit": float(offer_data['credit_limit']),
        "interestRate": offer_data['interest_rate'],
        "creditType": offer_data['credit_type'],
        "acceptedAt": datetime.utcnow().isoformat()
    }
    await nc.publish(NATS_ACCEPT_SUBJECT, json.dumps(event_data).encode())
    logging.info(f"Acceptance event for offer {offer_id} published to NATS subject '{NATS_ACCEPT_SUBJECT}'")
    return {"status": "offer acceptance is being processed"}

@app.get("/v1/users/{user_id}/offers", response_model=PaginatedOffersResponse, tags=["Credit Offers"])
async def get_user_offers(
    user_id: str,
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page")
):
    logging.info(f"Fetching offers for user_id={user_id}, page={page}, page_size={page_size}")
    offset = (page - 1) * page_size
    async with request.app.state.db_pool.acquire() as conn:
        count_query = "SELECT COUNT(*) FROM credit_limits WHERE user_id = $1;"
        total_count = await conn.fetchval(count_query, user_id)
        offers_query = """
        SELECT id, status, credit_limit, interest_rate, created_at, expires_at
        FROM credit_limits
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT $2 OFFSET $3;
        """
        records = await conn.fetch(offers_query, user_id, page_size, offset)
    items = [
        CreditOfferListItem(
            offer_id=str(r['id']),
            status=r['status'],
            credit_limit=r['credit_limit'],
            interest_rate=r['interest_rate'],
            created_at=r['created_at'],
            expires_at=r['expires_at']
        ) for r in records
    ]
    return PaginatedOffersResponse(
        total=total_count,
        page=page,
        page_size=page_size,
        items=items
    )
