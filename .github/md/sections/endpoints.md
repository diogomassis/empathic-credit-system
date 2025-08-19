# Endpoints

The `api-gateway-ecs` centralizes access to the system, routing requests to the appropriate internal microservices. Below are the endpoints and examples of how to use them.

## Authentication

### Register a new user

* **Endpoint**: `POST /v1/auth/register`

* **Description**: Creates a new user in the system.

* **Example `cURL`**:

    ```bash
    curl -X POST http://localhost:9999/v1/auth/register \
    -H "Content-Type: application/json" \
    -d '{
        "email": "new_user@example.com",
        "password": "super_secure_password_123"
    }'
    ```

### User login

* **Endpoint**: `POST /v1/auth/login`

* **Description**: Authenticates a user and returns a JWT token.

* **Example `cURL`**:

    ```bash
    curl -X POST http://localhost:9999/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{
        "email": "new_user@example.com",
        "password": "super_secure_password_123"
    }'
    ```

### Data Ingestion

### Send emotion event (Internal communication)

* **Endpoint**: `POST /v1/emotions/stream`

* **Description**: Receives and publishes an emotion event. Protected by an internal API key (`X-Internal-Key`).

* **Example `cURL`**:

    ```bash
    curl -X POST http://localhost:9999/v1/emotions/stream \
    -H "Content-Type: application/json" \
    -H "X-Internal-Key: your-different-secret-for-internal-services" \
    -d '{
        "userId": "user-uuid-here",
        "timestamp": "2025-08-19T12:00:00Z",
        "emotionEvent": {
            "type": "SENTIMENT_ANALYSIS",
            "metrics": {
                "positivity": 0.85,
                "intensity": 0.7,
                "stress_level": 0.15
            }
        }
    }'
    ```

### Send transaction event

* **Endpoint**: `POST /v1/transactions`

* **Description**: Receives and publishes a transaction event. Requires JWT token authentication.

* **Example `cURL`**:

    ```bash
    curl -X POST http://localhost:9999/v1/transactions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer your-jwt-token-here" \
    -d '{
        "userId": "user-uuid-here",
        "amount": 199.99
    }'
    ```

### Credit Analysis and Offers

#### Request credit analysis

* **Endpoint**: `POST /v1/users/{user_id}/credit-analysis`

* **Description**: Initiates the credit analysis flow for a user. Requires JWT token.

* **Example `cURL`**:

    ```bash
    curl -X POST http://localhost:9999/v1/users/user-uuid-here/credit-analysis \
    -H "Authorization: Bearer your-jwt-token-here"
    ```

#### Accept a credit offer

* **Endpoint**: `POST /v1/credit-offers/{offer_id}/accept`

* **Description**: Marks a credit offer as accepted and starts the asynchronous activation process. Requires JWT token.

* **Example `cURL`**:

    ```bash
    curl -X POST http://localhost:9999/v1/credit-offers/offer-uuid-here/accept \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer your-jwt-token-here" \
    -d '{
        "userId": "user-uuid-here"
    }'
    ```

#### List a user's credit offers

* **Endpoint**: `GET /v1/users/{user_id}/offers`

* **Description**: Returns a paginated list of a user's credit offers. Requires JWT token.

* **Example `cURL**:

    ```bash
    curl -X GET "http://localhost:9999/v1/users/user-uuid-here/offers?page=1&page_size=10" \
    -H "Authorization: Bearer your-jwt-token-here"
    ```

## Authentication Mechanism

The system uses a double authentication scheme, ensuring security for both external clients (users) and internal communication between services.

**External Authentication (JWT Bearer Token):**

* **Implementation:** For endpoints accessed by users, such as `/v1/transactions` or `/v1/users/{user_id}/credit-analysis`, the system requires a JSON Web Token (JWT) in the Authorization header.

* **Flow:** The user authenticates via `/v1/auth/login`. The user-and-credit-service validates the credentials and, if correct, generates a JWT token signed with SECRET_KEY using the HS256 algorithm. This token, containing the user ID and expiration date, is returned. In each subsequent request, the API Gateway uses the validate_api_key function to decode and validate the token before forwarding the call.

**Internal Authentication (API Key):**

* **Implementation:** For communication between services that should not be publicly exposed, such as emotion ingestion, a static API key is used.

* **Flow:** The source service (e.g., a simulator) must include the key in the X-Internal-Key header. The API Gateway uses the validate_internal_api_key function to verify that the received key matches the INTERNAL_SERVICE_API_KEY defined in the environment variables. This ensures that only trusted services can send emotion data to the system.
