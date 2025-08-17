from fastapi import FastAPI
from lifespan.lifespan import lifespan
from router.router import router as api_router

app = FastAPI(
    lifespan=lifespan,
    title="Empathic Credit System API Gateway",
    version="1.0.0"
)

app.include_router(api_router)
