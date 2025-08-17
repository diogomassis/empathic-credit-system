from fastapi import FastAPI
from api.api import router as api_router
from lifespan.lifespan import lifespan

app = FastAPI(
    lifespan=lifespan,
    title="User & Credit Service",
    version="1.0.0"
)

app.include_router(api_router)
