from fastapi import FastAPI
from contextlib import asynccontextmanager
from router.router import router as http_client

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the application's lifecycle.
    The code before 'yield' runs on startup.
    The code after 'yield' runs on shutdown.
    """
    yield
    await http_client.aclose()
