import nats
import asyncpg
import pytest_asyncio

@pytest_asyncio.fixture
async def db_connection():
    """
    Creates a new database connection for each test.
    """
    conn = await asyncpg.connect(
        user="ecsuser",
        password="ecspassword",
        database="ecsdb",
        host="localhost"
    )
    yield conn
    await conn.close()

@pytest_asyncio.fixture
async def nats_connection():
    """
    Creates a new NATS connection for each test.
    """
    nc = await nats.connect("nats://localhost:4222")
    yield nc
    await nc.close()
