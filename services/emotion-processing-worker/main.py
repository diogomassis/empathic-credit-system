from fastapi import FastAPI, status
from fastapi.responses import ORJSONResponse

app = FastAPI(
    title="Emotion Ingestion Service",
    version="1.1.0",
    default_response_class=ORJSONResponse 
)

@app.get("/healthz", status_code=status.HTTP_200_OK, tags=["Monitoring"])
async def health_check():
    return {"status": "ok"}
