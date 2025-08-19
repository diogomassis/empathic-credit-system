import uuid

async def get_user_features(db_conn, user_id: str) -> dict:
    """Fetches aggregated user data to form a feature vector."""
    emotional_query = """
    SELECT AVG(avg_positivity_score) as avg_positivity, SUM(event_count) as stress_events
    FROM emotional_events_summary 
    WHERE user_id = $1 AND summary_date >= NOW() - INTERVAL '7 days';
    """
    emotional_data = await db_conn.fetchrow(emotional_query, user_id)

    transactional_query = """
    SELECT COUNT(*) as tx_count, AVG(amount) as avg_tx_value
    FROM transactions 
    WHERE user_id = $1 AND created_at >= NOW() - INTERVAL '30 days';
    """
    transactional_data = await db_conn.fetchrow(transactional_query, user_id)

    feature_vector = {
        "transaction_count_30d": transactional_data['tx_count'] if transactional_data else 0,
        "avg_transaction_value_30d": float(transactional_data['avg_tx_value'] or 0.0),
        "avg_positivity_7d": emotional_data['avg_positivity'] if emotional_data and emotional_data['avg_positivity'] is not None else 0.5,
        "stress_events_30d": emotional_data['stress_events'] if emotional_data and emotional_data['stress_events'] is not None else 0
    }
    import logging
    logging.info(f"Feature vector for ML: {feature_vector}")
    return feature_vector

async def save_credit_offer(db_conn, offer_details: dict):
    """Saves a new credit offer to the database."""
    insert_query = """
    INSERT INTO credit_limits (id, user_id, status, credit_limit, interest_rate, credit_type, expires_at)
    VALUES ($1, $2, 'offered', $3, $4, $5, $6)
    """
    await db_conn.execute(
        insert_query, 
        offer_details['id'], 
        offer_details['user_id'], 
        offer_details['credit_limit'], 
        offer_details['interest_rate'], 
        offer_details['credit_type'], 
        offer_details['expires_at']
    )

async def validate_offer_for_acceptance(db_conn, offer_id: str, user_id: str):
    """Validates if an offer is valid for acceptance."""
    validation_query = """
    SELECT id, user_id, credit_limit, interest_rate, credit_type 
    FROM credit_limits 
    WHERE id = $1 AND user_id = $2 AND status = 'offered' AND expires_at > NOW()
    """
    return await db_conn.fetchrow(validation_query, uuid.UUID(offer_id), user_id)

async def fetch_paginated_offers(db_conn, user_id: str, page_size: int, offset: int):
    """Fetches a paginated list of offers for a user."""
    count_query = "SELECT COUNT(*) FROM credit_limits WHERE user_id = $1;"
    total_count = await db_conn.fetchval(count_query, user_id)
    
    offers_query = """
    SELECT id, status, credit_limit, interest_rate, created_at, expires_at
    FROM credit_limits
    WHERE user_id = $1
    ORDER BY created_at DESC
    LIMIT $2 OFFSET $3;
    """
    records = await db_conn.fetch(offers_query, user_id, page_size, offset)
    
    return total_count, records

async def insert_user(db_conn, email: str, password_hash: str):
    """
    Inserts a new user into the users table.
    Returns the created user record.
    """
    query = """
    INSERT INTO users (email, password_hash)
    VALUES ($1, $2)
    RETURNING id, email, created_at, updated_at;
    """
    return await db_conn.fetchrow(query, email, password_hash)

async def find_user_by_email(db_conn, email: str):
    """
    Finds a user by email.
    Returns the user record or None if not found.
    """
    query = """
    SELECT id, email, password_hash, created_at, updated_at
    FROM users
    WHERE email = $1;
    """
    return await db_conn.fetchrow(query, email)
