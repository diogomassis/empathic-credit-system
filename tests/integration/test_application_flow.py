import uuid
import pytest
import httpx
import json
import asyncio
from datetime import datetime

USER_ID = str(uuid.uuid4())
API_GATEWAY_URL = "http://localhost:9999"
API_KEY = "your-super-secret-and-long-api-token"
INTERNAL_API_KEY = "your-different-secret-for-internal-services"

@pytest.mark.asyncio
async def test_data_ingestion_flow(db_connection):
    # Arrange
    headers = {"Content-Type": "application/json", "X-Internal-Key": INTERNAL_API_KEY}
    payload = {
        "userId": USER_ID,
        "timestamp": datetime.utcnow().isoformat(),
        "emotionEvent": {
            "type": "SENTIMENT_ANALYSIS",
            "metrics": {
                "positivity": 0.8,
                "intensity": 0.9,
                "stress_level": 0.2,
            },
        },
    }

    # Act
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_GATEWAY_URL}/v1/emotions/stream", headers=headers, json=payload)
    await asyncio.sleep(5)
    summary = await db_connection.fetchrow(
        "SELECT * FROM emotional_events_summary WHERE user_id = $1", USER_ID
    )

    # Assert
    assert response.status_code == 202
    assert summary is not None
    assert summary['event_count'] > 0

@pytest.mark.asyncio
async def test_credit_analysis_flow(db_connection):
    # Arrange
    headers = {"Content-Type": "application/json", "X-API-Key": API_KEY}

    # Act
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_GATEWAY_URL}/v1/users/{USER_ID}/credit-analysis", headers=headers)
        response_json = response.json()
        print(response_json)

    # Assert
    assert response.status_code == 200
    if response_json.get("approved"):
        assert "offer" in response_json and response_json["offer"] is not None
        offer_id = response_json["offer"]["offer_id"]
        offer = await db_connection.fetchrow("SELECT * FROM credit_limits WHERE id = $1", offer_id)
        assert offer is not None
        assert offer["status"] == "offered"
    else:
        assert response_json.get("approved") is False
        assert "reason" in response_json
        assert "offer" not in response_json or response_json["offer"] is None

@pytest.mark.asyncio
async def test_credit_acceptance_flow(db_connection, nats_connection):
    # Arrange
    headers = {"Content-Type": "application/json", "X-API-Key": API_KEY}
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_GATEWAY_URL}/v1/users/{USER_ID}/credit-analysis", headers=headers)
        response_json = response.json()

    # Act & Assert
    assert response.status_code == 200
    if response_json.get("approved") and response_json.get("offer"):
        offer_id = response_json["offer"]["offer_id"]
        print(f"\nTest scenario: APPROVED offer (ID: {offer_id}). Proceeding with acceptance test...")

        future = asyncio.Future()
        async def message_handler(msg):
            if not future.done():
                future.set_result(msg.data)

        sub = await nats_connection.subscribe("user.notifications", cb=message_handler)

        try:
            payload = {"userId": USER_ID}
            async with httpx.AsyncClient() as client:
                accept_response = await client.post(f"{API_GATEWAY_URL}/v1/credit-offers/{offer_id}/accept", headers=headers, json=payload)
            notification = await asyncio.wait_for(future, timeout=10)
            notification_data = json.loads(notification.decode())
            offer_record = await db_connection.fetchrow("SELECT * FROM credit_limits WHERE id = $1", offer_id)

            # Assert
            assert accept_response.status_code == 202
            assert notification_data["type"] == "CREDIT_LIMIT_APPLIED"
            assert notification_data["userId"] == USER_ID
            assert offer_record is not None
            assert offer_record["status"] == "active"
            print("Acceptance flow completed successfully.")

        finally:
            await sub.unsubscribe()

    elif not response_json.get("approved") and response_json.get("reason"):
        reason = response_json['reason']
        print(f"\nTest scenario: DENIED offer (Reason: {reason}). Test passed, as this is a valid result.")
        assert True

    else:
        pytest.fail(f"Unexpected API response: {response_json}")
