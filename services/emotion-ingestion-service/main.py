from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from lifespan.lifespan import lifespan
from api.api import router as api_router

app = FastAPI(
    lifespan=lifespan,
    title="Emotion Ingestion Service",
    version="1.1.0",
    default_response_class=ORJSONResponse 
)

app.include_router(api_router)
