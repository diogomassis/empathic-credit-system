from fastapi import FastAPI
from lifespan.lifespan import lifespan
from api.api import router as api_router
from fastapi.responses import ORJSONResponse

app = FastAPI(
    lifespan=lifespan,
    title="Transaction Service",
    version="1.0.0",
    default_response_class=ORJSONResponse 
)

app.include_router(api_router)
