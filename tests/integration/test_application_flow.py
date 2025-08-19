import pytest
import httpx
import json
import asyncio
from datetime import datetime, timezone
import os

API_GATEWAY_URL = "http://localhost:9999"
INTERNAL_API_KEY = "your-different-secret-for-internal-services" 

def load_user_sessions():
    """Reads the sessions.json file and prepares it for parameterization."""
    sessions_file = os.path.join(os.path.dirname(__file__), '..', '..', 'k6', 'sessions.json')
    if not os.path.exists(sessions_file):
        pytest.skip(f"Data file '{sessions_file}' not found. Skipping integration tests.")
    with open(sessions_file, 'r') as f:
        sessions = json.load(f)
    if not sessions:
        pytest.skip(f"File '{sessions_file}' is empty. No users to test.")
    return sessions

USER_SESSIONS = load_user_sessions()
STATIC_TEST_USER_ID = USER_SESSIONS[0]['userId'] if USER_SESSIONS else "default-user-id"

@pytest.mark.asyncio
@pytest.mark.parametrize("user_session", USER_SESSIONS)
async def test_data_ingestion_flow(db_connection, user_session):
    """
    Tests the data ingestion flow for each user in sessions.json.
    """
    user_id = user_session['userId']

    # AAA: Arrange
    emotion_headers = {"Content-Type": "application/json", "X-Internal-Key": INTERNAL_API_KEY}
    emotion_payload = {
        "userId": user_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "emotionEvent": { "type": "SENTIMENT_ANALYSIS", "metrics": { "positivity": 0.8, "intensity": 0.9, "stress_level": 0.2 } },
    }
    async with httpx.AsyncClient() as client:
        emotion_response = await client.post(f"{API_GATEWAY_URL}/v1/emotions/stream", headers=emotion_headers, json=emotion_payload)

    # AAA: Act
    transaction_headers = {
        "Content-Type": "application/json", 
        "Authorization": f"Bearer {user_session['token']}"
    }
    transaction_payload = {"userId": user_id, "amount": 123.45}
    async with httpx.AsyncClient() as client:
        transaction_response = await client.post(f"{API_GATEWAY_URL}/v1/transactions", headers=transaction_headers, json=transaction_payload)

    # AAA: Assert
    await asyncio.sleep(0.5)
    emotion_summary = await db_connection.fetchrow("SELECT * FROM emotional_events_summary WHERE user_id = $1", user_id)
    transaction_record = await db_connection.fetchrow("SELECT * FROM transactions WHERE user_id = $1", user_id)

    assert emotion_response.status_code == 202
    assert transaction_response.status_code == 202
    assert emotion_summary is not None
    assert transaction_record is not None


@pytest.mark.asyncio
@pytest.mark.parametrize("user_session", USER_SESSIONS)
async def test_credit_analysis_flow(db_connection, user_session):
    """
    Validates the credit analysis for each user in sessions.json.
    """
    user_id = user_session['userId']

    # AAA: Arrange
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {user_session['token']}"
    }

    # AAA: Act
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_GATEWAY_URL}/v1/users/{user_id}/credit-analysis", headers=headers)
        response_json = response.json()

    # AAA: Assert
    assert response.status_code == 200
    if response_json.get("approved"):
        offer_id = response_json["offer"]["offer_id"]
        offer = await db_connection.fetchrow("SELECT * FROM credit_limits WHERE id = $1", offer_id)
        assert offer is not None and offer["status"] == "offered"
    else:
        assert response_json.get("approved") is False and "reason" in response_json


@pytest.mark.asyncio
@pytest.mark.parametrize("user_session", USER_SESSIONS)
async def test_credit_acceptance_flow(db_connection, nats_connection, user_session):
    """
    Tests the full credit acceptance lifecycle for each user.
    """
    user_id = user_session['userId']

    # AAA: Arrange
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {user_session['token']}"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_GATEWAY_URL}/v1/users/{user_id}/credit-analysis", headers=headers)
        response_json = response.json()

    # AAA: Act
    assert response.status_code == 200
    if response_json.get("approved") and response_json.get("offer"):
        offer_id = response_json["offer"]["offer_id"]
        future = asyncio.Future()
        async def message_handler(msg):
            if not future.done(): future.set_result(msg.data)
        sub = await nats_connection.subscribe("user.notifications", cb=message_handler)
        try:
            payload = {"userId": user_id}
            async with httpx.AsyncClient() as client:
                accept_response = await client.post(f"{API_GATEWAY_URL}/v1/credit-offers/{offer_id}/accept", headers=headers, json=payload)
            notification = await asyncio.wait_for(future, timeout=10)
            notification_data = json.loads(notification.decode())
            offer_record = await db_connection.fetchrow("SELECT * FROM credit_limits WHERE id = $1", offer_id)

            # AAA: Assert
            assert accept_response.status_code == 202
            assert notification_data["userId"] == user_id
            assert offer_record["status"] == "active"
        finally:
            await sub.unsubscribe()
    elif not response_json.get("approved"):
        print(f"\nUser {user_id}: Offer denied. Test passed.")
        assert True
    else:
        pytest.fail(f"Unexpected API response for user {user_id}: {response_json}")


# --- Security Tests ---

@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", [
    "/v1/transactions",
    f"/v1/users/{STATIC_TEST_USER_ID}/credit-analysis"
])
async def test_api_calls_with_wrong_token_should_fail(endpoint):
    """Validates that calls with an incorrect Bearer token are rejected."""
    # AAA: Arrange
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer this-is-a-wrong-token"
    }
    payload = {"userId": STATIC_TEST_USER_ID, "amount": 100} if "transactions" in endpoint else None

    # AAA: Act
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_GATEWAY_URL}{endpoint}", headers=headers, json=payload if payload else None)

    # AAA: Assert
    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", [
    "/v1/transactions",
    f"/v1/users/{STATIC_TEST_USER_ID}/credit-analysis"
])
async def test_api_calls_without_auth_header_should_fail(endpoint):
    """Validates that calls without the authentication header are rejected."""
    # AAA: Arrange
    headers = {"Content-Type": "application/json"}
    payload = {"userId": STATIC_TEST_USER_ID, "amount": 100} if "transactions" in endpoint else None

    # AAA: Act
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_GATEWAY_URL}{endpoint}", headers=headers, json=payload if payload else None)

    # AAA: Assert
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_internal_api_call_with_wrong_key_should_fail():
    """Validates that internal calls with an incorrect key are rejected."""
    # AAA: Arrange
    headers = {"Content-Type": "application/json", "X-Internal-Key": "this-is-a-wrong-internal-key"}
    emotion_payload = {
        "userId": STATIC_TEST_USER_ID,
        "timestamp": datetime.utcnow().isoformat(),
        "emotionEvent": { "type": "TEST", "metrics": { "positivity": 0.5, "intensity": 0.5, "stress_level": 0.5 } },
    }

    # AAA: Act
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_GATEWAY_URL}/v1/emotions/stream", headers=headers, json=emotion_payload)

    # AAA: Assert
    assert response.status_code == 401
