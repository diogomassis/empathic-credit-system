from fastapi import FastAPI
from router.router import http_client
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the application's lifecycle.
    The code before 'yield' runs on startup.
    The code after 'yield' runs on shutdown.
    """
    yield
    await http_client.aclose()
