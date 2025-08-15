import os
import httpx
import asyncpg
import logging
import nats
import json
import uuid
from datetime import datetime, timedelta

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages the service's connections (DB pool, HTTP client, NATS)."""
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
        WHERE user_id = $1 AND transaction_date >= NOW() - INTERVAL '30 days';
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
        credit_limit = max(1000, (1 - risk_score) * 10000)
        interest_rate = 5.0 + (risk_score * 15)
        
        logging.info(f"Analysis approved for user_id={user_id} with score={risk_score}")
        return CreditAnalysisResponse(
            user_id=user_id,
            approved=True,
            ml_risk_score=risk_score,
            offer=CreditOffer(
                offer_id=str(uuid.uuid4()),
                credit_limit=round(credit_limit, 2),
                interest_rate=round(interest_rate, 2),
                credit_type="SHORT_TERM_PERSONAL_LOAN",
                expires_at=(datetime.utcnow() + timedelta(days=7)).isoformat()
            )
        )

@app.post("/v1/credit-offers/{offer_id}/accept", status_code=status.HTTP_202_ACCEPTED, tags=["Credit Analysis"])
async def accept_credit_offer(offer_id: str, payload: AcceptOfferPayload, request: Request):
    logging.info(f"User {payload.user_id} accepted offer {offer_id}")
    
    nc = request.app.state.nats_conn
    event_data = {
        "offerId": offer_id,
        "userId": payload.user_id,
        "acceptedAt": datetime.now().isoformat()
    }
    
    await nc.publish(NATS_ACCEPT_SUBJECT, json.dumps(event_data).encode())
    logging.info(f"Acceptance event for offer {offer_id} published to NATS subject '{NATS_ACCEPT_SUBJECT}'")
    
    return {"status": "offer acceptance is being processed"}
