import uuid
import pytest
import httpx
import json
import asyncio
from datetime import datetime

USER_ID = str(uuid.uuid4())
# USER_ID = "d155096c-b1db-4cd6-9091-853a298f240f"
API_GATEWAY_URL = "http://localhost:9999"
API_KEY = "your-super-secret-and-long-api-token"
INTERNAL_API_KEY = "your-different-secret-for-internal-services"

@pytest.mark.asyncio
async def test_data_ingestion_flow(db_connection):
    """
    Tests the end-to-end data ingestion flows for both emotion and transaction events.

    This integration test simulates sending:
    1. A single emotion event to the `/v1/emotions/stream` endpoint.
    2. A single transaction event to the `/v1/transactions` endpoint.

    It verifies that both requests are accepted and then waits to confirm that the
    asynchronous processing pipelines have successfully inserted the corresponding
    records into the database.

    Args:
        db_connection: An asyncpg connection fixture to the test database.
    """
    # Part 1: Emotion Ingestion
    # Arrange
    emotion_headers = {"Content-Type": "application/json", "X-Internal-Key": INTERNAL_API_KEY}
    emotion_payload = {
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
        emotion_response = await client.post(f"{API_GATEWAY_URL}/v1/emotions/stream", headers=emotion_headers, json=emotion_payload)

    # Part 2: Transaction Ingestion
    # Arrange
    transaction_headers = {"Content-Type": "application/json", "X-API-Key": API_KEY}
    transaction_payload = {
        "userId": USER_ID,
        "amount": 123.45
    }

    # Act
    async with httpx.AsyncClient() as client:
        transaction_response = await client.post(f"{API_GATEWAY_URL}/v1/transactions", headers=transaction_headers, json=transaction_payload)

    # Part 3: Asynchronous Verification
    # Arrange
    await asyncio.sleep(5)  # Wait for workers to process messages

    # Act
    emotion_summary = await db_connection.fetchrow(
        "SELECT * FROM emotional_events_summary WHERE user_id = $1", USER_ID
    )
    transaction_record = await db_connection.fetchrow(
        "SELECT * FROM transactions WHERE user_id = $1", USER_ID
    )

    # Assert
    assert emotion_response.status_code == 202
    assert transaction_response.status_code == 202
    assert emotion_summary is not None
    assert emotion_summary['event_count'] > 0
    assert transaction_record is not None
    assert float(transaction_record['amount']) == 123.45

@pytest.mark.asyncio
async def test_credit_analysis_flow(db_connection):
    """
    Validates the credit analysis endpoint for both approved and denied scenarios.

    This test calls the credit analysis endpoint and confirms that it returns a
    valid response structure regardless of the outcome.
    - If the credit is approved, it asserts that a valid offer is returned and
      has been correctly persisted in the 'credit_limits' table.
    - If the credit is denied, it asserts that the response indicates no approval
      and includes a reason for the denial.

    Args:
        db_connection: An asyncpg connection fixture to the test database.
    """
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
    """
    Tests the complete credit offer and acceptance lifecycle.

    This test handles the two possible outcomes of a credit analysis call:
    1.  If an offer is approved: It proceeds to test the acceptance flow by
        calling the acceptance endpoint. It then verifies the asynchronous
        side effects: a notification message is published on the NATS bus,
        and the offer's status in the database is updated to 'active'.
    2.  If an offer is denied: The test acknowledges this as a valid
        business outcome and passes without further action.

    Args:
        db_connection: An asyncpg connection fixture to the test database.
        nats_connection: A NATS client connection fixture to listen for events.
    """
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

@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", [
    "/v1/transactions",
    f"/v1/users/{USER_ID}/credit-analysis"
])
async def test_api_calls_with_wrong_key_should_fail(endpoint):
    """
    Validates that API calls with an incorrect API key are rejected.

    This test ensures that endpoints requiring an API key reject requests
    when an invalid key is provided. It tests multiple endpoints to confirm
    consistent behavior across the API.

    Args:
        endpoint: The API endpoint to test.

    Scenarios:
    - For `/v1/transactions`, a payload with a `userId` and `amount` is sent.
    - For `/v1/users/{USER_ID}/credit-analysis`, no payload is required.

    Assertions:
    - The response status code is 401 (Unauthorized).
    """
    headers = {"Content-Type": "application/json", "X-API-Key": "this-is-a-wrong-key"}
    payload = {"userId": USER_ID, "amount": 100} if "transactions" in endpoint else None

    async with httpx.AsyncClient() as client:
        if payload:
            response = await client.post(f"{API_GATEWAY_URL}{endpoint}", headers=headers, json=payload)
        else:
            response = await client.post(f"{API_GATEWAY_URL}{endpoint}", headers=headers)

    assert response.status_code == 401

@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", [
    "/v1/transactions",
    f"/v1/users/{USER_ID}/credit-analysis"
])
async def test_api_calls_without_key_should_fail(endpoint):
    """
    Validates that API calls missing the API key header are rejected.

    This test ensures that endpoints requiring an API key reject requests
    when the `X-API-Key` header is omitted. It tests multiple endpoints to
    confirm consistent behavior across the API.

    Args:
        endpoint: The API endpoint to test.

    Scenarios:
    - For `/v1/transactions`, a payload with a `userId` and `amount` is sent.
    - For `/v1/users/{USER_ID}/credit-analysis`, no payload is required.

    Assertions:
    - The response status code is 401 (Unauthorized).
    """
    headers = {"Content-Type": "application/json"}
    payload = {"userId": USER_ID, "amount": 100} if "transactions" in endpoint else None

    async with httpx.AsyncClient() as client:
        if payload:
            response = await client.post(f"{API_GATEWAY_URL}{endpoint}", headers=headers, json=payload)
        else:
            response = await client.post(f"{API_GATEWAY_URL}{endpoint}", headers=headers)

    assert response.status_code == 401

@pytest.mark.asyncio
async def test_internal_api_call_with_wrong_key_should_fail():
    """
    Validates that internal API calls with an incorrect internal key are rejected.

    This test ensures that endpoints requiring an `X-Internal-Key` header reject
    requests when an invalid key is provided. It specifically tests the
    `/v1/emotions/stream` endpoint, which is used for internal emotion ingestion.

    Scenario:
    - A payload containing a `userId`, `timestamp`, and `emotionEvent` is sent
      with an invalid `X-Internal-Key`.

    Assertions:
    - The response status code is 401 (Unauthorized).
    """
    headers = {"Content-Type": "application/json", "X-Internal-Key": "this-is-a-wrong-internal-key"}
    emotion_payload = {
        "userId": USER_ID,
        "timestamp": datetime.utcnow().isoformat(),
        "emotionEvent": {
            "type": "TEST",
            "metrics": {
                "positivity": 0.5,
                "intensity": 0.5,
                "stress_level": 0.5,
            },
        },
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_GATEWAY_URL}/v1/emotions/stream", headers=headers, json=emotion_payload)

    assert response.status_code == 401
